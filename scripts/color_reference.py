import json
from acceptance import ROOT,OUT,run_job,single
from pixel_checks import frame
from PIL import Image,ImageDraw

source=OUT/"rgb_reference.png";im=Image.new("RGB",(1920,1080));d=ImageDraw.Draw(im)
values=list(range(0,256,17))
for row in range(4):
    for col,v in enumerate(values):
        rgb=(v,v,v) if row==0 else tuple(v if i==row-1 else 0 for i in range(3))
        d.rectangle((col*120,row*270,col*120+119,row*270+269),fill=rgb)
im.save(source)
r=run_job(single(source,"static",25),OUT/"rgb_reference.mp4");assert "error" not in r,r
decoded=frame(r["path"],0);errors=[]
def convert(v):
    s=v/255;linear=s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4
    return round(255*(4.5*linear if linear<.018 else 1.099*linear**.45-.099))
for row in range(4):
    for col,v in enumerate(values):
        expected=tuple(convert(v) if row==0 or i==row-1 else 0 for i in range(3))
        actual=decoded.getpixel((col*120+60,row*270+135))
        errors.append(max(abs(x-y) for x,y in zip(expected,actual)))
assert max(errors)<=4,errors
result={"swatches":64,"channels":"gray, red, green, blue","maxError8bit":max(errors),"expected":"inverse sRGB EOTF then BT.709 OETF; BT.709 YUV matrix, limited range"}
(OUT/"color_reference.json").write_text(json.dumps(result,indent=2),encoding="utf8");print(json.dumps(result),flush=True)
