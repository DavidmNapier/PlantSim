"""Rebuild the whole demo scene from scratch.

    blender -b -P build.py -- [--check] [--no-save]

--check   render 640x360 stills of each camera bookmark to renders/
"""
import argparse
import importlib
import os
import sys
import time

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Fresh import of the demo package each run (matters when run from an open Blender).
for name in [m for m in sys.modules if m == "demo" or m.startswith("demo.")]:
    del sys.modules[name]

from demo import config  # noqa: E402
from demo.sim import wetplant  # noqa: E402

BLEND_OUT = os.path.join(ROOT, "build", "plant_demo.blend")
RENDER_DIR = os.path.join(ROOT, "renders")

from demo import runtime  # noqa: E402
from demo.story import cameras as story_cams  # noqa: E402
from demo.story import chapters  # noqa: E402
from demo.assets import (_prims, belt, beltfilter, bwr, conveyors, crusher, cyclone, haultruck,  # noqa: E402
                         loadout, pile, scales, scrubber, screen, site, stacker, towers)
from demo.viz import segments  # noqa: E402


def _hero_view():
    import math
    hx, hy = cyclone.centre(config.CYCLONE["hero"])
    a = math.atan2(hy, hx) - 0.15
    return ((hx + 5.2 * math.cos(a), hy + 5.2 * math.sin(a), 5.0), (hx, hy, 4.3))


def _frame_at(minute):
    return int(minute / config.PLAYBACK["sim_min_per_s"] * 24) + 1


