import math, random, subprocess, sys, time, colorsys, threading
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .audio import AudioAnalysis
RESAMPLE=Image.Resampling.LANCZOS

def cover(img,w,h):
    img=img.convert('RGBA'); s=max(w/img.width,h/img.height); nw,nh=round(img.width*s),round(img.height*s); img=img.resize((nw,nh),RESAMPLE)
    return img.crop(((nw-w)//2,(nh-h)//2,(nw-w)//2+w,(nh-h)//2+h))
def fit(img,w,h):
    img=img.convert('RGBA'); s=min(w/img.width,h/img.height); return img.resize((max(1,round(img.width*s)),max(1,round(img.height*s))),RESAMPLE)
def fv(theme,e,k,d=0):
    try:return float(theme.value(e.get(k),d))
    except:return float(d)
def f2(theme,e,k,d=(0,0)):
    v=str(theme.value(e.get(k),f'{d[0]} {d[1]}')).split()
    try:return float(v[0]),float(v[1])
    except:return d
def vignette(w,h):
    y,x=np.ogrid[-1:1:complex(h),-1:1:complex(w)]; r=np.sqrt(x*x+y*y); a=np.clip((r-.35)/.75,0,1); arr=np.zeros((h,w,4),np.uint8); arr[...,3]=(a*205).astype(np.uint8)
    return Image.fromarray(arr,'RGBA')
def particle_tex(size=64):
    y,x=np.ogrid[-1:1:complex(size),-1:1:complex(size)]; a=np.clip(1-np.sqrt(x*x+y*y),0,1)**2; arr=np.full((size,size,4),255,np.uint8); arr[...,3]=(a*255).astype(np.uint8)
    return Image.fromarray(arr,'RGBA')
def hsla(v,default=(1,1,1,1)):
    try:
        p=[float(x) for x in str(v).split()]; h,s,l,a=(p+[1,1,1,1])[:4]; r,g,b=colorsys.hls_to_rgb(h%1,l,max(0,min(1,s))); return (int(r*255),int(g*255),int(b*255),int(max(0,min(1,a))*255))
    except:return default
def int_rgba(v,default=(255,255,255,255)):
    try:
        n=int(v)&0xffffffff; return ((n>>16)&255,(n>>8)&255,n&255,(n>>24)&255 or 255)
    except:return default
def lerp_color(a,b,x): return tuple(int(a[i]+(b[i]-a[i])*max(0,min(1,x))) for i in range(4))
def tint(im,c):
    a=np.asarray(im,dtype=np.uint16).copy()
    for i in range(4): a[...,i]=(a[...,i]*c[i]//255)
    return Image.fromarray(a.astype(np.uint8),'RGBA')
def blend(base,layer,mode='Alpha'):
    if mode in ('Add','AddAlpha','Screen'):
        a=np.asarray(base,dtype=np.uint16); b=np.asarray(layer,dtype=np.uint16); out=np.minimum(255,a+b*(b[...,3:4]/255)).astype(np.uint8); return Image.fromarray(out,'RGBA')
    return Image.alpha_composite(base,layer)

class SceneRenderer:
    SUPPORTED={'AudioProvider','Image','Bars','Particles','BlurEffect','MotionBlurEffect'}
    SUPPORTED_MEASURES={'Nothing','Beat','TotalTime','TotalTimeBackward','TotalTimeWhenPlaying','TotalTimeAndBeat','TrackPosition','BeatRandomShake','BeatCamShakeMore','BeatCamShakeLess','BeatCamShakeRotMore','BeatCamShakeRotLess','ConstantShakeMore','ConstantShakeLess','ConstantShakeRotMore','ConstantShakeRotLess','BeatTriggerAnim'}
    def __init__(self,theme,bg_path,logo_path,w,h,fps,analysis):
        self.t=theme; self.w=w; self.h=h; self.fps=fps; self.a=analysis; self.bg=Image.open(bg_path).convert('RGBA'); self.logo=Image.open(logo_path).convert('RGBA')
        self.vig=vignette(w,h); self.pt=particle_tex(); self.history={}; self.rng=random.Random(7719); self.particles=[]; self._frame_cache={}
    def measure(self,e,key,beat,t):
        what,A,B=self.t.measure(e,key)
        if what=='Beat': return (A*beat,B*beat)
        if what in ('TotalTime','TotalTimeWhenPlaying'): return (A*t,B*t)
        if what=='TotalTimeBackward': return (-A*t,-B*t)
        if what=='TotalTimeAndBeat': return (A*t+A*beat,B*t+B*beat)
        if what=='TrackPosition':
            p=min(1,max(0,t/max(self.a.duration,1e-6))); return (A*p,B*p)
        if what=='BeatTriggerAnim': return (A*beat,B*beat)
        if what in ('BeatRandomShake','BeatCamShakeMore','BeatCamShakeLess','BeatCamShakeRotMore','BeatCamShakeRotLess'):
            strength=beat*A*(.5 if what in ('BeatCamShakeLess','BeatCamShakeRotLess') else 1); speed=max(.1,B); return (math.sin(t*31*speed)*strength,math.cos(t*27*speed)*strength)
        if what in ('ConstantShakeMore','ConstantShake','ConstantShakeLess','ConstantShakeRotMore','ConstantShakeRotLess'): return (math.sin(t*20*max(.1,B))*A,math.cos(t*17*max(.1,B))*A)
        return (0,0)
    def scalar_measure(self,e,key,beat,t):
        what,A,B=self.t.measure(e,key)
        if what=='Nothing': return 0.
        if what=='Beat': return max(0,min(1,beat*max(A,B,1)))
        if what in ('TotalTime','TotalTimeWhenPlaying'): return (t*max(A,B,.01))%1
        if what=='TotalTimeBackward': return 1-((t*max(A,B,.01))%1)
        if what=='TotalTimeAndBeat': return ((t*max(A,.01))+beat*B)%1
        if what=='TrackPosition': return min(1,max(0,t/max(self.a.duration,1e-6)))
        if what=='BeatTriggerAnim': return max(0,min(1,beat*max(A,B,1)))
        return max(0,min(1,self.measure(e,key,beat,t)[0]))
    def element_color(self,e,beat,t,particle=False):
        if particle:
            c1=hsla(self.t.value(e.get('ColorFrom'),'0 0 1 1')); c2=hsla(self.t.value(e.get('ColorTo'),'0 0 1 1')); x=(math.sin(t*.7)+1)/2
        else:
            c1=hsla(self.t.value(e.get('Color'),'0 0 1 1')); c2=hsla(self.t.value(e.get('ColorTo'),self.t.value(e.get('Color'),'0 0 1 1'))); x=self.scalar_measure(e,'MeasureColorBlend',beat,t)
        return lerp_color(c1,c2,x)
    def transform(self,layer,e,beat,t):
        px,py=f2(self.t,e,'position',(.5,.5)); sx,sy=f2(self.t,e,'scale',(1,1)); dx,dy=self.measure(e,'MeasurePos',beat,t); msx,msy=self.measure(e,'measureScale',beat,t); sx=max(.001,sx+msx); sy=max(.001,sy+msy)
        nw=max(1,int(self.w*sx)); nh=max(1,int(self.h*sy)); im=layer.resize((nw,nh),RESAMPLE) if (nw,nh)!=(self.w,self.h) else layer
        rot=fv(self.t,e,'rotation',0); mr=self.measure(e,'measureRot',beat,t)[0]; angle=rot+mr*360
        if abs(angle)>.001: im=im.rotate(-angle,RESAMPLE,expand=False)
        canvas=Image.new('RGBA',(self.w,self.h)); x=int((px+dx)*self.w-nw/2); y=int((py+dy)*self.h-nh/2); canvas.alpha_composite(im,(x,y)); return canvas
    def image_element(self,e,beat,t,stack):
        src=str(self.t.value(e.get('customImage'),'') or ''); tag=self.t.tag(e); ref=self.t.ref(e,'customImage')
        if tag.lower()=='background': im=cover(self.bg,self.w,self.h)
        elif tag.lower()=='logo':
            box=max(8,min(self.w,self.h)); im0=fit(self.logo,box,box); im=Image.new('RGBA',(self.w,self.h)); im.alpha_composite(im0,((self.w-im0.width)//2,(self.h-im0.height)//2))
        elif ref is not None: im=self.composition(ref,beat,t,stack)
        elif src=='internalres:vignette80': im=self.vig.copy()
        elif src=='internalres:black': im=Image.new('RGBA',(self.w,self.h),(0,0,0,255))
        elif src=='internalres:white': im=Image.new('RGBA',(self.w,self.h),(255,255,255,255))
        else: im=Image.new('RGBA',(self.w,self.h))
        im=tint(im,self.element_color(e,beat,t))
        opacity=max(0,min(4,fv(self.t,e,'opacityStrength',1)))
        if opacity!=1:
            im.putalpha(im.getchannel('A').point(lambda x:min(255,int(x*opacity))))
        if bool(self.t.value(e.get('blurEnabled'),0)): im=im.filter(ImageFilter.GaussianBlur(max(0,fv(self.t,e,'blurRadius',1))))
        if str(self.t.value(e.get('Shape'),'None'))=='Circle':
            sx,sy=f2(self.t,e,'scale',(.3,.3)); r=int(min(self.w,self.h)*max(sx,sy)/2); mask=Image.new('L',(self.w,self.h)); ImageDraw.Draw(mask).ellipse((self.w//2-r,self.h//2-r,self.w//2+r,self.h//2+r),fill=255); im.putalpha(mask)
        return self.transform(im,e,beat,t)
    def bars(self,e,spec,beat,t):
        layer=Image.new('RGBA',(self.w,self.h)); d=ImageDraw.Draw(layer); sx,_=f2(self.t,e,'scale',(.31,.31)); r=min(self.w,self.h)*sx/2; height=fv(self.t,e,'heightScale',2.5); mx=fv(self.t,e,'maxHeightScale',4); delay=max(0,int(fv(self.t,e,'reactionDelay',0))); hist=self.history.get('spec',[spec]); src=hist[max(0,len(hist)-1-min(delay,len(hist)-1))]
        if bool(self.t.value(e.get('flipInput'),0)): src=src[::-1]
        n=min(len(src),200); cx,cy=self.w/2,self.h/2; seg=e.get('Segment1',{}); mult=fv(self.t,seg,'barHeightMultiplier',.4); fixed=fv(self.t,seg,'fixedHeight',0); color=int_rgba(self.t.value(seg.get('colorFrom'),-1)); lw=max(1,int(min(self.w,self.h)*.0018))
        for j in range(n):
            a=2*math.pi*j/n-math.pi/2; val=float(src[j]); L=min(self.w,self.h)*.03*(fixed+mult*min(mx,max(fv(self.t,e,'minHeightScale',0),height*val))); x1=cx+math.cos(a)*r; y1=cy+math.sin(a)*r; x2=cx+math.cos(a)*(r+L); y2=cy+math.sin(a)*(r+L); d.line((x1,y1,x2,y2),fill=color,width=lw)
        soft=fv(self.t,e,'softnessRadius',fv(self.t,e,'softness',0)); return layer.filter(ImageFilter.GaussianBlur(max(0,(soft-8)*.18))) if soft>8 else layer
    def particles_layer(self,e,beat,t):
        count=min(1000,max(1,int(fv(self.t,e,'CountLimit',1000)))); spawn=max(.005,fv(self.t,e,'spawnTime',.05)); desired=min(count,max(1,int(t/spawn)+1)); speed=fv(self.t,e,'OverallSpeed',1)
        while len(self.particles)<desired:self.particles.append([self.rng.random()*self.w,self.rng.random()*self.h,self.rng.uniform(-1,1),self.rng.uniform(-1,1)])
        layer=Image.new('RGBA',(self.w,self.h)); scale=max(.2,fv(self.t,e,'particleScale',1)); sz=max(2,int(min(self.w,self.h)*.004*scale)); tex=self.pt.resize((sz,sz),RESAMPLE); pcolor=self.element_color(e,beat,t,True); tex=tint(tex,pcolor); measured=self.measure(e,'MeasureOverallSpeed',beat,t)[0]; speed=(fv(self.t,e,'Speed',60)/60.0)*(1+measured)
        for p in self.particles:
            p[0]=(p[0]+p[2]*speed)%self.w; p[1]=(p[1]+p[3]*speed)%self.h; alpha=int(80+150*beat); q=tex.copy(); q.putalpha(q.getchannel('A').point(lambda x:x*alpha//255)); layer.alpha_composite(q,(int(p[0]-sz/2),int(p[1]-sz/2)))
        return layer
    def composition(self,idx,beat,t,stack=None):
        if idx in self._frame_cache: return self._frame_cache[idx].copy()
        stack=set() if stack is None else set(stack)
        if idx in stack:return Image.new('RGBA',(self.w,self.h))
        stack.add(idx); comp=self.t.composition(idx); out=Image.new('RGBA',(self.w,self.h))
        if not comp:return out
        spec=self.history['spec'][-1]
        for e in comp.get('elements',[]):
            if not bool(self.t.value(e.get('visible'),1)):continue
            typ=e.get('objType'); mode=str(self.t.value(e.get('blendMode'),'Alpha'))
            if typ=='AudioProvider':continue
            if typ=='Image':layer=self.image_element(e,beat,t,stack)
            elif typ=='Bars':layer=self.bars(e,spec,beat,t)
            elif typ=='Particles':layer=self.particles_layer(e,beat,t)
            elif typ=='BlurEffect':
                ref=self.t.ref(e,'sourceComposition')
                if ref is None:
                    try: ref=int(self.t.value(e.get('sourceCompositionIndex')))
                    except (TypeError,ValueError): ref=None
                layer=self.composition(ref,beat,t,stack) if ref is not None else out.copy(); rad=fv(self.t,e,'blurRadius',1)*fv(self.t,e,'blurMultiplier',1); layer=layer.filter(ImageFilter.GaussianBlur(max(0,rad)))
            elif typ=='MotionBlurEffect':
                ref=self.t.ref(e,'TargetImage'); layer=self.composition(ref,beat,t,stack) if ref is not None else out.copy(); parts=str(self.t.value(e.get('blurAmountMultiplier'),'Constant 1 1')).split()
                try:amount=max(.01,float(parts[1]))
                except:amount=1
                copies=max(2,min(8,int(2+amount*8))); acc=Image.new('RGBA',(self.w,self.h)); dx,dy=self.measure(e,'MeasurePos',beat,t)
                for k in range(copies):
                    offx=int(dx*self.w*k/copies*.02); offy=int(dy*self.h*k/copies*.02); tmp=Image.new('RGBA',(self.w,self.h)); tmp.alpha_composite(layer,(offx,offy)); acc=blend(acc,tmp,'AddAlpha')
                layer=acc
            else:continue
            out=blend(out,layer,mode)
        self._frame_cache[idx]=out.copy()
        return out
    def frame(self,i,spec,beat,bass):
        self._frame_cache.clear(); self.history.setdefault('spec',[]).append(spec); self.history['spec']=self.history['spec'][-16:]; return self.composition(0,beat,i/self.fps)

class RenderCancelled(RuntimeError): pass

def render_video(theme,audio_path,bg_path,logo_path,out_path,width=1920,height=1080,fps=30,crf=18,preset='medium',encoder='libx264',threads=0,progress_cb=None,cancel_event=None):
    analysis=AudioAnalysis(audio_path,fps=fps,settings=theme.audio_settings()); scene=SceneRenderer(theme,bg_path,logo_path,width,height,fps,analysis); total=max(1,math.ceil(analysis.duration*fps))
    enc=['-c:v','libx264','-preset',preset,'-crf',str(crf),'-threads',str(max(1,threads))]
    if encoder=='h264_nvenc':enc=['-c:v','h264_nvenc','-preset','p4','-cq',str(crf)]
    elif encoder=='h264_qsv':enc=['-c:v','h264_qsv','-preset','veryfast','-global_quality',str(crf)]
    elif encoder=='h264_amf':enc=['-c:v','h264_amf','-quality','speed','-qp_i',str(crf),'-qp_p',str(crf)]
    elif encoder=='h264_videotoolbox':enc=['-c:v','h264_videotoolbox','-q:v','65']
    cmd=['ffmpeg','-y','-v','warning','-f','rawvideo','-pix_fmt','rgba','-s',f'{width}x{height}','-r',str(fps),'-i','-','-i',str(audio_path),'-map','0:v:0','-map','1:a:0']+enc+['-pix_fmt','yuv420p','-c:a','aac','-b:a','320k','-shortest',str(out_path)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE); started=time.perf_counter(); last=-1
    try:
        for i in range(total):
            if cancel_event is not None and cancel_event.is_set(): raise RenderCancelled('Render dibatalkan.')
            spec,beat,bass=analysis.frame(i); frame=scene.frame(i,spec,beat,bass); p.stdin.write(np.asarray(frame,dtype=np.uint8).tobytes()); pct=int((i+1)*100/total)
            if pct!=last:
                elapsed=max(time.perf_counter()-started,1e-6); rf=(i+1)/elapsed; eta=max(0,(total-i-1)/max(rf,1e-6)); sys.stdout.write(f'\r  Render {pct:3d}% | {rf:5.1f} fps | {rf/fps:4.2f}x realtime'); sys.stdout.flush(); last=pct
                if progress_cb: progress_cb({'percent':pct,'frame':i+1,'total_frames':total,'render_fps':rf,'realtime':rf/fps,'elapsed':elapsed,'eta':eta})
    finally:
        if p.stdin:p.stdin.close()
        rc=p.wait(); print()
    if rc:raise RuntimeError(f'FFmpeg gagal dengan kode {rc}')
    return out_path
