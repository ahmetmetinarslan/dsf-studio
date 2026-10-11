import random
import pytest
from dsf.motion import MOTIONS, Transform
from dsf.safety import SafeArea, solve, is_safe, validate_plan


@pytest.mark.parametrize("kind", MOTIONS)
@pytest.mark.parametrize("easing", ["linear","smoothstep"])
def test_endpoints_and_every_frame(kind,easing):
    regions=[(.15,.15,.85,.85)]
    p=solve(kind,.1,easing=easing,regions=regions)
    assert p.status=="ok"
    assert p.at(0,200)==p.start
    assert abs(p.at(199,200).z-p.end.z)<1e-12
    for k in range(200): assert is_safe(p.at(k,200),regions)


def test_directions_and_no_border():
    for kind in MOTIONS:
        p=solve(kind,.1)
        if kind=="pan_left": assert p.end.tx>p.start.tx
        if kind=="pan_right": assert p.end.tx<p.start.tx
        if kind=="pan_up": assert p.end.ty>p.start.ty
        if kind=="pan_down": assert p.end.ty<p.start.ty
        if kind=="zoom_in": assert p.end.z>p.start.z
        if kind=="zoom_out": assert p.end.z<p.start.z and p.end.z>=1
        for k in range(200): assert is_safe(p.at(k,200),[])


def test_edge_reduces_and_impossible_fails():
    p=solve("zoom_in",.15,regions=[(.07,.07,.93,.93)])
    assert p.status=="reduced" and 0<p.applied<.15
    for kind in MOTIONS:
        assert solve(kind,regions=[(0,0,1,1)]).status=="invalid_region"


def test_exact_safe_with_guard_has_no_motion():
    l,r,t,b=SafeArea().bounds()
    p=solve("zoom_in",regions=[(l,t,r,b)])
    assert p.status=="no_motion_available"
    assert p.start==p.end==Transform()


def test_zoom_can_rescue_small_near_edge_region():
    p=solve("static",max_zoom=1.25,regions=[(.045,.2,.1,.3)])
    assert p.status=="ok" and p.start.z>1
    assert is_safe(p.start,[(.045,.2,.1,.3)],max_zoom=1.25)


def test_unchecked_and_disabled():
    assert solve("zoom_in").status=="unchecked_content"
    p=solve("zoom_in",regions=[(0,0,1,1)],protect=False)
    assert p.status=="unchecked_content" and "kapalı" in p.message


def test_pan_with_max_scale_one():
    p=solve("pan_left",max_zoom=1)
    assert p.status=="no_motion_available" and p.start==p.end==Transform()


def test_invalid_region():
    for region in [(.8,.1,.2,.9),(-.1,0,.5,.5),(0,0,float('nan'),.2)]:
        assert solve("static",regions=[region]).status=="invalid_region"


def test_random_rectangles_and_asymmetric_profiles():
    rng=random.Random(241)
    for _ in range(600):
        x0,x1=sorted([rng.uniform(.01,.99),rng.uniform(.01,.99)])
        y0,y1=sorted([rng.uniform(.01,.99),rng.uniform(.01,.99)])
        regions=[(x0,y0,x1,y1),(.4,.4,.6,.6)]
        safe=SafeArea("custom",.03,.07,.08,.13)
        p=solve(rng.choice(list(MOTIONS)),rng.uniform(.01,.25),
                (rng.random(),rng.random()),1.25,regions=regions,safe=safe)
        if p.status!="invalid_region":
            assert validate_plan(p,regions,safe,1.25)
            for k in range(73): assert is_safe(p.at(k,73),regions,safe,1.25)