# Check stills: name -> (camera loc, target, live events [(minute, hero condition)], frame).
# Later replaced by demo/story/ camera bookmarks.
CHECK_VIEWS = {
    "overview": ((30.0, -28.0, 20.0), (9.0, 0.0, 2.5), [(0, "NORMAL")], 30),
    "cluster": ((7.5, -7.5, 7.5), (0.0, 0.0, 4.0), [(0, "NORMAL")], 30),
    "hero_normal": (*_hero_view(), [(0, "NORMAL")], 30),
    "hero_roping": (*_hero_view(), [(0, "ROPING")], 30),
    "hero_pulsing": (*_hero_view(), [(0, "PULSING")], 30),
    # pulsing starts at minute 6: at minute 9 the first ~6 m of belt is off-spec, then green
    "ch3_pulsing": (*config.CAM_CH3, [(0, "NORMAL"), (6, "PULSING")], _frame_at(9)),
    # yard views use the scripted fault schedule (events None)
    "ch4_stacking": ((40.0, -75.0, 30.0), (85.0, 0.0, 5.0), None, _frame_at(66)),
    "ch4_pile": ((40.0, -75.0, 30.0), (85.0, 0.0, 5.0), None, _frame_at(121)),
    "pile_end": ((20.0, -22.0, 14.0), (42.0, 0.0, 6.0), None, _frame_at(121)),
    # BWR mid-reclaim (slice ~12 of 40, where the pulsing band is exposed)
    "ch5_reclaim": ((25.0, 55.0, 32.0), (58.0, 5.0, 4.0), None, _frame_at(135.5)),
    "ch5_face": ((35.0, -30.0, 16.0), (60.0, 0.0, 5.0), None, _frame_at(135.5)),
    # bench-by-bench digging: top bench mid-slew, second bench, a later slice
    "ch5_dig1": ((2.6, -15.7, 43.4), (44.3, -9.0, 12.9), None, _frame_at(125.15)),
    "ch5_dig2": ((3.5, -15.2, 42.5), (44.8, -9.0, 12.6), None, _frame_at(125.45)),
    "ch5_dig3": ((4.4, -14.8, 41.6), (45.3, -9.0, 12.4), None, _frame_at(125.75)),
    "ch5_dig4": ((48.0, 35.0, 20.0), (44.0, 2.0, 4.0), None, _frame_at(125.6)),
    "ch6_loadout": ((150.0, 25.0, 22.0), (170.0, 60.0, 4.0), None, _frame_at(140.0)),
    "ch6_train": ((165.0, 30.0, 26.0), (95.0, 60.0, 2.0), None, _frame_at(160.0)),
    "up_overview": ((-150.0, -70.0, 45.0), (-80.0, 0.0, 3.0), None, _frame_at(20)),
    "up_scrub_screen": ((-38.0, -24.0, 13.0), (-58.0, 0.0, 4.0), None, _frame_at(20)),
    "up_crusher": ((-100.0, -38.0, 26.0), (-130.0, 0.0, 6.0), None, _frame_at(20)),
    "site_overview": ((-60.0, -190.0, 120.0), (40.0, 0.0, 0.0), None, _frame_at(66)),
    "links_wet": ((-25.0, -40.0, 22.0), (-10.0, -5.0, 2.0), None, _frame_at(66)),
    # close-ups of the detailed equipment and infrastructure
    "detail_cyclones": ((7.0, -7.5, 6.5), (0.5, 0.0, 4.2), [(0, "NORMAL")], 30),
    "detail_filter": ((15.0, -9.0, 7.5), (10.0, 0.0, 3.5), None, _frame_at(66)),
    "detail_bwr": ((140.0, 4.0, 22.0), (165.0, 26.0, 8.0), None, _frame_at(66)),
    "detail_stacker": ((60.0, -50.0, 18.0), (70.0, -24.0, 8.0), None, _frame_at(5)),
    "detail_train": ((158.0, 74.0, 7.0), (172.0, 60.0, 3.0), None, _frame_at(150)),
    "detail_loco": ((135.0, 48.0, 6.0), (150.0, 60.0, 2.5), None, _frame_at(126)),
    "detail_crusher": ((-105.0, -32.0, 22.0), (-132.0, 0.0, 8.0), None, _frame_at(20)),
    "detail_rom": ((-165.0, -30.0, 22.0), (-145.0, 0.0, 8.0), None, _frame_at(20)),
    "detail_towers": ((45.0, -18.0, 12.0), (32.5, -12.0, 4.0), None, _frame_at(66)),
    "detail_sheds": ((-5.0, -95.0, 22.0), (0.0, -62.0, 4.0), None, _frame_at(66)),
}


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--only", default="", help="render only check views whose name starts with this")
    return ap.parse_args(argv)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24
    scene.view_settings.view_transform = "Standard"
    ee = getattr(scene, "eevee", None)
    if ee is not None:   # live-viewport budget: low shadows, few samples, no ray tracing
        for attr, val in (("taa_samples", 8), ("shadow_resolution_scale", 0.5),
                          ("use_shadow_jitter_viewport", False), ("use_raytracing", False),
                          ("shadow_ray_count", 1), ("shadow_step_count", 4)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    return scene


def build_world(scene):
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.62, 0.72, 0.85, 1.0)
    bg.inputs["Strength"].default_value = 0.8
    scene.world = world

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.8, 0.2, 0.6)
    scene.collection.objects.link(sun)

    bpy.ops.mesh.primitive_plane_add(size=1000.0, location=(100.0, 0.0, 0.0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    mat = bpy.data.materials.new("Ground")
    mat.diffuse_color = (0.45, 0.28, 0.18, 1.0)   # pilbara red dirt
    if mat.node_tree:
        mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mat.diffuse_color
    ground.data.materials.append(mat)


def add_camera(scene, name, loc, target, lens=28.0):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    cam.data.lens = lens
    cam.location = loc
    scene.collection.objects.link(cam)
    aim = bpy.data.objects.new(name + "_target", None)
    aim.location = target
    scene.collection.objects.link(aim)
    con = cam.constraints.new("TRACK_TO")
    con.target = aim
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    return cam


def build_assets(scene):
    """Each phase adds asset modules here (demo/assets/*)."""
    _prims.reset()
    cyclone.build(scene)
    belt.build(scene)
    pile.build(scene)
    stacker.build(scene)
    bwr.build(scene)
    loadout.build(scene)
    crusher.build(scene)
    haultruck.build(scene)
    scrubber.build(scene)
    screen.build(scene)
    scales.build(scene)
    conveyors.build(scene)
    beltfilter.build(scene)
    site.build(scene)
    towers.build(scene)
    segments.build(scene)


KEEP_SEPARATE = ("Pile", "PileCut", "Bin_GaugeLevel", "Ground")


def merge_static():
    """Join static mesh objects per collection into one mesh (far fewer draw calls).
    Skips anything animated or looked up by name: parented/parent objects, GN point
    clouds, LEDs, wagon templates, the pile and the bin gauge."""
    before = len(bpy.data.objects)
    for col in list(bpy.data.collections):
        objs = [o for o in col.objects if o.type == "MESH" and o.parent is None and not o.children
                and o.name not in KEEP_SEPARATE and not o.name.startswith("tmpl_")
                and not o.name.endswith("_Led") and not o.hide_viewport
                and not any(m.type == "NODES" for m in o.modifiers)]
        if len(objs) < 2:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.convert(target="MESH")          # applies bevels
        bpy.ops.object.join()
        bpy.context.view_layer.objects.active.name = f"{col.name}_static"
    print(f"[build] merged static meshes: {before} -> {len(bpy.data.objects)} objects")
    for col_name in NO_SHADOW:                 # see-through grating decks: no shadow
        o = bpy.data.objects.get(f"{col_name}_static")
        if o is not None:
            o.visible_shadow = False


NO_SHADOW = ("CycloneDeck",)


def report_tris():
    """Triangles per collection (linked duplicates counted once per object)."""
    per, total = {}, 0
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.hide_viewport:
            continue
        me = o.data
        n = sum(len(p.vertices) - 2 for p in me.polygons)
        c = o.users_collection[0].name if o.users_collection else "-"
        per[c] = per.get(c, 0) + n
        total += n
    top = sorted(per.items(), key=lambda kv: -kv[1])[:12]
    print(f"[build] triangles {total:,}: " + ", ".join(f"{k} {v:,}" for k, v in top))
    return total


def setup_viewports():
    """Saved file opens looking through the presenter camera, EEVEE material preview
    lit by the scene, sidebar open."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            sp = area.spaces[0]
            sp.shading.type = "RENDERED"         # measured faster than MATERIAL on Arc 140V
            sp.shading.use_scene_lights = True
            sp.shading.use_scene_world = True
            sp.show_region_ui = True
            sp.show_region_toolbar = False      # exec-clean view: no tools, gizmos, info text
            sp.show_gizmo_navigate = False
            sp.overlay.show_text = False
            sp.overlay.show_cursor = False             # no 3D cursor, grid or empties on screen
            sp.overlay.show_floor = False
            sp.overlay.show_axis_x = sp.overlay.show_axis_y = False
            sp.overlay.show_outline_selected = False
            sp.overlay.show_relationship_lines = False
            sp.overlay.show_object_origins = False
            sp.show_object_viewport_empty = False
            sp.show_object_viewport_camera = False      # no camera wireframes in the exec view
            sp.region_3d.view_perspective = "CAMERA"
    for o in bpy.context.scene.objects:
        o.select_set(False)


def render_checks(scene):
    os.makedirs(RENDER_DIR, exist_ok=True)
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 640, 360, 100
    r.image_settings.file_format = "PNG"
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 16
    hero = config.CYCLONE["hero"]
    only = ARGS.only
    bound = [(mk, mk.camera) for mk in scene.timeline_markers]
    for mk, _ in bound:            # markers would switch the camera at render time
        mk.camera = None
    for name, (loc, target, events, frame) in CHECK_VIEWS.items():
        if only and not name.startswith(only):
            continue
        runtime.STATE["mute"] = True
        scene.plantdemo.use_schedule = events is None
        scene.plantdemo.story = False          # these views use continuous sim time
        runtime.STATE["mute"] = False
        runtime.STATE["events"] = [(m, hero, {"condition": c}) for m, c in events or []]
        runtime.recompute(scene)
        scene.frame_set(frame)
        runtime.on_frame(scene)
        scene.camera = add_camera(scene, f"check_{name}", loc, target)
        r.filepath = os.path.join(RENDER_DIR, f"check_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[check] wrote {r.filepath}")

    for mk, cam in bound:
        mk.camera = cam

    # storyline: each chapter camera at 60% through its chapter, scripted fault, no live events
    runtime.STATE["mute"] = True
    scene.plantdemo.story = scene.plantdemo.use_schedule = True
    runtime.STATE["mute"] = False
    runtime.STATE["events"] = []
    runtime.recompute(scene)
    for i, _, f0, f1, *_ in chapters.chapters():
        name = f"story_ch{i}"
        if only and not name.startswith(only):
            continue
        scene.frame_set(int(f0 + 0.6 * (f1 - f0)))
        runtime.on_frame(scene)
        scene.camera = bpy.data.objects[f"Cam_Ch{i}"]
        r.filepath = os.path.join(RENDER_DIR, f"check_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[check] wrote {r.filepath}")


def main():
    global ARGS
    a = ARGS = args()
    t0 = time.time()
    recs = wetplant.run()
    alerts = sum(1 for r in recs if r.alerts)
    print(f"[sim] {len(recs)} parcels, {alerts} with alerts, "
          f"product {sum(r.product.dry_t for r in recs):.0f} dry t")

    scene = reset_scene()
    build_world(scene)
    build_assets(scene)
    add_camera(scene, "Cam_Overview", *CHECK_VIEWS["overview"][:2])
    story_cams.build(scene)
    scene.frame_start = 1
    scene.frame_end = chapters.total_frames()

    merge_static()
    report_tris()
    runtime.register()
    runtime.install_boot_text(ROOT)
    runtime.STATE["events"].clear()
    runtime.recompute(scene)
    scene.frame_set(1)
    setup_viewports()

    if not a.no_save:
        os.makedirs(os.path.dirname(BLEND_OUT), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
        print(f"[build] saved {BLEND_OUT}")
    if a.check:
        render_checks(scene)
    print(f"[build] done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
