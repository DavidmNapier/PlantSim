import sys, bpy
argv = sys.argv[sys.argv.index("--") + 1:]
OUT, MODE = argv[0], argv[1]
def setup():
    sc = bpy.context.scene
    sc.cyclone.mode = MODE
    sc.frame_set(120)
    bpy.app.timers.register(shoot, first_interval=8.0)
def shoot():
    win = bpy.context.window_manager.windows[0]
    with bpy.context.temp_override(window=win, screen=win.screen):
        bpy.ops.screen.screenshot(filepath=OUT)
        bpy.ops.wm.quit_blender()
bpy.app.timers.register(setup, first_interval=2.0)
