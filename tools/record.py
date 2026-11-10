"""Record a backup clip of the live viewport (KPI panel, tags and captions included)
by screenshotting the 3D view frame by frame.

    blender -y -p 0 0 1920 1080 build/plant_demo.blend -P tools/record.py -- [first_ch] [last_ch] [step] [out_dir]

Writes OUT_DIR/f_00001.png ... (default renders/clip) then quits. Encode with tools/encode.py;
tools/backup_videos.py records and encodes every chapter.
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FIRST = int(argv[0]) if argv else 3
LAST = int(argv[1]) if len(argv) > 1 else 6
STEP = int(argv[2]) if len(argv) > 2 else 2          # every 2nd frame -> 12 fps clip
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = argv[3] if len(argv) > 3 else os.path.join(ROOT, "renders", "clip")
st = {"n": 0}


def _area():
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height)
    return win, area


def setup():
    from demo.story import chapters
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    win, area = _area()
    sp = area.spaces[0]
    sp.show_region_ui = False                       # clean frame: no sidebar
    sp.show_region_header = False
    sp.overlay.show_overlays = False                # no dashed camera frame (the KPI overlay still draws)
    region = [r for r in area.regions if r.type == "WINDOW"][0]
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screen_full_area(use_hide_panels=True)
    bpy.app.timers.register(lambda: _start(), first_interval=1.0)
    return None


def _start():
    import json
    from demo.story import chapters
    win, area = _area()
    with bpy.context.temp_override(window=win):
        bpy.ops.plantdemo.chapter(index=FIRST)
    with open(os.path.join(OUT, "rect.json"), "w") as fh:     # crop box for the encoder
        json.dump({"x": area.x, "y": area.y, "w": area.width, "h": area.height,
                   "win_w": win.width, "win_h": win.height}, fh)
    chs = chapters.chapters()
    st["frames"] = list(range(chs[FIRST - 1][2], chs[LAST - 1][3] + 1, STEP))
    print(f"[rec] {len(st['frames'])} frames, chapters {FIRST}-{LAST}")
    bpy.app.timers.register(step, first_interval=6.0)   # shaders compile first
    return None


def step():
    if st["n"] >= len(st["frames"]):
        win, _ = _area()
        print("[rec] done")
        with bpy.context.temp_override(window=win):
            bpy.ops.wm.quit_blender()
        return None
    scene = bpy.context.scene
    f = st["frames"][st["n"]]
    scene.frame_set(f)
    cam = [m.camera for m in sorted(scene.timeline_markers, key=lambda m: m.frame) if m.frame <= f]
    if cam:
        scene.camera = cam[-1]
    win, area = _area()
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        bpy.ops.screen.screenshot(filepath=os.path.join(OUT, f"f_{st['n'] + 1:05d}.png"))
    st["n"] += 1
    if st["n"] % 200 == 0:
        print(f"[rec] {st['n']}/{len(st['frames'])}")
    return 0.0


bpy.app.timers.register(setup, first_interval=2.0)
