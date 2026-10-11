import json
from acceptance import ROOT,OUT,run_job,single
from pixel_checks import frame,red_bounds

results={}
for kind in ("zoom_in","zoom_out","pan_left","pan_right","pan_up","pan_down"):
    p=single(ROOT/"artifacts"/"stage1"/"source.png",kind)
    p.clips[0].amount=.1 if kind.startswith("pan") else .08;p.resolve(p.clips[0])
    low=run_job(p,OUT/f"preview_{kind}_540.mp4",960,540)
    assert "error" not in low,low
    deltas=[]
    for k in (0,100,199):
        a=red_bounds(frame(ROOT/"artifacts"/"stage1"/f"{kind}.mp4",k));b=red_bounds(frame(low["path"],k))
        delta=max(abs(x-2*y) for x,y in zip(a,b));deltas.append(delta);assert delta<=2,(kind,k,a,b)
    results[kind]=deltas;print(kind,deltas,flush=True)
(OUT/"preview_six.json").write_text(json.dumps(results,indent=2),encoding="utf8")
