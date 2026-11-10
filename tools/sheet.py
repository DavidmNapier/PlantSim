"""Contact sheet of check renders (needs Pillow; plain Python, not Blender).

    py tools/sheet.py OUT.png PREFIX [COLUMNS]

Tiles renders/check_PREFIX*.png two (or COLUMNS) across with their names.
"""
import glob
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out, prefix = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 2
files = sorted(glob.glob(os.path.join(ROOT, "renders", f"check_{prefix}*.png")))
if not files:
    sys.exit(f"no renders/check_{prefix}*.png")
ims = [Image.open(f).convert("RGB") for f in files]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, h * rows))
d = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * w, (i // cols) * h
    sheet.paste(im, (x, y))
    d.text((x + 6, y + 4), os.path.basename(f)[6:-4], fill=(255, 255, 255))
sheet.save(out)
print(f"wrote {out} ({len(ims)} tiles)")
