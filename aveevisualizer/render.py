import math, subprocess, sys, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from .audio import AudioAnalysis

RESAMPLE=Image.Resampling.LANCZOS

def cover(img,w,h):
    img=img.convert('RGB'); s=max(w/img.width,h/img.height)
    nw,nh=round(img.width*s),round(img.height*s)
    img=img.resize((nw,nh),RESAMPLE); x=(nw-w)//2; y=(nh-h)//2
    return img.crop((x,y,x+w,y+h))

def circle_logo(img,size):
    im=cover(img,size,size).convert('RGBA')
    mask=Image.new('L',(size,size)); ImageDraw.Draw(mask).ellipse((0,0,size-1,size-1),fill=255)
    im.putalpha(mask); return im

def render_video(theme,audio_path,bg_path,logo_path,out_path,width=1920,height=1080,fps=30,crf=18,preset='medium',encoder='libx264',threads=0):
    aset=theme.audio_settings(); vset=theme.visual_settings()
    analysis=AudioAnalysis(audio_path,fps=fps,lower_hz=aset['lower_hz'],higher_hz=max(16000,aset['higher_hz']),bands=96)
    bg=ImageEnhance.Contrast(cover(Image.open(bg_path),width,height)).enhance(1.05)
    base_radius=int(min(width,height)*vset['circle_scale']/2)
    logo_src=Image.open(logo_path)
    total=max(1,math.ceil(analysis.duration*fps))
    encopts=[]
    if encoder=='libx264':
        encopts=['-c:v','libx264','-preset',preset,'-crf',str(crf),'-threads',str(max(1,threads))]
    elif encoder=='h264_nvenc':
        encopts=['-c:v','h264_nvenc','-preset','p4','-cq',str(crf)]
    elif encoder=='h264_qsv':
        encopts=['-c:v','h264_qsv','-preset','veryfast','-global_quality',str(crf)]
    elif encoder=='h264_amf':
        encopts=['-c:v','h264_amf','-quality','speed','-qp_i',str(crf),'-qp_p',str(crf)]
    elif encoder=='h264_videotoolbox':
        encopts=['-c:v','h264_videotoolbox','-q:v','65']
    else:
        encopts=['-c:v','libx264','-preset','veryfast','-crf',str(crf)]
    cmd=['ffmpeg','-y','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r',str(fps),'-i','-','-i',str(audio_path),'-map','0:v:0','-map','1:a:0']+encopts+['-pix_fmt','yuv420p','-c:a','aac','-b:a','320k','-shortest',str(out_path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    history=[]
    started=time.perf_counter(); last_pct=-1
    try:
        for i in range(total):
            spec,beat,bass=analysis.frame(i)
            history.append(spec.copy()); history=history[-12:]
            pulse=1.0+0.055*beat+0.025*bass
            shake=int(min(width,height)*0.006*beat)
            sx=int(math.sin(i*2.13)*shake); sy=int(math.cos(i*1.71)*shake)
            frame=bg.transform(bg.size,Image.AFFINE,(1,0,-sx,0,1,-sy)).convert('RGBA')
            cx,cy=width//2,height//2
            layers=vset['bar_layers'] or [{"scale":vset['circle_scale'],"height":2.5,"delay":0,"softness":8}]
            for li,L in enumerate(layers[:4]):
                delay=min(max(0,L['delay']),len(history)-1)
                src=history[-1-delay]
                r=int(min(width,height)*L['scale']/2*pulse)
                overlay=Image.new('RGBA',(width,height),(0,0,0,0)); d=ImageDraw.Draw(overlay)
                n=min(96,len(src)); step=2*math.pi/n
                alpha=max(65,210-li*35); linew=max(2,int(min(width,height)*.0024))
                for j in range(n):
                    a=j*step-math.pi/2; val=float(src[j])
                    length=min(width,height)*(0.018+0.085*val)*(L['height']/3.0)
                    x1=cx+math.cos(a)*r; y1=cy+math.sin(a)*r
                    x2=cx+math.cos(a)*(r+length); y2=cy+math.sin(a)*(r+length)
                    d.line((x1,y1,x2,y2),fill=(255,255,255,alpha),width=linew)
                if L['softness']>10:
                    overlay=overlay.filter(ImageFilter.GaussianBlur((L['softness']-9)*.35))
                frame=Image.alpha_composite(frame,overlay)
            rr=int(base_radius*.92*pulse)
            ImageDraw.Draw(frame).ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=(0,0,0,205))
            ls=max(16,int(base_radius*1.75*pulse)); logo=circle_logo(logo_src,ls)
            frame.alpha_composite(logo,(cx-ls//2,cy-ls//2))
            p.stdin.write(np.asarray(frame.convert('RGB'),dtype=np.uint8).tobytes())
            pct=min(100,int(((i+1)*100)/total))
            if pct != last_pct:
                elapsed=max(time.perf_counter()-started,1e-6)
                render_fps=(i+1)/elapsed
                realtime=render_fps/fps
                sys.stdout.write(f'\r  Render {pct:3d}% | {render_fps:5.1f} fps | {realtime:4.2f}x realtime')
                sys.stdout.flush()
                last_pct=pct
    finally:
        if p.stdin: p.stdin.close()
        rc=p.wait()
    print()
    if rc: raise RuntimeError(f'FFmpeg gagal dengan kode {rc}')
    return out_path
