from dataclasses import dataclass, field, asdict
from copy import deepcopy
import math
import random
import re
import uuid
from .motion import MOTIONS, Plan
from .safety import SafeArea, solve, valid_regions, validate_plan


def duration_frames(seconds, fps):
    return math.floor(seconds*fps+.5)


@dataclass
class Clip:
    sourcePath: str
    sourceWidth: int = 1920
    sourceHeight: int = 1080
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    durationFrames: int = 200
    motionRequested: str = "zoom_in"
    amount: float = .08
    easing: str = "linear"
    focus: tuple = (.5,.5)
    locked: bool = False
    protectContent: bool = True
    protectedRegions: list = field(default_factory=list)
    motionResolved: Plan | None = None
    sourceFingerprint: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    mediaError: str = ""


@dataclass
class Project:
    name: str = "Haber DSF"
    fps: int = 25
    maxZoom: float = 1.15
    background: str = "#000000"
    safeArea: SafeArea = field(default_factory=SafeArea)
    seed: int = 20261010
    allowedMotions: list = field(default_factory=lambda: list(MOTIONS)[:-1])
    clips: list = field(default_factory=list)

    @property
    def total_frames(self):
        return sum(c.durationFrames for c in self.clips)

    def resolve(self, clip, kind=None):
        kind = kind or (clip.motionResolved.kind if clip.motionRequested=="auto" and clip.motionResolved
                        else clip.motionRequested)
        if kind == "auto":
            raise ValueError("Otomatik hareket için önce Yeniden dağıt düğmesini kullanın.")
        clip.motionResolved=solve(kind,clip.amount,clip.focus,self.maxZoom,clip.easing,
                                  clip.protectedRegions,self.safeArea,clip.protectContent)
        return clip.motionResolved

    def redistribute(self, ids=None):
        if not self.allowedMotions:
            raise ValueError("Önce proje ayarlarında en az bir harekete izin verin.")
        rng=random.Random(self.seed)
        changes=[]
        previous=None
        for c in self.clips:
            if c.locked or (ids is not None and c.id not in ids):
                previous=c.motionResolved.kind if c.motionResolved else None
                continue
            choices=list(self.allowedMotions)
            rng.shuffle(choices)
            choices.sort(key=lambda k:k==previous)
            for kind in choices:
                plan=solve(kind,c.amount,c.focus,self.maxZoom,c.easing,c.protectedRegions,self.safeArea,c.protectContent)
                if plan.status not in ("invalid_region","no_motion_available"):
                    changes.append((c,plan))
                    previous=kind
                    break
            else:
                raise ValueError(f"{c.sourcePath}: İzin verilen güvenli hareket bulunamadı. Alanı veya hareket kümesini düzenleyin.")
        for c,p in changes:
            c.motionRequested="auto"
            c.motionResolved=p
        self.seed+=1

    def snapshot(self):
        return deepcopy(self)

    def to_dict(self):
        return {"schemaVersion":1,"name":self.name,
            "output":{"width":1920,"height":1080,"fpsNum":self.fps,"fpsDen":1,
                      "container":"mp4","codec":"h264","audio":"none","colorProfile":"bt709_sdr_limited"},
            "safeArea":asdict(self.safeArea),
            "defaults":{"maxZoom":self.maxZoom,"durationFrames":8*self.fps,"easing":"linear","transition":"cut",
                        "background":self.background},
            "automation":{"seed":self.seed,"allowedMotions":self.allowedMotions},
            "clips":[asdict(c) for c in self.clips]}

    @classmethod
    def from_dict(cls,d):
        try:
            if type(d.get("schemaVersion")) is not int or d["schemaVersion"]!=1:
                raise ValueError("Proje sürümü desteklenmiyor; dosya değiştirilmedi.")
            out=d["output"]
            expected={"width":1920,"height":1080,"fpsDen":1,"container":"mp4","codec":"h264",
                      "audio":"none","colorProfile":"bt709_sdr_limited"}
            if any(out.get(k)!=v for k,v in expected.items()) or type(out["fpsNum"]) is not int or out["fpsNum"] not in (25,50):
                raise ValueError("Desteklenmeyen çıktı profili.")
            defaults=d["defaults"]
            p=cls(name=d["name"],fps=out["fpsNum"],maxZoom=defaults["maxZoom"],
                  background=defaults.get("background","#000000"),safeArea=SafeArea(**d["safeArea"]),
                  seed=d["automation"]["seed"],allowedMotions=d["automation"]["allowedMotions"])
            if not isinstance(p.name,str) or len(p.name)>500: raise ValueError("Geçersiz proje adı")
            if not isinstance(p.seed,int) or not isinstance(p.allowedMotions,list) or any(k not in MOTIONS for k in p.allowedMotions):
                raise ValueError("Geçersiz otomatik hareket ayarları")
            if not math.isfinite(p.maxZoom) or not 1 <= p.maxZoom <= 1.25: raise ValueError("Geçersiz büyütme sınırı")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}",p.background): raise ValueError("Geçersiz zemin rengi")
            a=p.safeArea
            if a.rasterGuardPx!=2 or any(not math.isfinite(x) or not 0<=x<.45 for x in (a.left,a.right,a.top,a.bottom)):
                raise ValueError("Geçersiz güvenli alan profili")
            if defaults["transition"]!="cut": raise ValueError("Yalnızca kesme desteklenir")
            if not isinstance(d["clips"],list) or len(d["clips"])>10000: raise ValueError("Geçersiz klip listesi")
            ids=set()
            for entry in d["clips"]:
                entry=deepcopy(entry)
                resolved=entry.pop("motionResolved")
                c=Clip(**entry)
                if not isinstance(c.id,str) or c.id in ids: raise ValueError("Klip kimliği geçersiz veya yinelenmiş")
                ids.add(c.id)
                if not isinstance(c.sourcePath,str) or not c.sourcePath or "\0" in c.sourcePath: raise ValueError("Geçersiz kaynak yolu")
                if type(c.durationFrames) is not int or not p.fps<=c.durationFrames<=120*p.fps: raise ValueError("Süre 1–120 saniye olmalıdır")
                if type(c.sourceWidth) is not int or type(c.sourceHeight) is not int or min(c.sourceWidth,c.sourceHeight)<=0:
                    raise ValueError("Geçersiz kaynak ölçüsü")
                if c.motionRequested not in (*MOTIONS,"auto") or c.easing not in ("linear","smoothstep"): raise ValueError("Geçersiz hareket")
                if not math.isfinite(c.amount) or not 0<=c.amount<=.25: raise ValueError("Geçersiz hareket miktarı")
                if len(c.focus)!=2 or any(not math.isfinite(x) or not 0<=x<=1 for x in c.focus): raise ValueError("Geçersiz odak")
                if not valid_regions(c.protectedRegions): raise ValueError("Geçersiz korunacak alan")
                c.focus=tuple(c.focus)
                c.protectedRegions=[tuple(r) for r in c.protectedRegions]
                if type(c.locked) is not bool or type(c.protectContent) is not bool: raise ValueError("Geçersiz koruma veya kilit")
                if not isinstance(c.notes,list) or not isinstance(c.mediaError,str) or not isinstance(c.sourceFingerprint,dict):
                    raise ValueError("Geçersiz medya bilgisi")
                if any(not isinstance(note,str) for note in c.notes):raise ValueError("Geçersiz medya notu")
                if resolved is not None:
                    c.motionResolved=Plan.from_dict(resolved)
                    q=c.motionResolved
                    if q.kind not in MOTIONS or q.easing!=c.easing: raise ValueError("Geçersiz kayıtlı hareket planı")
                    if c.motionRequested!="auto" and q.kind!=c.motionRequested: raise ValueError("Hareket türleri eşleşmiyor")
                    if q.status not in ("ok","reduced","no_motion_available","invalid_region","unchecked_content"):
                        raise ValueError("Geçersiz güvenlik durumu")
                    if not isinstance(q.message,str) or any(not isinstance(x,(int,float)) or not math.isfinite(x)
                        for tr in (q.start,q.end) for x in (tr.z,tr.tx,tr.ty)):
                        raise ValueError("Geçersiz kayıtlı dönüşüm")
                    if any(not isinstance(x,(int,float)) or not math.isfinite(x) or not 0<=x<=.25 for x in (q.requested,q.applied)):
                        raise ValueError("Geçersiz kayıtlı hareket miktarı")
                    if q.status!="invalid_region" and not validate_plan(q,c.protectedRegions if c.protectContent else (),a,p.maxZoom,c.durationFrames):
                        raise ValueError("Kayıtlı hareket güvenli alan kurallarını sağlamıyor")
                p.clips.append(c)
            return p
        except (KeyError,TypeError,AttributeError,OverflowError) as e:
            raise ValueError(f"Proje şeması geçersiz: {e}") from e
