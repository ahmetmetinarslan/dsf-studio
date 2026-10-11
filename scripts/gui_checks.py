import json
import sys
import time
import shutil
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psutil
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,Qt,QPoint,QUrl
from PySide6.QtTest import QTest
from dsf.ui import MainWindow
from dsf.persistence import save_project,load_project

root=Path(__file__).resolve().parents[1];out=root/"artifacts"/"gui";out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);app.setApplicationName("DSF test")
window=MainWindow(out/"appdata",check_tools=False);errors=[];window.error=errors.append;window.show()
ticks=[];memory=[];timer=QTimer();timer.setInterval(50)
def tick():ticks.append(time.monotonic());memory.append(psutil.Process().memory_info().rss)
timer.timeout.connect(tick);timer.start()
def until(predicate,timeout=30):
    start=time.monotonic()
    while not predicate():
        if time.monotonic()-start>timeout:raise AssertionError("GUI timeout")
        QTest.qWait(20)

try:
    media=out/"medya";media.mkdir(exist_ok=True);source=root/"examples"/"assets"/"haber_01_örnek.png"
    paths=[]
    for i in range(100):
        path=media/f"görsel_{i:03d}.png";shutil.copyfile(source,path);paths.append(str(path))
    start=time.monotonic();window.import_paths(paths);until(lambda:not window.importer.isRunning(),90)
    assert len(window.project.clips)==100 and window.list.count()==100
    assert len(window.images)<=8
    import_seconds=time.monotonic()-start
    window.list.setCurrentRow(0);window.list.item(1).setSelected(True)
    window.duration.setValue(3.14);window.apply(True)
    assert window.project.clips[0].durationFrames==79 and window.project.clips[1].durationFrames==79
    window.undo();assert window.project.clips[0].durationFrames==200
    window.redo();assert window.project.clips[0].durationFrames==79
    window.list.clearSelection();window.list.setCurrentRow(0);window.list.item(0).setSelected(True)
    window.toggle_lock();locked=deepcopy(window.project.clips[0]);window.redistribute();assert window.project.clips[0]==locked
    window.duplicate();assert len(window.project.clips)==101
    window.undo();assert len(window.project.clips)==100
    window.list.setCurrentRow(1);moving=window.current().id;window.move(1);assert window.project.clips[2].id==moving
    window.undo();window.list.setCurrentRow(0);until(lambda:not window.canvas.image.isNull())
    window.view_mode.setCurrentIndex(1);r=window.canvas.viewport()
    a=QPoint(round(r.x()+r.width()*.3),round(r.y()+r.height()*.3));b=QPoint(round(r.x()+r.width()*.65),round(r.y()+r.height()*.65))
    count=len(window.current().protectedRegions)
    QTest.mousePress(window.canvas,Qt.MouseButton.LeftButton,pos=a)
    QTest.mouseMove(window.canvas,b,100)
    QTest.mouseRelease(window.canvas,Qt.MouseButton.LeftButton,pos=b)
    assert len(window.current().protectedRegions)==count+1
    window.save_recovery();assert window.recovery.exists()
    assert len(load_project(window.recovery).clips)==100
    file=out/"yuvarlak.dsfproj";save_project(window.project,file);assert load_project(file).to_dict()==window.project.to_dict()
    # Exercise actual Qt multimedia video frames and playback position.
    frames=[];window.player.videoSink().videoFrameChanged.connect(lambda f:frames.append(f.isValid()))
    window.player.setSource(QUrl.fromLocalFile(str(root/"artifacts"/"stage1"/"pan_left.mp4")))
    window.stack.setCurrentWidget(window.video);window.player.play()
    until(lambda:window.player.position()>1200,20)
    assert any(frames) and window.player.error().value==0
    window.grab().save(str(out/"qt-playback.png"));window.player.stop();window.show_canvas()
    # One real render from a 100-image immutable snapshot; cancel while encoding.
    target=out/"cancelled.mp4";target.write_bytes(b"keep-existing")
    window.start_job(window.project,target,1920,1080,False)
    until(lambda:window.progress.value()>0,60)
    window.cancel_job();cancel_started=time.monotonic();until(lambda:not window.job.isRunning(),5)
    cancel_seconds=time.monotonic()-cancel_started
    assert target.read_bytes()==b"keep-existing"
    assert not list(out.glob(".dsf-render-*"))
    assert not errors,errors
    # Corrupt file stays visible and never removes valid imports.
    bad=media/"bozuk.png";bad.write_bytes(b"broken");window.import_paths([str(bad)])
    until(lambda:len(window.project.clips)==101 and not window.importer.isRunning());assert window.project.clips[-1].mediaError
    assert len(window.project.clips)==101
    window.project=load_project(root/"examples"/"Ornek_Haber.dsfproj");window.refresh();window.view_mode.setCurrentIndex(0)
    until(lambda:not window.canvas.image.isNull());QTest.qWait(300);window.grab().save(str(out/"DSF-Studio.png"))
    gaps=[b-a for a,b in zip(ticks,ticks[1:])]
    result={"passed":["100-image import","bounded 8-image preview cache","batch duration","undo redo","lock redistribution",
       "duplicate","reorder","mouse rectangle selection","recovery","project roundtrip","Qt actual video frames",
       "100-image render cancellation","existing output preservation","corrupt-file isolation"],
       "import100Seconds":round(import_seconds,3),"peakPythonMiB":round(max(memory)/1024**2,2),
       "maxGuiHeartbeatGapSeconds":round(max(gaps),3),"heartbeatTicks":len(ticks),"cancelSeconds":round(cancel_seconds,3),
       "validVideoFrames":sum(frames),"imageCacheLimit":8}
    (out/"results.json").write_text(json.dumps(result,indent=2),encoding="utf8");print(json.dumps(result,indent=2),flush=True)
finally:
    timer.stop()
    if window.job and window.job.isRunning():window.job.requestInterruption();window.job.wait(10000)
    if window.importer and window.importer.isRunning():window.importer.requestInterruption();window.importer.wait(10000)
    window.dirty=False;window.close()
