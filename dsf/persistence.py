import json
import os
from pathlib import Path
import tempfile
from .model import Project


def save_project(project,path):
    path=Path(path).resolve()
    data=project.to_dict()
    for c in data["clips"]:
        source=Path(c["sourcePath"]).resolve()
        try: c["sourcePath"]=source.relative_to(path.parent).as_posix()
        except ValueError: c["sourcePath"]=str(source)
    # Validate before replacing any previous successful save.
    Project.from_dict(data)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,prefix=".dsf-save-",suffix=".tmp",delete=False) as f:
            temp=Path(f.name)
            json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if temp and temp.exists(): temp.unlink()


def load_project(path):
    path=Path(path).resolve()
    if path.stat().st_size>20*1024*1024: raise ValueError("Proje dosyası 20 MB sınırını aşıyor.")
    data=json.loads(path.read_text(encoding="utf-8-sig"),parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Geçersiz sayısal değer")))
    project=Project.from_dict(data)
    for c in project.clips:
        p=Path(c.sourcePath)
        c.sourcePath=str((path.parent/p).resolve() if not p.is_absolute() else p)
        if not Path(c.sourcePath).is_file(): c.mediaError="Dosya bulunamadı — Yeniden bağla düğmesini kullanın."
    return project
