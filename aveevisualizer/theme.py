import json
from pathlib import Path

class Theme:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.elements = [e for c in self.data.get("compositions", []) for e in c.get("elements", [])]
        self.audio = next((e for e in self.elements if e.get("objType") == "AudioProvider"), {})
        self.background = next((e for e in self.elements if self._v(e, "tag") == "BackGround"), {})
        self.logo = next((e for e in self.elements if self._v(e, "tag") == "Logo"), {})
        self.circle = next((e for e in self.elements if e.get("objType") == "Image" and self._v(e, "Shape") == "Circle"), {})
        self.bars = [e for e in self.elements if e.get("objType") == "Bars"]

    @staticmethod
    def _v(e, key, default=None):
        x = e.get(key, {})
        return x.get("v", default) if isinstance(x, dict) else default

    def audio_settings(self):
        return {
            "fft_power": int(self._v(self.audio, "fftSize", 13)),
            "sample_count": int(self._v(self.audio, "sampleOutCount", 200)),
            "lower_hz": float(self._v(self.audio, "lowerHz", 45)),
            "higher_hz": float(self._v(self.audio, "higherHz", 300)),
            "smooth": float(self._v(self.audio, "smooth", 1.5)),
            "beat_smooth": float(self._v(self.audio, "beatSmooth", .4)),
        }

    def visual_settings(self):
        scale = self._v(self.circle, "scale", "0.310000 0.310000")
        try: circle_scale = float(str(scale).split()[0])
        except Exception: circle_scale = .31
        return {
            "circle_scale": circle_scale,
            "bar_layers": [{
                "scale": float(str(self._v(b, "scale", ".31 .31")).split()[0]),
                "height": float(self._v(b, "heightScale", 2.5)),
                "delay": int(self._v(b, "reactionDelay", 0)),
                "softness": int(self._v(b, "softness", 8)),
            } for b in self.bars]
        }
