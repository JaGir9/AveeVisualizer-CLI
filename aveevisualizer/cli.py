import argparse, shutil
from pathlib import Path
from .theme import discover_themes
from .media import scan, IMAGE_EXT, AUDIO_EXT, RotationState
from .render import render_video, SceneRenderer
from .performance import detect_profile, describe
ROOT=Path(__file__).resolve().parents[1]
def require_ffmpeg():
    if not shutil.which('ffmpeg'): raise SystemExit('ERROR: FFmpeg tidak ditemukan di PATH.')
def choose(title,files):
    print(f'\n{title}:')
    for i,p in enumerate(files,1): print(f'  [{i}] {p.name}')
    while True:
        try:
            n=int(input('Pilih nomor: ').strip())
            if 1<=n<=len(files): return files[n-1]
        except (ValueError,EOFError): pass
        print('Pilihan tidak valid.')
def choose_theme():
    themes=discover_themes(ROOT/'Themes')
    if not themes: raise SystemExit('ERROR: Tidak ada theme JSON valid di Themes/.')
    if len(themes)==1:
        print(f'\nTheme: {themes[0].path.parent.name} (otomatis)'); return themes[0]
    print('\nTheme terdeteksi:')
    for i,t in enumerate(themes,1): print(f'  [{i}] {t.path.parent.name} — {t.path.name}')
    while True:
        try:
            n=int(input('Pilih theme: ').strip())
            if 1<=n<=len(themes): return themes[n-1]
        except (ValueError,EOFError): pass
        print('Pilihan tidak valid.')
def scan_all(): return scan(ROOT/'Music',AUDIO_EXT),scan(ROOT/'BackGround',IMAGE_EXT),scan(ROOT/'Logo',IMAGE_EXT)
def ensure(x,n):
    if not x: raise SystemExit(f'ERROR: Folder {n}/ kosong.')
def output_name(m): return ROOT/'Output'/f'{m.stem}_visualizer.mp4'
def do_render(theme,m,b,l,args):
    out=output_name(m); out.parent.mkdir(exist_ok=True)
    print(f'\nRender:\n  Theme     : {theme.path.parent.name}\n  Music     : {m.name}\n  Background: {b.name}\n  Logo      : {l.name}\n  Output    : {out.name}')
    render_video(theme,m,b,l,out,args.width,args.height,args.fps,args.crf,args.preset,args.encoder,args.threads); print('SELESAI:',out)
def choose_orientation(args):
    print('\nPilih orientasi:\n  [1] Horizontal / Landscape\n  [2] Vertical / Portrait')
    while True:
        n=input('Pilih orientasi: ').strip()
        if n in ('1','2'): args.orientation=n; return
        print('Pilihan tidak valid.')
def choose_quality(args):
    ps=[('480p',854,480),('720p HD',1280,720),('1080p Full HD',1920,1080),('2K / 1440p QHD',2560,1440),('4K / 2160p UHD',3840,2160)]
    print('\nPilih kualitas:')
    for i,(n,w,h) in enumerate(ps,1): print(f'  [{i}] {n:<17} {w}x{h}')
    while True:
        try:
            i=int(input('Pilih kualitas: ').strip())-1
            if 0<=i<len(ps):
                n,w,h=ps[i]; args.width,args.height=((h,w) if args.orientation=='2' else (w,h)); print(f'Kualitas: {n} ({args.width}x{args.height})'); return
        except (ValueError,EOFError): pass
        print('Pilihan tidak valid.')
def interactive(args):
    theme=choose_theme(); inv=theme.inventory(); unsupported=theme.unsupported(SceneRenderer.SUPPORTED)
    print('Theme elements:',', '.join(f'{k}={v}' for k,v in inv.items()))
    if unsupported: print('PERINGATAN objType belum didukung:',', '.join(unsupported))
    music,bgs,logos=scan_all(); ensure(music,'Music'); ensure(bgs,'BackGround'); ensure(logos,'Logo')
    print('\n=========================================\n        AveeVisualizer-CLI\n========================================='); print(f'Music: {len(music)} | BackGround: {len(bgs)} | Logo: {len(logos)}'); print('\n[1] Manual\n[2] Otomatis / Berurutan')
    mode=input('\nPilih mode: ').strip()
    if mode not in ('1','2'): raise SystemExit('Pilihan tidak valid.')
    choose_orientation(args); choose_quality(args)
    if mode=='1':
        m=choose('Pilih Music',music); b=bgs[0] if len(bgs)==1 else choose('Pilih BackGround',bgs); l=logos[0] if len(logos)==1 else choose('Pilih Logo',logos); do_render(theme,m,b,l,args)
    else:
        state=RotationState(ROOT/'.state.json'); start=state.get('music')%len(music)
        for m in music[start:]+music[:start]:
            b=bgs[0] if len(bgs)==1 else bgs[state.get('background')%len(bgs)]; l=logos[0] if len(logos)==1 else logos[state.get('logo')%len(logos)]
            do_render(theme,m,b,l,args); state.advance('music',len(music)); state.advance('background',len(bgs)); state.advance('logo',len(logos)); state.save()
def main():
    ap=argparse.ArgumentParser(prog='AveeVisualizer-CLI'); ap.add_argument('--width',type=int,default=1920); ap.add_argument('--height',type=int,default=1080); ap.add_argument('--fps',type=int,default=30); ap.add_argument('--crf',type=int,default=18); ap.add_argument('--preset',default='medium',choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow']); ap.add_argument('--reset-state',action='store_true'); ap.add_argument('--check-themes',action='store_true',help='Audit semua theme tanpa render'); args=ap.parse_args(); require_ffmpeg(); p=detect_profile(); args.encoder=p['encoder']; args.threads=p['cores']; args.preset=p['preset'] if args.preset=='medium' else args.preset; print('\nAuto Performance:',describe(p))
    if args.reset_state: (ROOT/'.state.json').unlink(missing_ok=True); print('State berhasil di-reset.'); return
    interactive(args)
if __name__=='__main__': main()
