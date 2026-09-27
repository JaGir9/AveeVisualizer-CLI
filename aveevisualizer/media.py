import re, json
from pathlib import Path

IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.bmp'}
AUDIO_EXT={'.mp3','.wav','.flac','.m4a','.aac','.ogg','.opus','.wma'}

def natural_key(p):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', p.name)]

def scan(folder, exts):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts],key=natural_key)

class RotationState:
    def __init__(self, path):
        self.path=Path(path)
        try: self.data=json.loads(self.path.read_text(encoding='utf8'))
        except Exception: self.data={"background":0,"logo":0,"music":0}
    def get(self,k): return int(self.data.get(k,0))
    def advance(self,k,n):
        if n>1: self.data[k]=(self.get(k)+1)%n
    def save(self): self.path.write_text(json.dumps(self.data,indent=2),encoding='utf8')
