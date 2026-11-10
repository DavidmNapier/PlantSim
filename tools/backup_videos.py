"""Record and encode presenter backup videos: one MP4 per story chapter plus the whole story.

    py tools/backup_videos.py [chapters...]       e.g.  py tools/backup_videos.py 3 5
    py tools/backup_videos.py cyclone             the standalone hydrocyclone explainer only

Plain Python driver (not Blender). For each chapter it runs tools/record.py in the GUI at
1920x1080, every frame (24 fps, KPI panel, tags and captions included), encodes the frames
with tools/encode.py, then deletes them. Writes renders/backup/chN_<title>.mp4 and, when
all 7 chapters exist and ffmpeg is on PATH, renders/backup/full_story.mp4 (joined without
re-encoding). Needs build/plant_demo.blend (run build.py first) and AC power: a throttled
laptop records fine, only slower.
"""
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from demo import config  # noqa: E402

BLEND = os.path.join(ROOT, "build", "plant_demo.blend")
OUT = os.path.join(ROOT, "renders", "backup")
FRAMES = os.path.join(OUT, "frames")
BLENDER = shutil.which("blender") or "blender"


def name(i):
    slug = re.sub(r"[^a-z0-9]+", "_", config.STORY[i - 1][0].lower()).strip("_")
    return os.path.join(OUT, f"ch{i}_{slug}.mp4")


def run(args, timeout):
    t = time.time()
    subprocess.run(args, check=True, timeout=timeout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.time() - t


def chapter(i):
    secs = config.STORY[i - 1][1]
    shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES)
    dt = run([BLENDER, "-y", "-p", "0", "0", "1920", "1080", BLEND, "-P", os.path.join(ROOT, "tools", "record.py"),
              "--", str(i), str(i), "1", FRAMES], timeout=secs * 24 * 3 + 300)
    n = len([f for f in os.listdir(FRAMES) if f.endswith(".png")])
    if n < secs * 24 - 2:
        sys.exit(f"ch{i}: only {n} frames recorded (expected {secs * 24})")
    out = name(i)
    run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(ROOT, "tools", "encode.py"), "--",
         str(config.STORY_FPS), out, FRAMES], timeout=1800)
    shutil.rmtree(FRAMES, ignore_errors=True)
    print(f"ch{i}: {n} frames recorded in {dt:.0f} s -> {out} ({os.path.getsize(out) / 1e6:.0f} MB)", flush=True)


def cyclone():
    """renders/backup/cyclone_explainer.mp4: the explainer stepping through its modes."""
    secs = config.EXPLAINER_VIDEO[-1][1]
    blend = os.path.join(ROOT, "build", "cyclone_explainer.blend")
    shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES)
    dt = run([BLENDER, "-y", "-p", "0", "0", "1920", "1080", blend, "-P",
              os.path.join(ROOT, "tools", "record_cyclone.py"), "--", FRAMES], timeout=secs * 24 * 3 + 300)
    n = len([f for f in os.listdir(FRAMES) if f.endswith(".png")])
    if n < secs * 24 - 2:
        sys.exit(f"cyclone: only {n} frames recorded (expected {secs * 24})")
    out = os.path.join(OUT, "cyclone_explainer.mp4")
    run([BLENDER, "-b", "--factory-startup", "-P", os.path.join(ROOT, "tools", "encode.py"), "--",
         "24", out, FRAMES], timeout=1800)
    shutil.rmtree(FRAMES, ignore_errors=True)
    print(f"cyclone: {n} frames recorded in {dt:.0f} s -> {out} ({os.path.getsize(out) / 1e6:.0f} MB)", flush=True)


def join():
    parts = [name(i) for i in range(1, len(config.STORY) + 1)]
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not all(os.path.exists(p) for p in parts):
        print("full_story.mp4 skipped (needs all chapters and ffmpeg on PATH)")
        return
    lst = os.path.join(OUT, "parts.txt")
    with open(lst, "w") as f:
        f.write("".join(f"file '{p}'\n".replace("\\", "/") for p in parts))
    full = os.path.join(OUT, "full_story.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", full],
                   check=True)
    os.remove(lst)
    print(f"full story -> {full} ({os.path.getsize(full) / 1e6:.0f} MB)")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1:] == ["cyclone"]:
        cyclone()
        sys.exit(0)
    chs = [int(a) for a in sys.argv[1:]] or list(range(1, len(config.STORY) + 1))
    for i in chs:
        chapter(i)
    join()
