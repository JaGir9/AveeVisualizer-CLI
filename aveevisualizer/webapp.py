import json, threading, webbrowser, shutil, re
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename
from .theme import Theme, discover_themes
from .media import scan, IMAGE_EXT, AUDIO_EXT
from .performance import detect_profile, describe
from .render import render_video, SceneRenderer, RenderCancelled

ROOT=Path(__file__).resolve().parents[1]
PROJECTS=ROOT/'Projects'; PROJECTS.mkdir(exist_ok=True)
app=Flask(__name__,template_folder=str(ROOT/'web'/'templates'))
lock=threading.Lock(); cancel_event=threading.Event()
job={'state':'idle','percent':0,'message':'Siap','logs':[]}
QUALITIES={'480p':(854,480),'720p':(1280,720),'1080p':(1920,1080),'1440p':(2560,1440),'2160p':(3840,2160)}

def log(msg):
    with lock: job.setdefault('logs',[]).append(str(msg)); job['logs']=job['logs'][-150:]
def snapshot():
    with lock: return json.loads(json.dumps(job))
def slug(s):
    s=re.sub(r'[^a-zA-Z0-9_-]+','-',str(s).strip()).strip('-_')
    return s[:60] or 'project'
def project_dir(name): return PROJECTS/slug(name)
def project_file(name): return project_dir(name)/'project.json'
def safe_file(folder,name,exts):
    p=(ROOT/folder/secure_filename(name)).resolve(); base=(ROOT/folder).resolve()
    if p.parent!=base or p.suffix.lower() not in exts or not p.is_file(): raise ValueError(f'File {folder} tidak valid')
    return p
def theme_path(rel):
    p=(ROOT/rel).resolve(); base=(ROOT/'Themes').resolve()
    if base not in p.parents or p.suffix.lower()!='.json' or not p.is_file(): raise ValueError('Theme tidak valid')
    return p
def project_theme(name):
    p=project_dir(name)/'scene.json'
    return p if p.is_file() else None
def files_payload():
    themes=discover_themes(ROOT/'Themes')
    return {'themes':[{'id':str(t.path.relative_to(ROOT)),'name':f'{t.path.parent.name} / {t.path.name}'} for t in themes],
      'music':[p.name for p in scan(ROOT/'Music',AUDIO_EXT)],'backgrounds':[p.name for p in scan(ROOT/'BackGround',IMAGE_EXT)],
      'logos':[p.name for p in scan(ROOT/'Logo',IMAGE_EXT)],'qualities':list(QUALITIES.keys()),
      'projects':sorted([p.name for p in PROJECTS.iterdir() if p.is_dir() and (p/'project.json').is_file()])}

@app.get('/')
def index(): return render_template('index.html')
@app.get('/api/files')
def api_files():
    d=files_payload(); p=detect_profile(); d['performance']=describe(p); d['encoder']=p['encoder_label']; return jsonify(d)
@app.get('/api/status')
def api_status(): return jsonify(snapshot())
@app.get('/api/theme')
def api_theme():
    p=theme_path(request.args.get('theme','')); t=Theme(p)
    return jsonify({'path':str(p.relative_to(ROOT)),'data':t.data,'report':t.report(SceneRenderer.SUPPORTED,SceneRenderer.SUPPORTED_MEASURES)})
@app.get('/api/project/<name>')
def api_project(name):
    p=project_file(name)
    if not p.is_file(): return jsonify({'error':'Project tidak ditemukan'}),404
    d=json.loads(p.read_text(encoding='utf8')); tp=project_theme(name)
    if tp: d['theme_data']=json.loads(tp.read_text(encoding='utf8'))
    return jsonify(d)
@app.post('/api/project')
def api_save_project():
    d=request.get_json(force=True); name=slug(d.get('name','project')); pd=project_dir(name); pd.mkdir(parents=True,exist_ok=True)
    cfg={k:d.get(k) for k in ('name','theme','music','background','logo','orientation','quality')}
    cfg['name']=name; project_file(name).write_text(json.dumps(cfg,indent=2),encoding='utf8')
    if isinstance(d.get('theme_data'),dict):
        (pd/'scene.json').write_text(json.dumps(d['theme_data'],indent=2),encoding='utf8')
    return jsonify({'ok':True,'name':name})
