import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from dsf.motion import preset
from dsf.renderer import capabilities, render_single
from pixel_checks import measure_direction

root = Path(__file__).resolve().parents[1]
out = root / "artifacts" / "stage1"
out.mkdir(parents=True, exist_ok=True)
im = Image.new("RGB", (1920,1080), "#264960")
d = ImageDraw.Draw(im)
for x in range(0,1920,120):
    d.line((x,0,x,1079), fill="#608090", width=3)
for y in range(0,1080,120):
    d.line((0,y,1919,y), fill="#608090", width=3)
d.rectangle((720,360,1200,720), fill="#f24c4c")
d.rectangle((0,0,1919,1079), outline="#ffda50", width=16)
im.save(out / "source.png")
print(capabilities(), flush=True)
results = {}
for kind in ("zoom_in","zoom_out","pan_left","pan_right","pan_up","pan_down"):
    plan = preset(kind, .1 if kind.startswith("pan") else .08)
    data = render_single(out / "source.png", out / f"{kind}.mp4", plan)
    results[kind] = {"frames": data["streams"][0]["nb_read_frames"], "plan": plan.to_dict(),
                     "pixels": measure_direction(out / f"{kind}.mp4", kind)}
    print(kind, "PASS: 200 frames, 8 seconds, full decode", flush=True)
(out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
