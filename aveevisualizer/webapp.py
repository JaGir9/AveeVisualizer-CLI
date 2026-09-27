import json, threading, time, webbrowser
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory
from .theme import discover_themes
from .media import scan, IMAGE_EXT, AUDIO_EXT
from .performance import detect_profile, describe
from .render import render_video, SceneRenderer, RenderCancelled

ROOT=Path(__file__).resolve().parents[1]
app=Flask(__name__,template_folder=str(ROOT/'web'/'templates'))
lock=threading.Lock()
job={'state':'idle','percent':0,'message':'Siap','logs':[]}
cancel_event=threading.Event()

QUALITIES={'480p':(854,480),'720p':(1280,720),'1080p':(1920,1080),'1440p':(2560,1440),'2160p':(3840,2160)}

def log(msg):
    with lock:
        job.setdefault('logs',[]).append(str(msg)); job['logs']=job['logs'][-100:]

def snapshot():
    with lock: return json.loads(json.dumps(job))

def files_payload():
    themes=discover_themes(ROOT/'Themes')
    return {
      'themes':[{'id':str(t.path.relative_to(ROOT)),'name':f'{t.path.parent.name} / {t.path.name}'} for t in themes],
      'music':[p.name for p in scan(ROOT/'Music',AUDIO_EXT)],
      'backgrounds':[p.name for p in scan(ROOT/'BackGround',IMAGE_EXT)],
      'logos':[p.name for p in scan(ROOT/'Logo',IMAGE_EXT)],
      'qualities':list(QUALITIES.keys())
    }

def safe_file(folder,name,exts):
    p=(ROOT/folder/name).resolve(); base=(ROOT/folder).resolve()
    if p.parent!=base or p.suffix.lower() not in exts or not p.is_file(): raise ValueError(f'File {folder} tidak valid')
    return p

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/files')
def api_files():
    data=files_payload(); p=detect_profile(); data['performance']=describe(p); data['encoder']=p['encoder_label']; return jsonify(data)

@app.get('/api/status')
def api_status(): return jsonify(snapshot())

@app.post('/api/cancel')
def api_cancel():
    if snapshot().get('state')=='rendering':
        cancel_event.set(); log('Permintaan cancel diterima.')
    return jsonify({'ok':True})

@app.get('/output/<path:name>')
def output(name): return send_from_directory(ROOT/'Output',name,as_attachment=True)

@app.post('/api/render')
def api_render():
    global job
    if snapshot().get('state')=='rendering': return jsonify({'error':'Render lain masih berjalan.'}),409
    d=request.get_json(force=True)
    try:
        theme_path=(ROOT/d['theme']).resolve()
        if (ROOT/'Themes').resolve() not in theme_path.parents: raise ValueError('Theme tidak valid')
        from .theme import Theme
        theme=Theme(theme_path)
        music=safe_file('Music',d['music'],AUDIO_EXT); bg=safe_file('BackGround',d['background'],IMAGE_EXT); logo=safe_file('Logo',d['logo'],IMAGE_EXT)
        quality=d.get('quality','720p')
        if quality not in QUALITIES: raise ValueError('Kualitas tidak valid')
        w,h=QUALITIES[quality]
        if d.get('orientation')=='portrait': w,h=h,w
    except (KeyError,ValueError,OSError,json.JSONDecodeError) as e: return jsonify({'error':str(e)}),400
    profile=detect_profile(); out=ROOT/'Output'/f'{music.stem}_visualizer.mp4'; out.parent.mkdir(exist_ok=True)
    cancel_event.clear()
    with lock:
        job={'state':'rendering','percent':0,'frame':0,'total_frames':0,'render_fps':0,'realtime':0,'elapsed':0,'eta':0,'message':'Menganalisis audio...','output':out.name,'logs':[]}
    report=theme.report(SceneRenderer.SUPPORTED,SceneRenderer.SUPPORTED_MEASURES)
    log(f"Theme: {theme.path.parent.name} | {report['compositions']} compositions | {report['elements']} elements")
    log(f"Encoder: {profile['encoder_label']} | Resolution: {w}x{h} | FPS: 30")
    def progress(info):
        with lock:
            job.update(info); job['message']='Rendering frame...'
    def worker():
        try:
            render_video(theme,music,bg,logo,out,w,h,30,18,profile['preset'],profile['encoder'],profile['cores'],progress_cb=progress,cancel_event=cancel_event)
            with lock: job.update({'state':'done','percent':100,'message':'Render selesai.'})
            log(f'Selesai: {out.name}')
        except RenderCancelled:
            out.unlink(missing_ok=True)
            with lock: job.update({'state':'cancelled','message':'Render dibatalkan.'})
            log('Render dibatalkan.')
        except Exception as e:
            out.unlink(missing_ok=True)
            with lock: job.update({'state':'error','message':str(e)})
            log(f'ERROR: {e}')
    threading.Thread(target=worker,daemon=True).start()
    return jsonify({'ok':True,'output':out.name})

def run_web(host='127.0.0.1',port=8080,open_browser=True):
    if open_browser: threading.Timer(1.0,lambda:webbrowser.open(f'http://{host}:{port}')).start()
    app.run(host=host,port=port,debug=False,threaded=True,use_reloader=False)

if __name__=='__main__': run_web()
