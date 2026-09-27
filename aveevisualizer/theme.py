import json, re
from pathlib import Path
from collections import Counter

class Theme:
    def __init__(self,path):
        self.path=Path(path); self.data=json.loads(self.path.read_text(encoding='utf8'))
        self.compositions=self.data.get('compositions',[])
    @staticmethod
    def value(x,default=None):
        return x.get('v',default) if isinstance(x,dict) else (default if x is None else x)
    def elements(self,obj_type=None):
        out=[]
        for ci,c in enumerate(self.compositions):
            for e in c.get('elements',[]):
                if obj_type is None or e.get('objType')==obj_type: out.append((ci,e))
        return out
    def composition(self,index): return self.compositions[index] if 0<=index<len(self.compositions) else None
    def element_id(self,e): return int(self.value(e.get('_id'),-1))
    def tag(self,e): return str(self.value(e.get('tag'),''))
    def measure(self,node,name):
        m=node.get(name,{}) if isinstance(node,dict) else {}
        return str(self.value(m.get('measureWhat'),'Nothing')), float(self.value(m.get('A'),0) or 0), float(self.value(m.get('B'),0) or 0)
    def ref(self,node,key):
        v=str(self.value(node.get(key),'') or ''); m=re.fullmatch(r'composition:(\d+)',v)
        return int(m.group(1)) if m else None
    def audio_settings(self):
        a=(self.elements('AudioProvider') or [(0,{})])[0][1]; g=lambda k,d:self.value(a.get(k),d)
        defaults={'fftSize':13,'sampleOutCount':200,'lowerHz':45,'higherHz':300,'hzLinearFactor':1,'freqShift':0,'mirrorSamples':1,'repeatSamples':1,'starAndEndGap':0,'smooth':1.5,'preSmooth':1,'filterRadius':1,'filterStrength':.3,'beatSmooth':.4,'beatRangeBarFirst':0,'beatRangeBarLast':.2,'beatRangeValueLower':.7,'beatRangeValueHigher':35,'aWeight':.75,'outputMultiplier':1}
        return {k:g(k,d) for k,d in defaults.items()}
    def inventory(self): return Counter(e.get('objType','Unknown') for _,e in self.elements())
    def unsupported(self,supported): return sorted(set(self.inventory())-set(supported))

def discover_themes(root):
    root=Path(root); found=[]
    if not root.exists(): return found
    for p in sorted(root.rglob('*.json')):
        try:
            t=Theme(p)
            if t.data.get('objType')=='Root' and t.compositions: found.append(t)
        except Exception: pass
    return found
