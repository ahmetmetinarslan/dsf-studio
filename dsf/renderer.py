"""FFmpeg komutları. Geometri yalnızca motion.Plan üzerinden gelir."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

RENDERER_VERSION = "dsf-1.0-srgb-bt709-oetf-2x-v2"


def tool_path(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidates = [base / "tools" / f"{name}.exe"]
    candidates += list((base / "tools" / "vendor").glob(f"*/bin/{name}.exe"))
    for p in candidates:
        if p.is_file():
            return str(p)
    p = shutil.which(name)
    if p:
        return p
    raise RuntimeError(f"{name} bulunamadı. Uygulama paketindeki tools klasörünü kontrol edin.")


def run_tool(name, args, timeout=120):
    result = subprocess.run([tool_path(name), *map(str, args)], capture_output=True,
        timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-4000:])
    return result.stdout.decode("utf-8", "replace")


def capabilities():
    filters = run_tool("ffmpeg", ["-hide_banner", "-filters"])
    encoders = run_tool("ffmpeg", ["-hide_banner", "-encoders"])
    for name in ("zoompan", "zscale", "scale"):
        if name not in filters:
            raise RuntimeError(f"Paketli FFmpeg gerekli {name} filtresini içermiyor.")
    if "libx264" not in encoders:
        raise RuntimeError("H.264 (libx264) kodlayıcısı eksik.")
    return {"ffmpeg": run_tool("ffmpeg", ["-version"]).splitlines()[0],
            "ffprobe": run_tool("ffprobe", ["-version"]).splitlines()[0]}


def expression(start, end, frames, easing):
    p = f"(on/{max(1, frames-1)})"
    a = f"(3*{p}*{p}-2*{p}*{p}*{p})" if easing == "smoothstep" else p
    return f"({start:.14g}+({end-start:.14g})*{a})"


def video_filter(plan, frames, fps, width=1920, height=1080):
    z, tx, ty = [expression(getattr(plan.start, a), getattr(plan.end, a), frames, plan.easing)
                  for a in ("z", "tx", "ty")]
    # Explicit inverse sRGB EOTF + BT.709 OETF. zimg's display-referred 709
    # transfer uses BT.1886; it is deliberately not used for this OETF contract.
    linear="if(lte(val/65535,0.04045),val/65535/12.92,pow((val/65535+0.055)/1.055,2.4))"
    transfer=f"65535*if(lt({linear},0.018),4.5*{linear},1.099*pow({linear},0.45)-0.099)"
    lut=":".join(f"{channel}='{transfer}'" for channel in ("r","g","b"))
    # Geometry always uses 3840x2160, including 540p previews, so the rounding
    # is shared. Matrix/range conversion is explicit and separate from transfer.
    return (f"format=gbrp16le,lutrgb={lut},format=gbrp,scale=3840:2160:flags=lanczos,"
            f"zoompan=z='{z}':x='iw*(-{tx}/{z})':y='ih*(-{ty}/{z})':"
            f"d={frames}:s=3840x2160:fps={fps},"
            f"scale={width}:{height}:flags=lanczos,format=gbrp16le,"
            "zscale=pin=709:tin=709:min=gbr:rin=full:p=709:t=709:m=709:r=limited:dither=error_diffusion,"
            "format=yuv420p,setsar=1,setpts=PTS-STARTPTS,"
            "setparams=range=limited:color_primaries=bt709:color_trc=bt709:colorspace=bt709")


def clip_args(source, dest, plan, frames, fps=25, width=1920, height=1080):
    return ["-hide_banner", "-nostdin", "-y", "-v", "error", "-progress", "pipe:1",
            "-threads", "2", "-i", str(source), "-vf", video_filter(plan, frames, fps, width, height),
            "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-threads", "4", "-filter_threads", "2", "-pix_fmt", "yuv420p",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-color_range", "tv", "-chroma_sample_location", "left", "-field_order", "progressive",
            "-video_track_timescale", str(fps*512), "-movflags", "+faststart", str(dest)]


def probe(path, count=True):
    args = ["-v", "error", "-show_streams", "-show_format", "-of", "json"]
    if count:
        args += ["-count_frames"]
    return json.loads(run_tool("ffprobe", [*args, str(path)], timeout=600))


def validate_probe(data, frames, fps, width, height):
    streams = data["streams"]
    if len(streams) != 1 or streams[0]["codec_type"] != "video":
        raise RuntimeError("Çıktı tek ve sessiz video akışı içermiyor.")
    s = streams[0]
    expected = {"codec_name": "h264", "width": width, "height": height,
                "pix_fmt": "yuv420p", "color_space": "bt709", "color_transfer": "bt709",
                "color_primaries": "bt709", "color_range": "tv", "sample_aspect_ratio": "1:1"}
    for key, value in expected.items():
        if s.get(key) != value:
            raise RuntimeError(f"Çıktı doğrulanamadı: {key}={s.get(key)}, beklenen {value}")
    if int(s.get("nb_read_frames", s.get("nb_frames", -1))) != frames:
        raise RuntimeError("Çıktı kare sayısı beklenen değerle eşleşmiyor.")
    if s["r_frame_rate"] != f"{fps}/1" or abs(float(s["duration"])-frames/fps) > 0.001:
        raise RuntimeError("Çıktı süresi veya kare hızı yanlış.")
    if s.get("field_order") not in ("progressive", "unknown"):
        raise RuntimeError("Çıktı progressive değil.")


def render_single(source, dest, plan, frames=200, fps=25, width=1920, height=1080):
    """Developer smoke helper. Desktop exports use the cancellable QProcess queue."""
    run_tool("ffmpeg", clip_args(source, dest, plan, frames, fps, width, height), timeout=1800)
    data = probe(dest)
    validate_probe(data, frames, fps, width, height)
    run_tool("ffmpeg", ["-v", "error", "-xerror", "-i", str(dest), "-f", "null", "-"], timeout=600)
    return data
