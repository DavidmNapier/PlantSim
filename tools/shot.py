"""GUI screenshot check of the live viewport (sidebar + KPI overlay).

    blender -y build/plant_demo.blend -P tools/shot.py -- renders/ui_check.png [condition] [minute]

Opens the demo, applies the condition to the hero cyclone at minute 0, jumps to
`minute`, screenshots the window and quits.
"""
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "renders/ui_check.png"
COND = argv[1] if len(argv) > 1 else "PULSING"
MINUTE = float(argv[2]) if len(argv) > 2 else 9.0
CAM = [tuple(map(float, a.split(","))) for a in argv[3:5]] if len(argv) > 4 else None  # loc, target


def setup():
    from demo import config, runtime
    scene = bpy.context.scene
    win = bpy.context.window_manager.windows[0]
    runtime.STATE["mute"] = True
    scene.plantdemo.use_schedule = COND == "SCHEDULE" or COND.startswith("CH")
    scene.plantdemo.story = COND.startswith("CH")
    runtime.STATE["mute"] = False
    runtime.STATE["events"] = [] if COND == "SCHEDULE" or COND.startswith("CH") else [
        (0.0, config.CYCLONE["hero"], {"condition": "NORMAL"}),
        (4.0, config.CYCLONE["hero"], {"condition": COND})]
    runtime.recompute(scene)
    if CAM:
        cam = bpy.data.objects.new("ShotCam", bpy.data.cameras.new("ShotCam"))
        cam.data.lens = 28.0
        scene.collection.objects.link(cam)
        cam.location = CAM[0]
        tgt = bpy.data.objects.new("ShotCam_target", None)
        scene.collection.objects.link(tgt)
        tgt.location = CAM[1]
        con = cam.constraints.new("TRACK_TO")
        con.target, con.track_axis, con.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
        scene.camera = cam
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                region = [r for r in area.regions if r.type == "WINDOW"][0]
                with bpy.context.temp_override(window=win, area=area, region=region):
                    bpy.ops.view3d.view_center_camera()
    if COND.startswith("CH"):                     # CHn: chapter n, MINUTE = seconds into it
        with bpy.context.temp_override(window=win):
            bpy.ops.plantdemo.chapter(index=int(COND[2:]))
        scene.frame_set(scene.frame_current + int(MINUTE * scene.render.fps))
    else:
        scene.frame_set(int(MINUTE / config.PLAYBACK["sim_min_per_s"] * scene.render.fps) + 1)
    for area in win.screen.areas:
        if area.type == "VIEW_3D":
            area.tag_redraw()
    bpy.app.timers.register(shoot, first_interval=10.0)   # let EEVEE finish compiling shaders


def shoot():
    win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=bpy.path.abspath(OUT))
        print(f"[shot] wrote {OUT}")
        bpy.ops.wm.quit_blender()


bpy.app.timers.register(setup, first_interval=2.0)
