import io
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from .media import load_image, fingerprint
from .model import Clip
from .renderer import capabilities


class ImportWorker(QThread):
    item=Signal(object,bytes,bytes)
    done=Signal()

    def __init__(self, paths, fps, background, parent=None):
        super().__init__(parent)
        self.paths=list(paths)
        self.fps=fps
        self.background=background

    def run(self):
        for path in self.paths:
            if self.isInterruptionRequested(): break
            c=Clip(str(Path(path).resolve()),durationFrames=8*self.fps)
            thumb=preview=b""
            try:
                im,c.notes=load_image(path,self.background)
                c.sourceWidth,c.sourceHeight=im.size
                c.sourceFingerprint=fingerprint(path)
                im.thumbnail((1280,720))
                stream=io.BytesIO(); im.save(stream,"PNG"); preview=stream.getvalue()
                im.thumbnail((160,90))
                stream=io.BytesIO(); im.save(stream,"PNG"); thumb=stream.getvalue()
            except Exception as e:
                c.mediaError=str(e)
            self.item.emit(c,thumb,preview)
        self.done.emit()


class ImageWorker(QThread):
    loaded=Signal(str,bytes,str)

    def __init__(self, clip_id, path, background, parent=None):
        super().__init__(parent)
        self.clip_id,self.path,self.background=clip_id,path,background

    def run(self):
        try:
            im,_=load_image(self.path,self.background)
            im.thumbnail((1280,720))
            stream=io.BytesIO(); im.save(stream,"PNG")
            self.loaded.emit(self.clip_id,stream.getvalue(),"")
        except Exception as e:
            self.loaded.emit(self.clip_id,b"",str(e))


class CapabilityWorker(QThread):
    checked=Signal(bool,str)

    def run(self):
        try:
            info=capabilities()
            self.checked.emit(True,info["ffmpeg"])
        except Exception as e:
            self.checked.emit(False,str(e))
