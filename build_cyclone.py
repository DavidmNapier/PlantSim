"""Build the standalone hydrocyclone explainer.

    blender -b -P build_cyclone.py -- [--check]

Writes build/cyclone_explainer.blend (open with run_cyclone.bat). --check renders a
640x360 still per mode to renders/cyc_<mode>.png.
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
    del sys.modules[name]

from demo.assets import _prims  # noqa: E402
from demo.explainer import live, scene as xscene  # noqa: E402

OUT = os.path.join(ROOT, "build", "cyclone_explainer.blend")


def main():
    check = "--check" in sys.argv
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, 24 * 120
    sc.view_settings.view_transform = "Standard"
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = engine
            break
        except TypeError:
            continue
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_samples", 8), ("shadow_resolution_scale", 0.5), ("use_raytracing", False)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    _prims.reset()
    xscene.build(sc)
    live.register()
    live.install_boot_text(ROOT)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces[0]
                sp.shading.type = "RENDERED"
                sp.show_region_ui = True
                sp.show_region_toolbar = False
                sp.show_gizmo_navigate = False
                ov = sp.overlay
                ov.show_text = ov.show_cursor = ov.show_floor = False
                ov.show_axis_x = ov.show_axis_y = False
                ov.show_relationship_lines = ov.show_object_origins = False
                ov.show_outline_selected = False
                ov.show_extras = False            # no light / camera wireframes
                sp.show_object_viewport_empty = False
                sp.region_3d.view_perspective = "CAMERA"
    for o in sc.objects:
        o.select_set(False)
    sc.frame_set(1)
    live.on_frame(sc)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print(f"[cyc] saved {OUT}")
    if check:
        r = sc.render
        r.resolution_x, r.resolution_y, r.resolution_percentage = 640, 360, 100
        for mode in ("NORMAL", "ROPING", "PULSING"):
            sc.cyclone.mode = mode
            sc.frame_set(100)
            live.on_frame(sc)
            r.filepath = os.path.join(ROOT, "renders", f"cyc_{mode.lower()}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[cyc] wrote {r.filepath}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
