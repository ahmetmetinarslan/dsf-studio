"""Tek geometri sözleşmesi: çıktı = ölçek * kaynak + öteleme."""
from dataclasses import dataclass, asdict

MOTIONS = {"zoom_in": "Yaklaş", "zoom_out": "Uzaklaş", "pan_left": "Kamera sola",
           "pan_right": "Kamera sağa", "pan_up": "Kamera yukarı",
           "pan_down": "Kamera aşağı", "static": "Sabit"}


@dataclass(frozen=True)
class Transform:
    z: float = 1.0
    tx: float = 0.0
    ty: float = 0.0

    def point(self, u, v):
        return self.z * u + self.tx, self.z * v + self.ty


@dataclass(frozen=True)
class Plan:
    kind: str
    start: Transform
    end: Transform
    easing: str = "linear"
    status: str = "unchecked_content"
    requested: float = 0.08
    applied: float = 0.08
    message: str = "İçerik koruması tanımlanmadı"

    def at(self, k, frames):
        p = max(0., min(1., k / (frames - 1))) if frames > 1 else 0.
        a = 3*p*p - 2*p*p*p if self.easing == "smoothstep" else p
        return Transform(*(x + (y-x)*a for x, y in zip(
            (self.start.z, self.start.tx, self.start.ty),
            (self.end.z, self.end.tx, self.end.ty))))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{**d, "start": Transform(**d["start"]), "end": Transform(**d["end"])})


def preset(kind, amount=0.08, focus=(0.5, 0.5), max_zoom=1.15, easing="linear"):
    if kind not in MOTIONS:
        raise ValueError("Bilinmeyen hareket")
    a = min(max(0., amount), max_zoom-1.)
    fu, fv = focus
    big = Transform(1+a, -a*fu, -a*fv)
    start = end = Transform()
    if kind == "zoom_in":
        end = big
    elif kind == "zoom_out":
        start = big
    elif kind.startswith("pan_"):
        # Pan amount is total translation in normalized output units.
        if kind in ("pan_left", "pan_right"):
            start, end = Transform(1+a, -a, -a*fv), Transform(1+a, 0., -a*fv)
        else:
            start, end = Transform(1+a, -a*fu, -a), Transform(1+a, -a*fu, 0.)
        if kind in ("pan_right", "pan_down"):
            start, end = end, start
    return Plan(kind, start, end, easing, requested=amount, applied=a if kind != "static" else 0.)
