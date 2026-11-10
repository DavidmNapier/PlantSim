"""Automated dry run of the presenter flow in the live GUI.

    blender -y -p 0 0 1920 1080 build/plant_demo.blend -P tools/dryrun.py -- [secs per chapter]

For each chapter: press its chapter button, play for N seconds at normal speed,
record fps, and screenshot. In chapter 3 it switches C3 to PULSING mid-play (as the
presenter would) and checks that an alert fires and the wagons downstream change.
Writes renders/dryrun.txt and renders/dryrun_chN.png, then quits.
"""
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SECS = float(argv[0]) if argv else 6.0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders")
log, st = [], {"ch": 0, "frames": 0, "t0": 0.0}


def _win():
    win = bpy.context.window_manager.windows[0]
    area = [a for a in win.screen.areas if a.type == "VIEW_3D"][0]
    region = [r for r in area.regions if r.type == "WINDOW"][0]
    return win, area, region


def _count(scene, *_):
    st["frames"] += 1


def _ctx():
    win, area, region = _win()
    return bpy.context.temp_override(window=win, area=area, region=region)


def next_chapter():
    st["ch"] += 1
    if st["ch"] > 7:
        return finish()
    with _ctx():
        bpy.ops.plantdemo.chapter(index=st["ch"])
        bpy.ops.screen.animation_play()
    st.update(frames=0, t0=time.perf_counter(), f0=bpy.context.scene.frame_current)
    if st["ch"] == 3:
        bpy.app.timers.register(live_tweak, first_interval=SECS / 2)
    bpy.app.timers.register(stop_chapter, first_interval=SECS)
    return None


def live_tweak():
    from demo import runtime
    scene = bpy.context.scene
    yard_before = sum(w.flagged for w in runtime.STATE["yard"].wagons)
    scene.plantdemo.cyclone = "2"
    scene.plantdemo.condition = "PULSING"           # what the presenter clicks
    snap = runtime.snapshot(scene)
    alerts = snap["rec"].alerts if snap else []
    yard_after = sum(w.flagged for w in runtime.STATE["yard"].wagons)
    log.append(f"ch3 live tweak at {snap['minute']:.1f} min: alerts={len(alerts)} "
               f"({alerts[0] if alerts else 'none'}); flagged wagons {yard_before} -> {yard_after}")
    print("[dry]", log[-1])
    bpy.app.timers.register(_back_to_normal, first_interval=1.0)
    return None


def _back_to_normal():
    bpy.context.scene.plantdemo.condition = "NORMAL"     # presenter sets it back
    return None


def stop_chapter():
    with _ctx():
        bpy.ops.screen.animation_cancel(restore_frame=False)
    dt = time.perf_counter() - st["t0"]
    scene = bpy.context.scene
    from demo.story import chapters
    ch = chapters.chapter_at(scene.frame_current)
    log.append(f"ch{st['ch']}: {st['frames'] / dt:5.1f} fps, frames {st['f0']}->{scene.frame_current} "
               f"(still in ch{ch[0]}), camera {scene.camera.name}")
    print("[dry]", log[-1])
    bpy.app.timers.register(shoot, first_interval=1.0)
    return None


def shoot():
    win, *_ = _win()
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=os.path.join(OUT, f"dryrun_ch{st['ch']}.png"))
    bpy.app.timers.register(next_chapter, first_interval=0.5)
    return None


def finish():
    if st["ch"] == 8:
        with _ctx():
            bpy.ops.plantdemo.reset()
        log.append(f"reset: frame {bpy.context.scene.frame_current}, events "
                   f"{len(__import__('demo.runtime', fromlist=['x']).STATE['events'])}")
    with open(os.path.join(OUT, "dryrun.txt"), "w") as f:
        f.write("\n".join(log) + "\n")
    win, *_ = _win()
    with bpy.context.temp_override(window=win):
        bpy.ops.wm.quit_blender()
    return None


def setup():
    bpy.app.handlers.frame_change_post.append(_count)
    bpy.app.timers.register(next_chapter, first_interval=6.0)    # let shaders compile
    return None


bpy.app.timers.register(setup, first_interval=2.0)
