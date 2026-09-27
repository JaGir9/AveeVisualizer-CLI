import json, re
from pathlib import Path
from collections import Counter

class Theme:
    def __init__(self,path):
        self.path=Path(path); self.data=json.loads(self.path.read_text(encoding='utf8')); self.compositions=self.data.get('compositions',[])
    @staticmethod
    def value(x,default=None): return x.get('v',default) if isinstance(x,dict) else (default if x is None else x)
    def elements(self,obj_type=None):
        return [(ci,e) for ci,c in enumerate(self.compositions) for e in c.get('elements',[]) if obj_type is None or e.get('objType')==obj_type]
    def composition(self,index): return self.compositions[index] if 0<=index<len(self.compositions) else None
    def element_id(self,e):
        try:return int(self.value(e.get('_id'),-1))
        except:return -1
    def tag(self,e): return str(self.value(e.get('tag'),''))
    def measure(self,node,name):
        m=node.get(name,{}) if isinstance(node,dict) else {}
        def num(k):
            try:return float(self.value(m.get(k),0) or 0)
            except:return 0.
        return str(self.value(m.get('measureWhat'),'Nothing')),num('A'),num('B')
    def ref(self,node,key):
        v=str(self.value(node.get(key),'') or ''); m=re.fullmatch(r'composition:(\d+)',v); return int(m.group(1)) if m else None
    def audio_settings(self):
        a=(self.elements('AudioProvider') or [(0,{})])[0][1]; g=lambda k,d:self.value(a.get(k),d)
        defaults={'fftSize':13,'sampleOutCount':200,'lowerHz':45,'higherHz':300,'hzLinearFactor':1,'freqShift':0,'mirrorSamples':1,'repeatSamples':1,'starAndEndGap':0,'smooth':1.5,'preSmooth':1,'filterRadius':1,'filterStrength':.3,'beatSmooth':.4,'beatRangeBarFirst':0,'beatRangeBarLast':.2,'beatRangeValueLower':.7,'beatRangeValueHigher':35,'aWeight':.75,'outputMultiplier':1}
        return {k:g(k,d) for k,d in defaults.items()}
    def inventory(self): return Counter(e.get('objType','Unknown') for _,e in self.elements())
    def unsupported(self,supported): return sorted(set(self.inventory())-set(supported))
    def _walk(self,node):
        if isinstance(node,dict):
            yield node
            for v in node.values(): yield from self._walk(v)
        elif isinstance(node,list):
            for v in node: yield from self._walk(v)
    def measures(self):
        out=Counter()
        for n in self._walk(self.data):
            if 'measureWhat' in n:
                w=str(self.value(n.get('measureWhat'),'Nothing')); out[w]+=1
        return out
    def resources(self):
        out=Counter()
        for n in self._walk(self.data):
            if 'v' in n and isinstance(n['v'],str):
                v=n['v']
                if v.startswith('internalres:') or v.startswith('composition:') or v.startswith('local:'): out[v]+=1
        return out
    def report(self,supported_types=None,supported_measures=None):
        inv=self.inventory(); meas=self.measures(); res=self.resources()
        return {'compositions':len(self.compositions),'elements':sum(inv.values()),'types':dict(inv),'measures':dict(meas),'resources':dict(res),
                'unsupported_types':sorted(set(inv)-(set(supported_types or inv))),
                'unsupported_measures':sorted(set(meas)-(set(supported_measures or meas)))}

def discover_themes(root):
    root=Path(root); found=[]
    if not root.exists(): return found
    for p in sorted(root.rglob('*.json')):
        try:
            t=Theme(p)
            if t.data.get('objType')=='Root' and t.compositions: found.append(t)
        except (OSError,json.JSONDecodeError,UnicodeError): pass
    return found
