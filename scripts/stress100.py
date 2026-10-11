import json
from pathlib import Path
from acceptance import ROOT,OUT,run_job
from dsf.model import Project,Clip
from dsf.media import fingerprint

p=Project(name="100 görsel bellek testi")
paths=sorted((ROOT/"artifacts"/"gui"/"medya").glob("görsel_*.png"))
assert len(paths)==100
for i,path in enumerate(paths):
    c=Clip(str(path),durationFrames=25,motionRequested=["zoom_in","pan_left","pan_down"][i%3],
           protectedRegions=[(.15,.18,.85,.8)],sourceFingerprint=fingerprint(path))
    p.resolve(c);p.clips.append(c)
r=run_job(p,OUT/"stress100.mp4")
assert "error" not in r,r
assert r["data"]["streams"][0]["nb_read_frames"]=="2500"
assert r["heartbeatTicks"]>30 and r["maxHeartbeatGap"]<2
report={k:v for k,v in r.items() if k!="data"}
report.update(images=100,sourceResolution="1920x1080",frames=2500,durationSeconds=100,clipDurationSeconds=1,
              boundedQueue=1,fullDecode=True)
(OUT/"stress100.json").write_text(json.dumps(report,indent=2),encoding="utf8")
print(json.dumps(report,indent=2),flush=True)
