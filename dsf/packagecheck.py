"""Executable smoke check: bundled encoder, ffprobe, Qt playback, no PATH tools."""
import json
from pathlib import Path
import time
from PIL import Image,ImageDraw
from PySide6.QtCore import QTimer,QUrl
from .model import Project,Clip
from .renderer import capabilities
from .jobs import RenderJob
from .ui import MainWindow


def verify(app,destination):
    out=Path(destination).resolve();out.mkdir(parents=True,exist_ok=True)
    window=MainWindow(out/"appdata",check_tools=False);window.show()
    result={"started":time.time(),"qtVideoFrames":0};job=None;finished=False
    def finish(code,error=None):
        nonlocal finished
        if finished:return
        finished=True;result["exitCode"]=code
        if error:result["error"]=str(error)
        if job and job.isRunning():job.requestInterruption();job.wait(5000)
        result["elapsedSeconds"]=round(time.time()-result.pop("started"),3)
        window.grab().save(str(out/"package.png"))
        (out/"package-check.json").write_text(json.dumps(result,indent=2),encoding="utf8")
        window.dirty=False;window.close();app.exit(code)
    def on_frame(f):
        if f.isValid():result["qtVideoFrames"]+=1
    def on_success(path,data):
        result["video"]=data["streams"][0]
        window.player.setSource(QUrl.fromLocalFile(path));window.stack.setCurrentWidget(window.video);window.player.play()
    def check_playback():
        if result["qtVideoFrames"]>=8 and window.player.position()>250:finish(0)
    try:
        result["tools"]=capabilities()
        source=out/"paket_şğü.png";im=Image.new("RGB",(1920,1080),"#284b63");d=ImageDraw.Draw(im)
        d.rectangle((500,300,1400,780),fill="#dc4545");im.save(source)
        p=Project(clips=[Clip(str(source),durationFrames=25,protectedRegions=[(.2,.2,.8,.8)])]);p.resolve(p.clips[0])
        window.project=p;window.refresh()
        job=RenderJob(p,out/"paket_test.mp4");job.succeeded.connect(on_success);job.failed.connect(lambda e:finish(1,e))
        window.player.videoSink().videoFrameChanged.connect(on_frame)
        window.player.errorOccurred.connect(lambda *_:finish(1,window.player.errorString()))
        timer=QTimer();timer.setInterval(100);timer.timeout.connect(check_playback);timer.start()
        QTimer.singleShot(60000,lambda:finish(1,"Package check timed out"));job.start()
        return app.exec()
    except Exception as e:
        finish(1,e);return 1
