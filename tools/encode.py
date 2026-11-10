"""Encode SRC/f_*.png (default renders/clip) into an H.264 MP4 with Blender's sequencer,
cropped to the recorded 3D view.

    blender -b --factory-startup -P tools/encode.py -- [fps] [out.mp4] [src_dir]
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FPS = int(argv[0]) if argv else 12
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = argv[1] if len(argv) > 1 else os.path.join(ROOT, "renders", "backup_ch3-6.mp4")
SRC = argv[2] if len(argv) > 2 else os.path.join(ROOT, "renders", "clip")
files = sorted(f for f in os.listdir(SRC) if f.endswith(".png"))
scene = bpy.context.scene
scene.sequence_editor_create()
strips = scene.sequence_editor.strips if hasattr(scene.sequence_editor, "strips") else scene.sequence_editor.sequences
s = strips.new_image("clip", os.path.join(SRC, files[0]), 1, 1)
for f in files[1:]:
    s.elements.append(f)
import json  # noqa: E402
rect = json.load(open(os.path.join(SRC, "rect.json")))
img = bpy.data.images.load(os.path.join(SRC, files[0]))
W, H = img.size
sx, sy = W / rect["win_w"], H / rect["win_h"]            # screenshot px per window px
x, y, w, h = (int(rect["x"] * sx), int(rect["y"] * sy), int(rect["w"] * sx), int(rect["h"] * sy))
s.crop.min_x, s.crop.max_x = x, W - (x + w)
s.crop.min_y, s.crop.max_y = y, H - (y + h)
if hasattr(s, "transform"):
    s.transform.offset_x, s.transform.offset_y = -x, -y
r = scene.render
scene.view_settings.view_transform = "Standard"           # screenshots are already display sRGB
scene.view_settings.look = "None"
scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
r.resolution_x, r.resolution_y, r.resolution_percentage = w - w % 2, h - h % 2, 100
r.fps = FPS
scene.frame_start, scene.frame_end = 1, len(files)
if hasattr(r.image_settings, "media_type"):               # Blender 5: video is its own media type
    r.image_settings.media_type = "VIDEO"
r.image_settings.file_format = "FFMPEG"
r.ffmpeg.format = "MPEG4"
r.ffmpeg.codec = "H264"
r.ffmpeg.constant_rate_factor = "HIGH"
r.filepath = OUT
bpy.ops.render.render(animation=True)
print(f"[enc] wrote {r.filepath} ({len(files)} frames, {len(files) / FPS:.0f} s)")
