import subprocess, numpy as np

class AudioAnalysis:
    def __init__(self, path, fps=30, sr=44100, lower_hz=45, higher_hz=16000, bands=96):
        self.path=str(path); self.fps=fps; self.sr=sr; self.lower_hz=lower_hz; self.higher_hz=max(higher_hz, lower_hz+100); self.bands=bands
        cmd=['ffmpeg','-v','error','-i',self.path,'-f','f32le','-ac','1','-ar',str(sr),'-']
        raw=subprocess.check_output(cmd)
        self.samples=np.frombuffer(raw,dtype=np.float32)
        self.duration=len(self.samples)/sr
        self.hop=max(1,int(sr/fps)); self.win=1
        while self.win < self.hop*2: self.win*=2
        self.window=np.hanning(self.win).astype(np.float32)
        self.freqs=np.fft.rfftfreq(self.win,1/sr)
        self.edges=np.geomspace(max(20,lower_hz),min(sr/2-1,self.higher_hz),bands+1)
        self.prev_energy=0.; self.flux_avg=1e-4

    def frame(self, i):
        center=i*self.hop; start=max(0,center-self.win//2); x=np.zeros(self.win,np.float32)
        chunk=self.samples[start:min(len(self.samples),start+self.win)]; x[:len(chunk)]=chunk
        mag=np.abs(np.fft.rfft(x*self.window)); mag=np.log1p(mag*20)
        vals=np.zeros(self.bands,np.float32)
        for b in range(self.bands):
            m=(self.freqs>=self.edges[b])&(self.freqs<self.edges[b+1])
            if m.any(): vals[b]=mag[m].mean()
        peak=max(float(vals.max()),1e-6); vals=np.clip(vals/peak,0,1)
        bass=float(vals[:max(3,self.bands//8)].mean())
        energy=float(np.sqrt(np.mean(x*x))+1e-8)
        flux=max(0.,energy-self.prev_energy); self.prev_energy=energy
        self.flux_avg=.94*self.flux_avg+.06*flux
        beat=np.clip(flux/(self.flux_avg*2.2+1e-6),0,1)
        return vals, float(beat), bass
