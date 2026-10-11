import hashlib
import io
from pathlib import Path
from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError


class MediaError(ValueError):
    pass


def fingerprint(path):
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    st = p.stat()
    return {"size": st.st_size, "mtimeNs": st.st_mtime_ns, "sha256": h.hexdigest()}


def load_image(path, background="#000000"):
    try:
        with Image.open(path) as raw:
            if raw.format not in ("JPEG", "PNG"):
                raise MediaError("Yalnızca gerçek JPG ve PNG dosyaları desteklenir.")
            raw.load()
            icc = raw.info.get("icc_profile")
            im = ImageOps.exif_transpose(raw)
            w, h = im.size
            if w * 9 != h * 16:
                raise MediaError(f"16:9 görsel gerekli; yön düzeltmesi sonrası {w}×{h}. Görsel esnetilmedi veya kırpılmadı.")
            notes = []
            alpha = im.convert("RGBA").getchannel("A") if "A" in im.getbands() or "transparency" in im.info else None
            if icc:
                try:
                    profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
                    base = im if im.mode in ("RGB", "CMYK", "LAB") else im.convert("RGB")
                    im = ImageCms.profileToProfile(base, profile, ImageCms.createProfile("sRGB"), outputMode="RGB")
                except Exception as e:
                    raise MediaError("ICC renk profili okunamadı veya desteklenmiyor.") from e
                notes.append("ICC profili sRGB'ye dönüştürüldü")
            else:
                if im.mode == "CMYK":
                    raise MediaError("CMYK görsel için geçerli ICC profili gerekli.")
                im = im.convert("RGB")
                notes.append("ICC profili yok; sRGB varsayıldı")
            if alpha is not None:
                bg = Image.new("RGB", im.size, background)
                bg.paste(im, mask=alpha)
                im = bg
            if w < 1920:
                notes.append("Küçük görsel: büyütme ayrıntı kaybına yol açabilir")
            return im.copy(), notes
    except MediaError:
        raise
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as e:
        raise MediaError(f"Görsel açılamadı: {Path(path).name}. {e}") from e


def normalize(path, destination, background="#000000"):
    im, notes = load_image(path, background)
    im.save(destination, "PNG")
    return im.size, notes
