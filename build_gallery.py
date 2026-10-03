#!/usr/bin/env python3
"""Drop photos/videos into gallery-source/, run `python3 build_gallery.py`.
Makes web-sized copies in gallery/ and writes gallery-data.js for the page.
The video named main.* is the featured one, centred and playing live."""
import json, os, subprocess, pathlib
from PIL import Image, ImageOps

SRC, OUT = pathlib.Path("gallery-source"), pathlib.Path("gallery")
IMG, VID = {".jpg", ".jpeg", ".png", ".webp"}, {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")  # set FFMPEG=/path if your ffmpeg lacks HEVC/H.264
OUT.mkdir(exist_ok=True)
_enc = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
# H.264 MP4 plays everywhere; if this ffmpeg lacks libx264, fall back to VP9/Opus WebM
if "libx264" in _enc:
    VEXT, VCODEC, ACODEC = "mp4", ["-c:v", "libx264", "-crf", "26", "-preset", "medium"], ["-c:a", "aac", "-b:a", "96k"]
else:
    VEXT, VCODEC, ACODEC = "webm", ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4"], ["-c:a", "libopus", "-b:a", "96k"]
items = []
for f in sorted(SRC.iterdir(), key=lambda p: p.name.lower()):
    if f.suffix.lower() not in IMG | VID:
        print("skipped (unsupported):", f.name); continue
    ext, stem = f.suffix.lower(), "".join(c if c.isalnum() else "-" for c in f.stem).lower()
    if ext in IMG:
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(OUT / f"{stem}.jpg", quality=82, optimize=True)
        items.append({"type": "photo", "src": f"gallery/{stem}.jpg", "w": im.width, "h": im.height})
    elif ext in VID:
        mp4, poster = OUT / f"{stem}.{VEXT}", OUT / f"{stem}-poster.jpg"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(f), "-map", "0:v:0", "-map", "0:a:0?", "-vf", "scale='min(1600,iw)':-2",
                        *VCODEC, "-pix_fmt", "yuv420p",
                        *ACODEC, "-movflags", "+faststart", str(mp4)], check=True)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", "1", "-i", str(mp4),
                        "-frames:v", "1", "-q:v", "3", str(poster)], check=True)
        w, h = Image.open(poster).size
        items.append({"type": "video", "src": f"gallery/{stem}.{VEXT}", "poster": f"gallery/{stem}-poster.jpg", "w": w, "h": h,
                      "main": stem == "main"})
pathlib.Path("gallery-data.js").write_text("window.GALLERY = " + json.dumps(items, indent=1) + ";\n")
print(f"{len(items)} items -> gallery-data.js")
