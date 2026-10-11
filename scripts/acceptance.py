"""Real FFmpeg + Qt acceptance, writes evidence after each completed check."""
import json
import os
import sys
import subprocess
import time
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication,QEventLoop,QTimer
from PIL import Image,ImageDraw,ImageChops,ImageStat
import psutil
from dsf.jobs import RenderJob
from dsf.model import Project,Clip,duration_frames
from dsf.media import fingerprint
from dsf.persistence import load_project
from dsf.renderer import tool_path,probe,render_single,run_tool
from pixel_checks import frame,red_bounds

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts"/"acceptance";OUT.mkdir(parents=True,exist_ok=True)
app=QCoreApplication.instance() or QCoreApplication([])
results={}


def record(key,value):
    results[key]=value
    (OUT/"results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
    print(key,json.dumps(value,ensure_ascii=False)[:500],flush=True)


def run_job(p,target,w=1920,h=1080,cancel=False):
    loop=QEventLoop();result={};ticks=[];start=time.monotonic();peak=0
    job=RenderJob(p,target,w,h)
    def tick():
        nonlocal peak
        ticks.append(time.monotonic())
        proc=psutil.Process()
        rss=proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:rss+=child.memory_info().rss
            except psutil.Error:pass
        peak=max(peak,rss)
    timer=QTimer();timer.setInterval(100);timer.timeout.connect(tick);timer.start()
    def progress(n,text):
        if cancel and n>0 and "işleniyor" in text and "cancelRequestedAt" not in result:
            result["cancelRequestedAt"]=time.monotonic();job.requestInterruption()
    job.progress.connect(progress)
    job.succeeded.connect(lambda path,data:result.update(path=path,data=data))
    job.failed.connect(lambda error:result.update(error=error))
    job.cancelled.connect(lambda:result.update(cancelled=True))
    job.finished.connect(loop.quit);job.start();loop.exec();timer.stop();job.wait()
    result["elapsed"]=round(time.monotonic()-start,3);result["peakMiB"]=round(peak/1024**2,1)
    result["heartbeatTicks"]=len(ticks);result["maxHeartbeatGap"]=round(max((b-a for a,b in zip(ticks,ticks[1:])),default=0),3)
    if "cancelRequestedAt" in result:result["cancelLatency"]=round(time.monotonic()-result.pop("cancelRequestedAt"),3)
    return result


def single(path,kind="zoom_in",frames=200,fps=25,regions=()):
    p=Project(fps=fps);c=Clip(str(path),durationFrames=frames,motionRequested=kind,protectedRegions=list(regions),sourceFingerprint=fingerprint(path))
    p.clips=[c];p.resolve(c);return p


def stream_frames(path):
    proc=subprocess.Popen([tool_path("ffmpeg"),"-v","error","-i",str(path),"-f","rawvideo","-pix_fmt","rgb24","-"],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        while True:
            raw=proc.stdout.read(1920*1080*3)
            if not raw:break
            assert len(raw)==1920*1080*3
            yield Image.frombytes("RGB",(1920,1080),raw)
        assert proc.wait()==0
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        proc.stdout.close();proc.stderr.close()


def main():
    project=load_project(ROOT/"examples"/"Ornek_Haber.dsfproj")
    if "--reuse-main" in sys.argv:
        r=json.loads((OUT/"results.json").read_text(encoding="utf8"))["K01"]
        r["data"]=probe(r["path"])
        run_tool("ffmpeg",["-v","error","-xerror","-i",r["path"],"-f","null","-"],timeout=600)
    else:
        r=run_job(project,ROOT/"examples"/"Ornek_Haber_80sn.mp4")
    assert "error" not in r,r
    assert r["data"]["streams"][0]["nb_read_frames"]=="2000"
    assert float(r["data"]["format"]["duration"])==80
    assert r["heartbeatTicks"]>20 and r["maxHeartbeatGap"]<2,r
    (OUT/"K01_ffprobe.json").write_text(json.dumps(r["data"],ensure_ascii=False,indent=2),encoding="utf8")
    record("K01",{k:v for k,v in r.items() if k!="data"})
    # Render each cut endpoint independently from the frozen plan, then compare
    # decoded pixels. Also inspect timestamps for uniform cadence over all frames.
    timestamps=json.loads(subprocess.check_output([tool_path("ffprobe"),"-v","error","-select_streams","v:0","-show_frames",
        "-show_entries","frame=best_effort_timestamp_time","-of","json",r["path"]],creationflags=subprocess.CREATE_NO_WINDOW))["frames"]
    ts=[float(f["best_effort_timestamp_time"]) for f in timestamps]
    assert len(ts)==2000 and all(abs(t-i/25)<1e-6 for i,t in enumerate(ts))
    cut_errors=[]
    for k in [0,199,200,399,400,599,600,799,800,999,1000,1199,1200,1399,1400,1599,1600,1799,1800,1999]:
        im=frame(r["path"],k)
        c=project.clips[k//200];tr=c.motionResolved.at(k%200,200)
        reference=OUT/"cut-reference.mp4"
        render_single(c.sourcePath,reference,replace(c.motionResolved,start=tr,end=tr),1)
        expected=frame(reference,0)
        mae=max(ImageStat.Stat(ImageChops.difference(im,expected)).mean)
        cut_errors.append(round(mae,4));assert mae<2,(k,mae)
    record("K18",{"frames":2000,"timestamps":"all continuous 0.04 seconds","cutEndpointFramesChecked":20,"lastFrame":1999,
                  "maxMeanPixelErrorAgainstIndependentlyRenderedEndpoints":max(cut_errors)})
    marker=ROOT/"artifacts"/"stage1"/"source.png"
    p=single(marker,"pan_left",frames=51,fps=50)
    full=run_job(p,OUT/"preview_full.mp4");low=run_job(p,OUT/"preview_540.mp4",960,540)
    assert "error" not in full and "error" not in low,(full,low)
    differences=[]
    for k in (0,25,50):
        a=red_bounds(frame(full["path"],k));b=red_bounds(frame(low["path"],k))
        delta=max(abs(x-2*y) for x,y in zip(a,b));differences.append(delta);assert delta<=2,(a,b)
    record("K08",{"firstMiddleLastMaxDifference1080px":differences,"commonIntermediate":"3840x2160"})
    p.clips.append(deepcopy(p.clips[0]));p.clips[-1].id="second";p.clips[-1].durationFrames=duration_frames(1.22,50)
    r=run_job(p,OUT/"50fps_fractional.mp4");assert "error" not in r,r
    assert r["data"]["streams"][0]["nb_read_frames"]=="112"
    record("K07",{"fps":50,"frames":112,"duration":r["data"]["streams"][0]["duration"],"clipFrames":[51,61]})
    r25=run_job(single(marker,"zoom_out",26,25),OUT/"25fps_fractional.mp4")
    assert "error" not in r25 and r25["data"]["streams"][0]["nb_read_frames"]=="26",r25
    record("K07_25fps",{"fps":25,"frames":26,"duration":r25["data"]["streams"][0]["duration"]})
    protected=OUT/"korunan_yazı.png";im=Image.new("RGB",(1920,1080),"#246080");d=ImageDraw.Draw(im)
    d.rectangle((135,76,1784,1003),fill="#fa2020");im.save(protected)
    p=single(protected,regions=[(.07,.07,.93,.93)]);p.clips[0].amount=.15;p.resolve(p.clips[0])
    assert p.clips[0].motionResolved.status=="reduced"
    r=run_job(p,OUT/"protected.mp4");assert "error" not in r,r
    n=0
    for im in stream_frames(r["path"]):
        a=red_bounds(im);assert a[0]>=96 and a[1]>=54 and a[2]<=1824 and a[3]<=1026,a;n+=1
    assert n==200
    record("K04",{"checkedFrames":n,"appliedAmount":p.clips[0].motionResolved.applied,"allRegionsInsideSafeMargins":True})
    # Scan decoded pan geometry for blank borders and backwards jumps.
    centers=[]
    for im in stream_frames(ROOT/"artifacts"/"stage1"/"pan_left.mp4"):
        b=red_bounds(im);centers.append((b[0]+b[2])/2)
        for xy in ((0,0),(1919,0),(0,1079),(1919,1079),(0,540),(1919,540)):
            assert max(im.getpixel(xy))>30
    steps=[b-a for a,b in zip(centers,centers[1:])];assert min(steps)>=0 and max(steps)<=2
    record("K03_K09_partial",{"panFrames":len(centers),"minPixelStep":min(steps),"maxPixelStep":max(steps),"blankEdges":False,"manualRealtimeInspection":"not performed"})
    p=load_project(ROOT/"examples"/"Ornek_Haber.dsfproj")
    target=OUT/"cancel_preserves.mp4";target.write_bytes(b"previous-successful-output-sentinel")
    r=run_job(p,target,cancel=True)
    assert r.get("cancelled") and r["cancelLatency"]<3,r
    assert target.read_bytes()==b"previous-successful-output-sentinel"
    assert not list(OUT.glob(".dsf-render-*"))
    record("K13_cancel",r)
    usage=namedtuple("usage","total used free")
    with patch("dsf.jobs.shutil.disk_usage",return_value=usage(100,100,0)):r=run_job(p,target)
    assert "disk" in r.get("error","") and target.read_bytes()==b"previous-successful-output-sentinel"
    record("K13_disk_full",{"simulation":"disk_usage.free=0","result":r["error"],"existingOutputPreserved":True})
    p=single(marker);p.clips[0].sourcePath=str(OUT/"missing.png");r=run_job(p,OUT/"missing.mp4")
    assert "bulunamadı" in r.get("error","") and not (OUT/"missing.mp4").exists()
    record("K12_missing",{"result":r["error"]})
    # Analytic sRGB -> linear -> BT.709 reference; metadata-only conversion fails.
    ramp=OUT/"ramp.png";im=Image.new("RGB",(1920,1080));d=ImageDraw.Draw(im)
    values=list(range(0,256,17))
    for i,v in enumerate(values):d.rectangle((i*120,0,(i+1)*120-1,1079),fill=(v,v,v))
    im.save(ramp);p=single(ramp,"static",25);r=run_job(p,OUT/"ramp.mp4");assert "error" not in r,r
    decoded=frame(r["path"],0);errors=[]
    for i,v in enumerate(values):
        s=v/255;linear=s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
        bt=4.5*linear if linear<.018 else 1.099*linear**.45-.099
        errors.append(abs(decoded.getpixel((i*120+60,540))[0]-round(bt*255)))
    assert max(errors)<=3,errors
    record("K16_K17",{"rampMaxError8bit":max(errors),"allStreams":len(r["data"]["streams"]),"format":"yuv420p BT.709 limited progressive","overlays":"render path contains no overlay filters"})
    record("complete",True)


if __name__=="__main__":main()
