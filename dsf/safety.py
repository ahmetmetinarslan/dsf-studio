"""Affine eşitsizlik çözücüsü; uç noktalarla bütün hareket doğrulanır."""
from dataclasses import dataclass
import math
from .motion import Plan, Transform, preset

EPS = 1e-9


@dataclass(frozen=True)
class SafeArea:
    preset: str = "ebu_graphics"
    left: float = .05
    right: float = .05
    top: float = .05
    bottom: float = .05
    rasterGuardPx: int = 2

    def bounds(self):
        return (self.left+self.rasterGuardPx/1920, 1-self.right-self.rasterGuardPx/1920,
                self.top+self.rasterGuardPx/1080, 1-self.bottom-self.rasterGuardPx/1080)


def valid_regions(regions):
    return all(len(r) == 4 and all(math.isfinite(x) for x in r)
               and 0 <= r[0] < r[2] <= 1 and 0 <= r[1] < r[3] <= 1 for r in regions)


def lines(regions, safe):
    l,r,t,b = safe.bounds()
    return ([ (1., -1.), *[(l, -x[0]) for x in regions]],
            [ (0., 0.), *[(r, -x[2]) for x in regions]],
            [ (1., -1.), *[(t, -x[1]) for x in regions]],
            [ (0., 0.), *[(b, -x[3]) for x in regions]])


def scale_interval(regions, safe, max_zoom):
    low, high = 1., max_zoom
    xl,xh,yl,yh = lines(regions, safe)
    for lower, upper in ((xl,xh),(yl,yh)):
        for c,m in lower:
            for d,n in upper:
                slope, rhs = m-n, d-c
                if abs(slope) < 1e-14:
                    if rhs < -EPS: return None
                elif slope > 0: high = min(high, rhs/slope)
                else: low = max(low, rhs/slope)
    return (low, max(low,high)) if low <= high+EPS else None


def translation_interval(z, regions, safe):
    xl,xh,yl,yh = lines(regions, safe)
    return (max(c+m*z for c,m in xl), min(c+m*z for c,m in xh),
            max(c+m*z for c,m in yl), min(c+m*z for c,m in yh))


def clamp(value, low, high):
    return max(low, min(high, value))


def framed(z, focus, regions, safe):
    xl,xh,yl,yh = translation_interval(z, regions, safe)
    return Transform(z, clamp((1-z)*focus[0], xl, xh), clamp((1-z)*focus[1],yl,yh))


def is_safe(transform, regions, safe=SafeArea(), max_zoom=1.15):
    z,x,y = transform.z,transform.tx,transform.ty
    if not all(math.isfinite(v) for v in (z,x,y)): return False
    if not 1-EPS <= z <= max_zoom+EPS: return False
    if not 1-z-EPS <= x <= EPS or not 1-z-EPS <= y <= EPS: return False
    l,r,t,b = safe.bounds()
    return all(l-EPS <= z*u0+x and z*u1+x <= r+EPS and
               t-EPS <= z*v0+y and z*v1+y <= b+EPS for u0,v0,u1,v1 in regions)


def validate_plan(plan, regions, safe, max_zoom, frames=200):
    # Endpoint proof plus intermediate checks catch implementation regressions.
    return valid_regions(regions) and all(is_safe(plan.at(k,frames), regions, safe, max_zoom)
        for k in sorted({0,frames-1,*[round((frames-1)*i/16) for i in range(17)]}))


def solve(kind, amount=.08, focus=(.5,.5), max_zoom=1.15, easing="linear",
          regions=(), safe=SafeArea(), protect=True):
    requested = preset(kind, amount, focus, max_zoom, easing)
    if not valid_regions(regions):
        return Plan(kind, Transform(), Transform(), easing, "invalid_region", amount, 0.,
                    "Korunacak alan geçersiz; dikdörtgeni yeniden çizin.")
    active = regions if protect else ()
    interval = scale_interval(active, safe, max_zoom)
    if interval is None:
        return Plan(kind, Transform(), Transform(), easing, "invalid_region", amount, 0.,
                    "Sabit kadraj bile güvensiz. Kaynak görseli veya korunacak alanı düzenleyin.")
    lo,hi = interval
    still = framed(lo, focus, active, safe)
    start = end = still
    applied = 0.
    target = min(1+amount, max_zoom, hi)
    if kind.startswith("zoom") and target > lo+EPS:
        start, end = still, framed(target, focus, active, safe)
        applied = target-lo
        if kind == "zoom_out": start,end = end,start
    elif kind.startswith("pan") and target >= lo-EPS:
        # Interval widths are piecewise linear: their maxima occur at endpoints
        # or a change of the active lower/upper constraint, no grid-search gaps.
        xl,xh,yl,yh = lines(active, safe)
        groups = (xl,xh) if kind in ("pan_left","pan_right") else (yl,yh)
        candidates = {lo, max(lo,target)}
        for group in groups:
            for c,m in group:
                for d,n in group:
                    if abs(m-n)>1e-14:
                        z=(d-c)/(m-n)
                        if lo <= z <= target: candidates.add(z)
        def travel(z):
            bounds=translation_interval(z,active,safe)
            idx=0 if kind in ("pan_left","pan_right") else 2
            return bounds[idx+1]-bounds[idx]
        z=max(candidates,key=lambda z:(min(amount,travel(z)),-z))
        applied=max(0.,min(amount,travel(z)))
        xl,xh,yl,yh=translation_interval(z,active,safe)
        f=framed(z,focus,active,safe)
        if kind in ("pan_left","pan_right"):
            left=clamp(f.tx-applied/2,xl,xh-applied)
            start,end=Transform(z,left,f.ty),Transform(z,left+applied,f.ty)
        else:
            top=clamp(f.ty-applied/2,yl,yh-applied)
            start,end=Transform(z,f.tx,top),Transform(z,f.tx,top+applied)
        if kind in ("pan_right","pan_down"): start,end=end,start
    if kind != "static" and applied < 1e-7:
        status, message = "no_motion_available", "Güvenli hareket yok; güvenli sabit kadraj uygulanacak."
    elif kind != "static" and applied < amount-1e-7:
        status, message = "reduced", f"Hareket azaltıldı: %{amount*100:.2f} → %{applied*100:.2f}"
    else:
        status, message = "ok", "Alan uygun"
    if not active:
        if status == "ok": message="Görüntü sınırları uygun"
        message += " · İçerik koruması tanımlanmadı" if protect else " · İçerik koruması kapalı"
        if status == "ok": status="unchecked_content"
    result=Plan(kind,start,end,easing,status,amount,applied,message)
    if not validate_plan(result,active,safe,max_zoom):
        raise RuntimeError("Hareket çözücüsü geçersiz kadraj üretti.")
    return result
