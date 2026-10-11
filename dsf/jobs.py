"""Sınırlı, iptal edilebilir QProcess kuyruğu; doğrulamadan hedefe dokunmaz."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from PySide6.QtCore import QThread, QProcess, Signal
from .media import fingerprint, normalize
from .renderer import RENDERER_VERSION, tool_path, clip_args, validate_probe
from .safety import validate_plan


class Cancelled(Exception): pass


def preview_key(project,width,height):
    d=project.to_dict()
    for c in d["clips"]: c["currentFingerprint"]=fingerprint(c["sourcePath"])
    data={"project":d,"size":[width,height],"renderer":RENDERER_VERSION}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class RenderJob(QThread):
    progress=Signal(int,str)
    succeeded=Signal(str,object)
    failed=Signal(str)
    cancelled=Signal()

    def __init__(self,project,target,width=1920,height=1080,preview=False,parent=None):
        super().__init__(parent)
        self.project=project.snapshot()
        self.target=Path(target).resolve()
        self.width,self.height=width,height
        self.preview=preview
        self.started_at=0
        self.log=[]

    def check_cancel(self):
        if self.isInterruptionRequested(): raise Cancelled()

    def process(self,name,args,frame_callback=None):
        self.check_cancel()
        proc=QProcess()
        proc.setProgram(tool_path(name));proc.setArguments(list(map(str,args)))
        proc.start()
        if not proc.waitForStarted(10000): raise RuntimeError(f"{name} başlatılamadı: {proc.errorString()}")
        stdout=bytearray();stderr=bytearray();pending=b""
        try:
            while True:
                proc.waitForFinished(80)
                chunk=bytes(proc.readAllStandardOutput())
                if frame_callback:
                    pending+=chunk
                    rows=pending.split(b"\n");pending=rows.pop()
                    for line in rows:
                        if line.startswith(b"frame="):
                            try: frame_callback(int(line[6:]))
                            except ValueError: pass
                else: stdout.extend(chunk)
                stderr.extend(bytes(proc.readAllStandardError()))
                if len(stderr)>12000: del stderr[:-12000]
                self.check_cancel()
                if proc.state()==QProcess.ProcessState.NotRunning: break
            if proc.exitCode()!=0 or proc.exitStatus()!=QProcess.ExitStatus.NormalExit:
                raise RuntimeError("Video işlemi başarısız. " + stderr.decode("utf-8","replace")[-4000:])
            return stdout.decode("utf-8","replace")
        finally:
            if proc.state()!=QProcess.ProcessState.NotRunning:
                proc.kill();proc.waitForFinished(3000)

    def run(self):
        self.started_at=time.monotonic()
        temp=None
        try:
            p=self.project
            if not p.clips: raise ValueError("En az bir görsel ekleyin.")
            if self.target.suffix.lower()!=".mp4": raise ValueError("Çıktı dosyası .mp4 olmalıdır.")
            self.target.parent.mkdir(parents=True,exist_ok=True)
            if any(Path(c.sourcePath).resolve()==self.target for c in p.clips):
                raise ValueError("Kaynak görsel çıktı hedefi olarak kullanılamaz.")
            total=p.total_frames
            estimate=max(256*1024*1024,int(total/p.fps*8*1024*1024))
            if shutil.disk_usage(self.target.parent).free<estimate:
                raise OSError("Yeterli boş disk alanı yok. Ara klipler ve son çıktı için yer açın.")
            self.progress.emit(0,"Kaynaklar ve güvenli alanlar denetleniyor…")
            for c in p.clips:
                self.check_cancel()
                if c.mediaError: raise ValueError(f"{Path(c.sourcePath).name}: {c.mediaError}")
                if not Path(c.sourcePath).is_file(): raise ValueError(f"Dosya bulunamadı: {c.sourcePath}. Yeniden bağlayın.")
                current=fingerprint(c.sourcePath)
                if c.sourceFingerprint and current["sha256"]!=c.sourceFingerprint.get("sha256"):
                    raise ValueError(f"{Path(c.sourcePath).name}: Kaynak içeriği değişmiş. Yeniden bağlayıp korunan alanları kontrol edin.")
                plan=c.motionResolved
                if not plan or plan.status=="invalid_region" or not validate_plan(plan,c.protectedRegions if c.protectContent else (),p.safeArea,p.maxZoom,c.durationFrames):
                    raise ValueError(f"{Path(c.sourcePath).name}: Güvensiz veya çözülmemiş hareket dışa aktarılamaz.")
            if self.preview:
                key=preview_key(p,self.width,self.height)
                self.target=self.target.parent/f"{key}.mp4"
                if self.target.exists():
                    data=json.loads(self.process("ffprobe",["-v","error","-count_frames","-show_streams","-show_format","-of","json",self.target]))
                    validate_probe(data,total,p.fps,self.width,self.height)
                    self.process("ffmpeg",["-v","error","-xerror","-i",self.target,"-f","null","-"])
                    self.check_cancel()
                    self.progress.emit(100,"Önizleme hazır")
                    self.succeeded.emit(str(self.target),data);return
            temp=Path(tempfile.mkdtemp(prefix=".dsf-render-",dir=self.target.parent))
            completed=0
            clips=[]
            signatures=[]
            for i,c in enumerate(p.clips):
                self.check_cancel()
                self.progress.emit(int(85*completed/total),f"Görsel {i+1}/{len(p.clips)} hazırlanıyor…")
                source=temp/"source.png"
                before=fingerprint(c.sourcePath)
                size,notes=normalize(c.sourcePath,source,p.background)
                after=fingerprint(c.sourcePath)
                if before!=after or (c.sourceFingerprint and after["sha256"]!=c.sourceFingerprint.get("sha256")):
                    raise ValueError("Kaynak işlem sırasında değişti; işi yeniden başlatın.")
                if tuple(size)!=(c.sourceWidth,c.sourceHeight): raise ValueError("Kaynak ölçüsü değişmiş; yeniden bağlayın.")
                self.log.append({"source":c.sourcePath,"notes":notes})
                clip=temp/f"clip_{i:05d}.mp4"
                self.process("ffmpeg",clip_args(source,clip,c.motionResolved,c.durationFrames,p.fps,self.width,self.height),
                    lambda n,base=completed,idx=i: self.progress.emit(min(85,int(85*(base+min(n,c.durationFrames))/total)),f"Görsel {idx+1}/{len(p.clips)} işleniyor…"))
                info=json.loads(self.process("ffprobe",["-v","error","-show_streams","-show_format","-of","json",clip]))
                validate_probe(info,c.durationFrames,p.fps,self.width,self.height)
                s=info["streams"][0]
                signatures.append(tuple(s.get(k) for k in ("codec_name","profile","level","width","height","pix_fmt","time_base","extradata_size")))
                if signatures[-1]!=signatures[0]: raise RuntimeError("Ara klipler birleştirme için uyumlu değil.")
                clips.append(clip)
                source.unlink()
                completed+=c.durationFrames
            self.progress.emit(88,"Klipler tek videoda birleştiriliyor…")
            listing=temp/"concat.txt"
            listing.write_text("".join(f"file '{c.name}'\n" for c in clips),encoding="utf-8")
            combined=temp/"complete.mp4"
            self.process("ffmpeg",["-hide_banner","-nostdin","-y","-v","error","-f","concat","-safe","1","-i",listing,
                                  "-map","0:v:0","-c","copy","-an","-movflags","+faststart",combined])
            self.progress.emit(93,"Kare sayısı ve çıktı profili doğrulanıyor…")
            data=json.loads(self.process("ffprobe",["-v","error","-count_frames","-show_streams","-show_format","-of","json",combined]))
            validate_probe(data,total,p.fps,self.width,self.height)
            self.progress.emit(97,"Video baştan sona çözülerek denetleniyor…")
            self.process("ffmpeg",["-v","error","-xerror","-i",combined,"-f","null","-"])
            self.check_cancel()
            os.replace(combined,self.target)
            data["dsf"]={"elapsedSeconds":round(time.monotonic()-self.started_at,3),"renderer":RENDERER_VERSION,"sources":self.log}
            if self.preview:
                # Bounded on-disk cache, only own content-addressed files.
                old=sorted((x for x in self.target.parent.glob("*.mp4") if len(x.stem)==64 and x.stem.isalnum()),key=lambda x:x.stat().st_mtime,reverse=True)
                for x in old[8:]:
                    try: x.unlink()
                    except OSError: pass
            self.progress.emit(100,"Tamamlandı — çıktı doğrulandı")
            self.succeeded.emit(str(self.target),data)
        except Cancelled:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if temp is not None:
                # Only the unique directory created by this job, under target disk.
                if temp.parent.resolve()==self.target.parent.resolve() and temp.name.startswith(".dsf-render-"):
                    shutil.rmtree(temp,ignore_errors=True)
