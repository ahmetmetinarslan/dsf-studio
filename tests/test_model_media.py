from copy import deepcopy
import json
from pathlib import Path
import pytest
from PIL import Image
from dsf.model import Project,Clip,duration_frames
from dsf.media import load_image,MediaError,fingerprint
from dsf.persistence import save_project,load_project
from dsf.jobs import preview_key


@pytest.fixture
def source(tmp_path):
    p=tmp_path/"Türkçe boşluk şğü.png";Image.new("RGB",(320,180),"red").save(p);return p


def test_duration_rounding():
    assert duration_frames(8,25)==200
    assert duration_frames(1.02,25)==26
    assert duration_frames(1.01,50)==51


def test_roundtrip_and_atomic_save(source,tmp_path):
    p=Project();p.clips=[Clip(str(source),sourceWidth=320,sourceHeight=180,protectedRegions=[(.2,.2,.8,.8)],locked=True)]
    p.resolve(p.clips[0]);target=tmp_path/"Proje ş.dsfproj";save_project(p,target)
    assert not Path(json.loads(target.read_text(encoding="utf8"))["clips"][0]["sourcePath"]).is_absolute()
    q=load_project(target);assert q.to_dict()==p.to_dict()
    original=target.read_bytes();p.fps=17
    with pytest.raises(ValueError):save_project(p,target)
    assert target.read_bytes()==original


def test_future_version_untouched(source,tmp_path):
    p=tmp_path/"future.dsfproj";p.write_text('{"schemaVersion": 99}',encoding="utf8")
    before=p.read_bytes()
    with pytest.raises(ValueError,match="sürümü"):load_project(p)
    assert p.read_bytes()==before


@pytest.mark.parametrize("change",[
    lambda d:d["output"].update(fpsNum=30),lambda d:d["defaults"].update(maxZoom=float('nan')),
    lambda d:d["clips"][0].update(durationFrames=0),lambda d:d["clips"][0].update(amount=float('inf')),
    lambda d:d["clips"][0].update(locked="yes"),lambda d:d["clips"][0].update(focus=[1.1,.5]),
    lambda d:d["safeArea"].update(left=-1),lambda d:d["clips"][0]["motionResolved"]["end"].update(tx=1),
    lambda d:d["clips"][0].update(notes=[{}]),
    lambda d:d["clips"][0]["motionResolved"].update(status="invalid_region",start={"z":"bad","tx":0,"ty":0}),
    lambda d:d["clips"][0]["motionResolved"].update(applied=float('nan')),
])
def test_schema_rejects_bad_values(change,source):
    p=Project(clips=[Clip(str(source))]);p.resolve(p.clips[0]);d=p.to_dict();change(d)
    with pytest.raises(ValueError):Project.from_dict(d)


def test_automatic_locked_persisted(source,tmp_path):
    p=Project(allowedMotions=["pan_left","zoom_in"])
    p.clips=[Clip(str(source),protectedRegions=[(.2,.2,.8,.8)]) for _ in range(12)]
    for c in p.clips:p.resolve(c)
    p.clips[4].locked=True;locked=deepcopy(p.clips[4]);p.redistribute()
    assert p.clips[4]==locked
    for c in p.clips:assert c.motionResolved.kind in p.allowedMotions
    path=tmp_path/"auto.dsfproj";save_project(p,path);q=load_project(path)
    assert q.to_dict()==p.to_dict()
    before=p.to_dict();preview_key(p,960,540);assert p.to_dict()==before
    p.allowedMotions=[]
    with pytest.raises(ValueError):p.redistribute()


def test_preview_cache_content_and_geometry(source):
    p=Project(clips=[Clip(str(source))]);p.resolve(p.clips[0]);key=preview_key(p,960,540)
    Image.new("RGB",(320,180),"blue").save(source)
    assert preview_key(p,960,540)!=key
    key=preview_key(p,960,540);p.clips[0].amount=.12;p.resolve(p.clips[0])
    assert preview_key(p,960,540)!=key
    assert preview_key(p,1920,1080)!=preview_key(p,960,540)


def test_media_validation_exif_alpha_and_small(source,tmp_path):
    im,notes=load_image(source);assert im.size==(320,180) and any("Küçük" in x for x in notes)
    bad=tmp_path/"bad.png";bad.write_text("not an image")
    with pytest.raises(MediaError):load_image(bad)
    wrong=tmp_path/"portrait.png";Image.new("RGB",(180,320)).save(wrong)
    with pytest.raises(MediaError,match="16:9"):load_image(wrong)
    rotated=tmp_path/"rotation.jpg";exif=Image.Exif();exif[274]=6;Image.new("RGB",(180,320)).save(rotated,exif=exif)
    assert load_image(rotated)[0].size==(320,180)
    alpha=tmp_path/"alpha.png";Image.new("RGBA",(320,180),(255,0,0,0)).save(alpha)
    assert load_image(alpha,"#123456")[0].getpixel((0,0))==(18,52,86)
    icc=tmp_path/"icc.png";Image.new("RGB",(320,180)).save(icc,icc_profile=b"broken")
    with pytest.raises(MediaError,match="ICC"):load_image(icc)


def test_missing_file_marked(source,tmp_path):
    p=Project(clips=[Clip(str(source))]);p.resolve(p.clips[0]);file=tmp_path/"test.dsfproj";save_project(p,file);source.unlink()
    assert "bulunamadı" in load_project(file).clips[0].mediaError
