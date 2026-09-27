import subprocess, numpy as np

class AudioAnalysis:
    def __init__(self,path,fps=30,sr=44100,settings=None):
        s=settings or {}; self.path=str(path); self.fps=fps; self.sr=sr
        self.lower=float(s.get('lowerHz',45)); self.higher=max(self.lower+1,float(s.get('higherHz',300)))
        self.bands=max(8,int(s.get('sampleOutCount',200))); self.smooth=float(s.get('smooth',1.5)); self.beat_smooth=float(s.get('beatSmooth',.4))
        self.mult=float(s.get('outputMultiplier',1))
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',self.path,'-f','f32le','-ac','1','-ar',str(sr),'-'])
        self.samples=np.frombuffer(raw,dtype=np.float32); self.duration=len(self.samples)/sr; self.hop=max(1,int(sr/fps))
        fs=int(s.get('fftSize',13)); self.win=(1<<fs) if 7<=fs<=18 else 8192
        self.window=np.hanning(self.win).astype(np.float32); self.freqs=np.fft.rfftfreq(self.win,1/sr)
        linear=float(s.get('hzLinearFactor',1)); x=np.linspace(0,1,self.bands+1); log=self.lower*(self.higher/self.lower)**x; lin=self.lower+(self.higher-self.lower)*x
        self.edges=log*(1-linear)+lin*linear; self.prev=np.zeros(self.bands,np.float32); self.energy_avg=1e-4; self.beat_state=0.
    def frame(self,i):
        center=i*self.hop; start=center-self.win//2; x=np.zeros(self.win,np.float32); a=max(0,start); b=min(len(self.samples),start+self.win)
        if b>a: x[a-start:b-start]=self.samples[a:b]
        mag=np.abs(np.fft.rfft(x*self.window)); vals=np.zeros(self.bands,np.float32)
        for j in range(self.bands):
            m=(self.freqs>=self.edges[j])&(self.freqs<self.edges[j+1]); vals[j]=mag[m].mean() if m.any() else 0
        vals=np.log1p(vals*20)*self.mult; peak=max(float(np.percentile(vals,98)),1e-6); vals=np.clip(vals/peak,0,1)
        alpha=np.clip(1/(1+max(.1,self.smooth)),.05,.9); vals=self.prev*(1-alpha)+vals*alpha; self.prev=vals
        lo=max(1,int(self.bands*.2)); energy=float(vals[:lo].mean()); delta=max(0,energy-self.energy_avg); self.energy_avg=.94*self.energy_avg+.06*energy
        rawbeat=np.clip(delta/(self.energy_avg*.22+1e-5),0,1); ba=np.clip(1-max(0,self.beat_smooth)*.75,.1,.9); self.beat_state=self.beat_state*(1-ba)+rawbeat*ba
        return vals.copy(),float(self.beat_state),energy
