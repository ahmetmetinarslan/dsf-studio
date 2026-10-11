import json
import os
from pathlib import Path
from unittest.mock import patch
from acceptance import ROOT,OUT,run_job,single
from dsf.media import normalize
from PIL import Image

results={}
source=ROOT/"artifacts"/"stage1"/"source.png"
extra_out=OUT/"extra";extra_out.mkdir(exist_ok=True)
target=extra_out/"mid_failure.mp4";target.write_bytes(b"previous-success")
def disk_error(*args,**kwargs):
    normalize(*args,**kwargs)
    raise OSError(28,"Disk alanı işlem sırasında tükendi")
with patch("dsf.jobs.normalize",side_effect=disk_error):r=run_job(single(source,frames=25),target)
assert "Disk alanı" in r.get("error","") and target.read_bytes()==b"previous-success"
assert not list(extra_out.glob(".dsf-render-*"))
results["diskFailureDuringPreparation"]={"error":r["error"],"previousOutputPreserved":True,"simulated":True}
with patch("dsf.jobs.os.replace",side_effect=OSError(28,"Disk metadata alanı dolu")):
    r=run_job(single(source,frames=25),target)
assert "Disk metadata" in r.get("error","") and target.read_bytes()==b"previous-success"
results["diskFailureAtCommit"]={"error":r["error"],"previousOutputPreserved":True,"simulated":True}
long_dir=OUT/"uzun_yol"/("haber_"+"a"*90)/("şğü_"+"b"*90)/("c"*70)
long_dir.mkdir(parents=True,exist_ok=True)
long_source=long_dir/"Türkçe boşluk görsel.png";Image.new("RGB",(1920,1080),"#308070").save(long_source)
long_target=long_dir/"Türkçe çıktı.mp4"
r=run_job(single(long_source,frames=25),long_target)
assert "error" not in r,r
results["longTurkishPaths"]={"sourcePathLength":len(str(long_source)),"outputPathLength":len(str(long_target)),"frames":r["data"]["streams"][0]["nb_read_frames"]}
(OUT/"extra.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps(results,ensure_ascii=False,indent=2),flush=True)
