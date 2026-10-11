"""Synthetic marker measurements independent from the geometry implementation."""
import io
import os
import subprocess
from PIL import Image
from dsf.renderer import tool_path


def frame(path, k):
    r = subprocess.run([tool_path("ffmpeg"), "-v", "error", "-i", str(path), "-vf",
        f"select=eq(n\\,{k})", "-frames:v", "1", "-f", "image2pipe", "-c:v", "png", "-"],
        capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    return Image.open(io.BytesIO(r.stdout)).convert("RGB")


def red_bounds(im):
    # Pillow C-level channels avoid storing decoded videos or large pixel lists.
    r, g, b = im.split()
    from PIL import ImageChops
    red = ImageChops.subtract(r, g).point(lambda p: 255 if p > 75 else 0)
    red = ImageChops.multiply(red, ImageChops.subtract(r, b).point(lambda p: 255 if p > 75 else 0))
    bounds = red.getbbox()
    if bounds is None:
        raise AssertionError("Red test marker absent")
    return bounds


def measure_direction(path, kind, frames=200):
    first, last = frame(path, 0), frame(path, frames-1)
    a,b = red_bounds(first), red_bounds(last)
    cx = lambda r: (r[0]+r[2])/2
    cy = lambda r: (r[1]+r[3])/2
    if kind == "zoom_in": assert b[2]-b[0] > a[2]-a[0]
    if kind == "zoom_out": assert b[2]-b[0] < a[2]-a[0]
    if kind == "pan_left": assert cx(b) > cx(a)+20
    if kind == "pan_right": assert cx(b) < cx(a)-20
    if kind == "pan_up": assert cy(b) > cy(a)+20
    if kind == "pan_down": assert cy(b) < cy(a)-20
    for im in (first, frame(path, frames//2), last):
        w,h = im.size
        for xy in ((0,0),(w-1,0),(0,h-1),(w-1,h-1),(0,h//2),(w-1,h//2)):
            assert max(im.getpixel(xy)) > 30, (path, xy, "unexpected blank edge")
    return {"firstBounds":a,"lastBounds":b,"direction":"passed","edges":"passed"}
