import argparse, shutil
from pathlib import Path
from .theme import Theme
from .media import scan, IMAGE_EXT, AUDIO_EXT, RotationState
from .render import render_video

ROOT=Path(__file__).resolve().parents[1]

def require_ffmpeg():
    if not shutil.which('ffmpeg'):
        raise SystemExit('ERROR: FFmpeg tidak ditemukan di PATH. Install FFmpeg terlebih dahulu.')

def choose(title, files):
    print(f'\n{title}:')
    for i,p in enumerate(files,1): print(f'  [{i}] {p.name}')
    while True:
        try:
            n=int(input('Pilih nomor: ').strip())
            if 1<=n<=len(files): return files[n-1]
        except (ValueError,EOFError): pass
        print('Pilihan tidak valid.')

def scan_all(root):
    return scan(root/'Music',AUDIO_EXT),scan(root/'BackGround',IMAGE_EXT),scan(root/'Logo',IMAGE_EXT)

def ensure(files,name):
    if not files: raise SystemExit(f'ERROR: Folder {name}/ kosong. Tambahkan minimal 1 file.')

def output_name(music): return ROOT/'Output'/f'{music.stem}_visualizer.mp4'

def do_render(theme,music,bg,logo,args):
    out=output_name(music); out.parent.mkdir(exist_ok=True)
    print('\nRender:'); print('  Music     :',music.name); print('  Background:',bg.name); print('  Logo      :',logo.name); print('  Output    :',out.name)
    render_video(theme,music,bg,logo,out,args.width,args.height,args.fps,args.crf,args.preset)
    print('SELESAI:',out)

def choose_quality(args):
    presets = [
        ("480p", 854, 480),
        ("720p HD", 1280, 720),
        ("1080p Full HD", 1920, 1080),
        ("2K / 1440p QHD", 2560, 1440),
        ("4K / 2160p UHD", 3840, 2160),
    ]
    print("\nPilih kualitas hasil video:")
    for i, (name, w, h) in enumerate(presets, 1):
        print(f"  [{i}] {name:<17} {w}x{h}")
    while True:
        try:
            n = int(input("Pilih kualitas: ").strip())
            if 1 <= n <= len(presets):
                name, args.width, args.height = presets[n-1]
                print(f"Kualitas: {name} ({args.width}x{args.height})")
                return
        except (ValueError, EOFError):
            pass
        print("Pilihan tidak valid.")

def interactive(args):
    theme=Theme(ROOT/'scene.json'); music,bgs,logos=scan_all(ROOT)
    ensure(music,'Music'); ensure(bgs,'BackGround'); ensure(logos,'Logo')
    print('\n=========================================\n        AveeVisualizer-CLI\n=========================================')
    print(f'Music: {len(music)} | BackGround: {len(bgs)} | Logo: {len(logos)}')
    print('\n[1] Manual\n[2] Otomatis / Berurutan')
    mode=input('\nPilih mode: ').strip()
    if mode not in ('1','2'): raise SystemExit('Pilihan tidak valid.')
    choose_quality(args)
    if mode=='1':
        m=choose('Pilih Music',music); b=bgs[0] if len(bgs)==1 else choose('Pilih BackGround',bgs); l=logos[0] if len(logos)==1 else choose('Pilih Logo',logos)
        do_render(theme,m,b,l,args)
    elif mode=='2':
        state=RotationState(ROOT/'.state.json')
        start=state.get('music')%len(music)
        ordered=music[start:]+music[:start]
        for m in ordered:
            b=bgs[0] if len(bgs)==1 else bgs[state.get('background')%len(bgs)]
            l=logos[0] if len(logos)==1 else logos[state.get('logo')%len(logos)]
            do_render(theme,m,b,l,args)
            state.advance('music',len(music)); state.advance('background',len(bgs)); state.advance('logo',len(logos)); state.save()


def main():
    ap=argparse.ArgumentParser(prog='AveeVisualizer-CLI',description='Independent audio-reactive CLI renderer inspired by an Avee visualizer scene.')
    ap.add_argument('--width',type=int,default=1920); ap.add_argument('--height',type=int,default=1080); ap.add_argument('--fps',type=int,default=30)
    ap.add_argument('--crf',type=int,default=18); ap.add_argument('--preset',default='medium',choices=['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'])
    ap.add_argument('--reset-state',action='store_true',help='Reset urutan otomatis lalu keluar')
    args=ap.parse_args(); require_ffmpeg()
    if args.reset_state:
        p=ROOT/'.state.json'; p.unlink(missing_ok=True); print('State berhasil di-reset.'); return
    interactive(args)
if __name__=='__main__': main()
