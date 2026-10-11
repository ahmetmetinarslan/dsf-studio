import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from dsf.model import Project,Clip
from dsf.media import fingerprint
from dsf.persistence import save_project


def create(root):
    root=Path(root);assets=root/"assets";assets.mkdir(parents=True,exist_ok=True)
    font=lambda s:ImageFont.truetype("C:/Windows/Fonts/arial.ttf",s)
    p=Project(name="Örnek haber akışı · 10 görsel")
    labels=["GÜNDEM","EKONOMİ","BİLİM","ULAŞIM","ENERJİ","EĞİTİM","ÇEVRE","KÜLTÜR","TEKNOLOJİ","DÜNYA"]
    colors=["#143047","#203954","#22433e","#383b59","#414332","#183d55","#254437","#483653","#1b4553","#303951"]
    motions=["zoom_in","zoom_out","pan_left","pan_right","pan_up","pan_down","zoom_in","pan_left","zoom_out","pan_down"]
    for i,(label,color,kind) in enumerate(zip(labels,colors,motions)):
        im=Image.new("RGB",(1920,1080),color);d=ImageDraw.Draw(im)
        for x in range(0,1920,80):d.line((x,0,x,1080),fill="#466174",width=1)
        for y in range(0,1080,80):d.line((0,y,1920,y),fill="#466174",width=1)
        d.rectangle((0,0,1919,1079),outline="#d8b957",width=10)
        d.rounded_rectangle((260,190,1660,880),28,fill="#13202e")
        d.rectangle((310,250,322,308),fill="#48ccb2")
        d.text((352,245),label,font=font(48),fill="#48ccb2")
        d.text((310,365),f"Haber görseli {i+1:02d}",font=font(90),fill="white")
        d.text((310,495),"Yavaş hareket · güvenli kadraj",font=font(48),fill="#b9ccdf")
        d.text((310,585),"DSF STUDIO / ÖRNEK PROJE",font=font(30),fill="#96aabd")
        d.text((310,766),"TEMSİLİ TEST GÖRSELİ — gerçek haber değildir",font=font(25),fill="#9fb2c6")
        for j in range(6):
            x=1130+j*65;h=80+((j+i)%5)*32
            d.rectangle((x,730-h,x+38,730),fill="#3dac9e")
        path=assets/f"haber_{i+1:02d}_örnek.png";im.save(path)
        c=Clip(str(path.resolve()),motionRequested=kind,amount=.1 if kind.startswith("pan") else .08,
               protectedRegions=[(.15,.18,.85,.80)],sourceFingerprint=fingerprint(path),locked=i==0,
               notes=["ICC profili yok; sRGB varsayıldı"])
        p.resolve(c);p.clips.append(c)
    save_project(p,root/"Ornek_Haber.dsfproj")
    return p


if __name__=="__main__":
    create(Path(__file__).resolve().parents[1]/"examples")
    print("10-image example project created")
