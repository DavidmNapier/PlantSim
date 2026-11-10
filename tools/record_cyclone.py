"""Record the standalone hydrocyclone explainer as a backup clip: the live viewport with
its explanation panel, partition chart and labels, stepping through the modes.

    blender -y -p 0 0 1920 1080 build/cyclone_explainer.blend -P tools/record_cyclone.py -- OUT_DIR

Writes OUT_DIR/f_00001.png ... and rect.json (crop box) then quits. Encode with
tools/encode.py; tools/backup_videos.py cyclone does both. The mode schedule is
config.EXPLAINER_VIDEO.
"""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = argv[0] if argv else os.path.join(ROOT, "renders", "backup", "frames")
st = {"n": 0}


def _area():
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height)
    return win, area


def setup():
    from demo import config
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    win, area = _area()
    sp = area.spaces[0]
    sp.show_region_ui = False                       # clean frame: no sidebar or header
    sp.show_region_header = False
    sp.overlay.show_overlays = False                # no camera frame (our panel/chart/labels still draw)
    region = [r for r in area.regions if r.type == "WINDOW"][0]
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screen_full_area(use_hide_panels=True)
    sched = config.EXPLAINER_VIDEO
    fps = bpy.context.scene.render.fps
    st["frames"] = [(f, mode) for secs0, secs1, mode in sched for f in range(int(secs0 * fps) + 1, int(secs1 * fps) + 1)]
    bpy.app.timers.register(_fit, first_interval=1.0)
    return None


def _fit():
    win, area = _area()
    area.spaces[0].region_3d.view_perspective = "CAMERA"
    region = [r for r in area.regions if r.type == "WINDOW"][0]
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_center_camera()
    with open(os.path.join(OUT, "rect.json"), "w") as fh:
        json.dump({"x": area.x, "y": area.y, "w": area.width, "h": area.height,
                   "win_w": win.width, "win_h": win.height}, fh)
    print(f"[rec] {len(st['frames'])} frames")
    bpy.app.timers.register(step, first_interval=6.0)     # shaders compile first
    return None


def step():
    if st["n"] >= len(st["frames"]):
        win, _ = _area()
        print("[rec] done")
        with bpy.context.temp_override(window=win):
            bpy.ops.wm.quit_blender()
        return None
    scene = bpy.context.scene
    f, mode = st["frames"][st["n"]]
    pd = scene.cyclone
    if pd.auto or pd.mode != mode:
        pd.auto, pd.mode = False, mode
    scene.frame_set(f)
    win, _ = _area()
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        bpy.ops.screen.screenshot(filepath=os.path.join(OUT, f"f_{st['n'] + 1:05d}.png"))
    st["n"] += 1
    return 0.0


bpy.app.timers.register(setup, first_interval=2.0)
