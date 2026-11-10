"""Perf gate: play the demo flat out in the live viewport and report fps.

    blender -y build/plant_demo.blend -P tools/perf.py -- [seconds] [WxH]

Runs each shading mode for `seconds` with frame dropping off (every frame drawn),
prints fps and the Python handler cost, writes renders/perf.txt, then quits.
"""
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SECS = float(argv[0]) if argv else 8.0
START_MIN = float(argv[1]) if len(argv) > 1 else 0.0          # sim minute to start playback at
CAM = [tuple(map(float, a.split(","))) for a in argv[2:4]] if len(argv) > 3 else None
MODES = ["MATERIAL", "RENDERED", "SOLID"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
results = []
stats = {"frames": 0, "t0": 0.0, "py": 0.0}


def _view():
    win = bpy.context.window_manager.windows[0]
    for area in win.screen.areas:
        if area.type == "VIEW_3D":
            region = [r for r in area.regions if r.type == "WINDOW"][0]
            return win, area, region
    raise RuntimeError("no 3D view")


def _count(scene, *_):
    stats["frames"] += 1


def _timed_on_frame():
    """Measure the Python per-frame cost of the playback handler alone."""
    from demo import runtime
    scene = bpy.context.scene
    t = time.perf_counter()
    for f in range(1, 121):
        scene.frame_current = f
        runtime.on_frame(scene)
    return (time.perf_counter() - t) / 120 * 1000


def start_mode():
    if not MODES:
        return finish()
    mode = MODES.pop(0)
    win, area, region = _view()
    area.spaces[0].shading.type = mode
    scene = bpy.context.scene
    scene.sync_mode = "NONE"
    scene.render.fps = 240          # uncapped: measures headroom, not presenter speed
    scene.frame_set(int(START_MIN / 2.0 * 24) + 1)
    stats.update(frames=0, t0=time.perf_counter(), mode=mode, size=(region.width, region.height))
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.animation_play()
    bpy.app.timers.register(stop_mode, first_interval=SECS)
    return None


def stop_mode():
    win, area, region = _view()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.animation_cancel(restore_frame=False)
    dt = time.perf_counter() - stats["t0"]
    fps = stats["frames"] / dt
    line = f"{stats['mode']:9s} {fps:6.1f} fps  viewport {stats['size'][0]}x{stats['size'][1]}"
    print("[perf]", line)
    results.append(line)
    bpy.app.timers.register(start_mode, first_interval=1.0)
    return None


def finish():
    ms = _timed_on_frame()
    results.append(f"python on_frame {ms:.2f} ms/frame")
    print("[perf]", results[-1])
    with open(os.path.join(ROOT, "renders", "perf.txt"), "w") as f:
        f.write("\n".join(results) + "\n")
    win, *_ = _view()
    with bpy.context.temp_override(window=win):
        bpy.ops.wm.quit_blender()
    return None


def setup():
    bpy.app.handlers.frame_change_post.append(_count)
    win, area, region = _view()
    scene = bpy.context.scene
    from demo import runtime
    runtime.STATE["mute"] = True
    scene.plantdemo.use_schedule = True
    runtime.STATE["mute"] = False
    runtime.recompute(scene)
    if CAM:
        cam = bpy.data.objects.new("PerfCam", bpy.data.cameras.new("PerfCam"))
        cam.data.lens = 28.0
        scene.collection.objects.link(cam)
        cam.location = CAM[0]
        tgt = bpy.data.objects.new("PerfCam_target", None)
        scene.collection.objects.link(tgt)
        tgt.location = CAM[1]
        con = cam.constraints.new("TRACK_TO")
        con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
        scene.camera = cam
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_center_camera()
    bpy.app.timers.register(start_mode, first_interval=2.0)
    return None


bpy.app.timers.register(setup, first_interval=3.0)