@app.delete('/api/project/<name>')
def api_delete_project(name):
    pd=project_dir(name)
    if pd.exists(): shutil.rmtree(pd)
    return jsonify({'ok':True})
@app.post('/api/upload/<kind>')
def api_upload(kind):
    mapping={'music':('Music',AUDIO_EXT),'background':('BackGround',IMAGE_EXT),'logo':('Logo',IMAGE_EXT)}
    if kind not in mapping or 'file' not in request.files: return jsonify({'error':'Upload tidak valid'}),400
    folder,exts=mapping[kind]; f=request.files['file']; name=secure_filename(f.filename)
    if Path(name).suffix.lower() not in exts: return jsonify({'error':'Format file tidak didukung'}),400
    dest=ROOT/folder/name; dest.parent.mkdir(exist_ok=True); f.save(dest)
    return jsonify({'ok':True,'name':name})
@app.post('/api/cancel')
def api_cancel():
    if snapshot().get('state')=='rendering': cancel_event.set(); log('Permintaan cancel diterima.')
    return jsonify({'ok':True})
@app.get('/media/<kind>/<path:name>')
def media(kind,name):
    mapping={'music':'Music','background':'BackGround','logo':'Logo'}
    if kind not in mapping: return jsonify({'error':'Media tidak valid'}),404
    return send_from_directory(ROOT/mapping[kind],secure_filename(name))

@app.get('/output/<path:name>')
def output(name): return send_from_directory(ROOT/'Output',name,as_attachment=True)

@app.post('/api/render')
def api_render():
    global job
    if snapshot().get('state')=='rendering': return jsonify({'error':'Render lain masih berjalan.'}),409
    d=request.get_json(force=True)
    try:
        pname=slug(d.get('project','')) if d.get('project') else ''
        tp=project_theme(pname) if pname else None
        theme=Theme(tp if tp else theme_path(d['theme']))
        music=safe_file('Music',d['music'],AUDIO_EXT); bg=safe_file('BackGround',d['background'],IMAGE_EXT); logo=safe_file('Logo',d['logo'],IMAGE_EXT)
        quality=d.get('quality','720p')
        if quality not in QUALITIES: raise ValueError('Kualitas tidak valid')
        w,h=QUALITIES[quality]
        if d.get('orientation')=='portrait': w,h=h,w
    except (KeyError,ValueError,OSError,json.JSONDecodeError) as e: return jsonify({'error':str(e)}),400
    profile=detect_profile(); filename=secure_filename(d.get('output_name') or f'{music.stem}_visualizer')+'.mp4'; out=ROOT/'Output'/filename; out.parent.mkdir(exist_ok=True)
    cancel_event.clear()
    with lock: job={'state':'rendering','percent':0,'frame':0,'total_frames':0,'render_fps':0,'realtime':0,'elapsed':0,'eta':0,'message':'Menganalisis audio...','output':out.name,'logs':[]}
    report=theme.report(SceneRenderer.SUPPORTED,SceneRenderer.SUPPORTED_MEASURES)
    log(f"Theme: {theme.path.name} | {report['compositions']} compositions | {report['elements']} elements")
    log(f"Encoder: {profile['encoder_label']} | {w}x{h} | 30 FPS")
    def progress(info):
        with lock: job.update(info); job['message']='Rendering frame...'
    def worker():
        try:
            render_video(theme,music,bg,logo,out,w,h,30,18,profile['preset'],profile['encoder'],profile['cores'],progress_cb=progress,cancel_event=cancel_event)
            with lock: job.update({'state':'done','percent':100,'message':'Render selesai.'})
            log(f'Selesai: {out.name}')
        except RenderCancelled:
            out.unlink(missing_ok=True)
            with lock: job.update({'state':'cancelled','message':'Render dibatalkan.'})
        except Exception as e:
            out.unlink(missing_ok=True)
            with lock: job.update({'state':'error','message':str(e)})
            log(f'ERROR: {e}')
    threading.Thread(target=worker,daemon=True).start(); return jsonify({'ok':True,'output':out.name})

def run_web(host='127.0.0.1',port=8080,open_browser=True):
    if open_browser: threading.Timer(1.0,lambda:webbrowser.open(f'http://{host}:{port}')).start()
    app.run(host=host,port=port,debug=False,threaded=True,use_reloader=False)
if __name__=='__main__': run_web()
