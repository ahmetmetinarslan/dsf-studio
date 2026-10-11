"""Build a portable folder with Python, Qt, FFmpeg, licenses and build metadata."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dsf.renderer import tool_path,capabilities,run_tool


def main():
    if sys.platform!="win32":raise SystemExit("Windows paketi Windows üzerinde oluşturulmalıdır.")
    subprocess.run([sys.executable,"-m","PyInstaller","--noconfirm","--clean","--windowed","--onedir",
        "--name","DSF-Studio","--distpath",str(ROOT/"dist"),"--workpath",str(ROOT/"build"),
        "--specpath",str(ROOT/"build"),"--paths",str(ROOT),
        "--add-binary",f"{tool_path('ffmpeg')};tools","--add-binary",f"{tool_path('ffprobe')};tools",
        "--collect-submodules","PySide6.QtMultimedia","--collect-submodules","PySide6.QtMultimediaWidgets",
        str(ROOT/"main.py")],cwd=ROOT,check=True)
    package=ROOT/"dist"/"DSF-Studio";licenses=package/"licenses";licenses.mkdir(exist_ok=True)
    for name in ("PySide6","PySide6_Essentials","PySide6_Addons","shiboken6","Pillow","pyinstaller"):
        dist=importlib.metadata.distribution(name)
        for item in dist.files or []:
            path=Path(dist.locate_file(item))
            if path.is_file() and (any(s in path.name.lower() for s in ("license","copying","notice","copyright")) or "licenses" in [x.lower() for x in path.parts]):
                relative=Path(str(item).replace("..","_"))
                target=licenses/name/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    ffroot=ROOT/"tools"/"runtime"
    for p in ffroot.glob("*/LICENSE*"):shutil.copy2(p,licenses/("FFmpeg-"+p.name))
    for p in ffroot.glob("*/README*"):shutil.copy2(p,licenses/("FFmpeg-"+p.name))
    if (ROOT/"licenses").exists():shutil.copytree(ROOT/"licenses",licenses,dirs_exist_ok=True)
    for name in ("README.md","THIRD_PARTY_NOTICES.md","requirements.lock"):
        if (ROOT/name).exists():shutil.copy2(ROOT/name,package/name)
    if (ROOT/"examples").exists():shutil.copytree(ROOT/"examples",package/"examples",dirs_exist_ok=True)
    build={"app":"DSF Studio 1.0.0","python":sys.version,"platform":platform.platform(),"tools":capabilities(),
           "ffmpegConfiguration":run_tool("ffmpeg",["-version"]),
           "dependencies":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()},
           "binaries":{name:hashlib.sha256(Path(tool_path(name)).read_bytes()).hexdigest() for name in ("ffmpeg","ffprobe")}}
    (package/"BUILD_INFO.json").write_text(json.dumps(build,indent=2,ensure_ascii=False),encoding="utf8")
    (ROOT/"BUILD_INFO.json").write_text(json.dumps(build,indent=2,ensure_ascii=False),encoding="utf8")
    print("Built:",package/"DSF-Studio.exe",flush=True)


if __name__=="__main__":main()
