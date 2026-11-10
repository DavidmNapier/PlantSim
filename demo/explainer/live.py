"""Live layer for the cyclone explainer: sidebar buttons, per-frame particle update and
the viewport overlay (explanation, legend, partition curves, 3D labels)."""
from __future__ import annotations

import math

import blf
import bpy
import gpu
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

from demo import config
from demo.assets import _prims as P
from demo.explainer import model as M

E = config.EXPLAINER
_parts = M.particles()
_handle = None

TEXT = {
    "NORMAL": ["Normal operation",
               "Spinning slurry throws coarse, dense hematite to the wall; it spirals",
               "down and out the apex as an umbrella spray (underflow -> belt filter).",
               "Fine slimes and most water turn into the inner vortex around the air",
               "core and leave up the vortex finder (overflow -> thickener)."],
    "ROPING": ["Roping: apex overloaded",
               "Too many solids for the apex (small apex / high feed solids). The air",
               "core collapses, the underflow leaves as a dense rope, and coarse",
               "hematite is forced up the vortex finder: product lost to tailings."],
    "PULSING": ["Pulsing: unstable feed",
                "Low or surging feed pressure. The vortex and the spray surge, the cut",
                "size swings, and slimes (clay, silica) bypass into the underflow:",
                "product Al2O3 and SiO2 spike, and the filter cake gets wetter."],
}


def _mode(pd):
    return M.auto_mode(pd.apex_mm, pd.solids, pd.pressure) if pd.auto else pd.mode


def _time(scene):
    return scene.frame_current / scene.render.fps * scene.cyclone.speed


@persistent
def on_frame(scene, *_):
    if not hasattr(scene, "cyclone") or "P_slimes" not in bpy.data.objects:
        return
    pd = scene.cyclone
    mode = _mode(pd)
    t = _time(scene)

    def d50_fn(tt):
        return M.d50(pd.apex_mm, pd.solids, pd.pressure, mode, tt)
    coords = {c[0]: [] for c in E["classes"]}
    names = [c[0] for c in E["classes"]]
    for i, part in enumerate(_parts):
        x, y, z, _ = M.position(i, part, t, mode, d50_fn)
        coords[names[part[0]]] += (x, y, z)
    for n in names:
        P.set_points(bpy.data.objects[f"P_{n}"], coords[n])
    air = bpy.data.objects["AirCore"]
    air.hide_viewport = air.hide_render = (mode == "ROPING") or not pd.show_air
    k = 1.0 + (0.8 * M.surge(t) - 0.4 if mode == "PULSING" else 0.0)
    air.scale = (k, k, 1.0)


# ------------------------------------------------------------------ overlay
WHITE, GREY = (1, 1, 1, 1), (0.75, 0.78, 0.82, 1)


def _rect(x, y, w, h, rgba):
    sh = gpu.shader.from_builtin("UNIFORM_COLOR")
    b = batch_for_shader(sh, "TRIS", {"pos": [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]},
                         indices=[(0, 1, 2), (0, 2, 3)])
    sh.uniform_float("color", rgba)
    b.draw(sh)


def _lines(pts, rgba, strip=True):
    sh = gpu.shader.from_builtin("UNIFORM_COLOR")
    b = batch_for_shader(sh, "LINE_STRIP" if strip else "LINES", {"pos": pts})
    sh.uniform_float("color", rgba)
    b.draw(sh)


def _text(x, y, s, size, rgba=WHITE):
    blf.size(0, size)
    blf.color(0, *rgba)
    blf.position(0, x, y, 0)
    blf.draw(0, s)


def _panel(region, pd, mode, t, s):
    d50 = M.d50(pd.apex_mm, pd.solids, pd.pressure, mode, t)
    lines = TEXT[mode]
    lh = int(21 * s)
    rows = len(lines) + len(E["classes"]) + 3
    w, h = int(640 * s), lh * rows + int(16 * s)
    x0, y0 = int(16 * s), region.height - h - int(80 * s)       # below the header
    gpu.state.blend_set("ALPHA")
    _rect(x0, y0, w, h, (0.05, 0.06, 0.08, 0.80))
    y = y0 + h - lh
    _text(x0 + 12 * s, y, "HYDROCYCLONE  |  how iron ore fines are classified", 17 * s)
    y -= lh
    col = (0.35, 0.85, 0.45, 1) if mode == "NORMAL" else ((1.0, 0.8, 0.2, 1) if mode == "ROPING" else (1, .35, .3, 1))
    _text(x0 + 12 * s, y, lines[0] + ("   (auto from settings)" if pd.auto else ""), 16 * s, col)
    for ln in lines[1:]:
        y -= lh
        _text(x0 + 12 * s, y, ln, 14 * s, GREY)
    y -= lh * 1.3
    _text(x0 + 12 * s, y, f"Cut size d50: silica {d50:.0f} um,  hematite {M.d50_for(5.0, d50):.0f} um   "
          f"|  water bypass {M.bypass(mode, t):.0%}", 14 * s)
    for name, label, rho, dmin, dmax, _, _, rgb in E["classes"]:
        y -= lh
        _rect(x0 + 14 * s, y - 2 * s, 14 * s, 14 * s, (*rgb, 1.0))
        mid = math.sqrt(dmin * dmax)
        p = M.partition(mid, rho, d50, mode, t)
        _text(x0 + 36 * s, y, f"{label}: {dmin:.0f}-{dmax:.0f} um  ->  {p:.0%} to underflow", 14 * s)
    y -= lh
    _text(x0 + 12 * s, y, "Underflow -> belt filter (product)     Overflow -> thickener (tailings)", 14 * s, GREY)
    gpu.state.blend_set("NONE")


def _chart(region, pd, mode, t, s):
    """Partition curves: % to underflow vs particle size (log), hematite and silica."""
    d50 = M.d50(pd.apex_mm, pd.solids, pd.pressure, mode, t)
    w, h = int(420 * s), int(230 * s)
    x0, y0 = int(16 * s), int(16 * s)
    px0, py0, pw, ph = x0 + 46 * s, y0 + 36 * s, w - 62 * s, h - 66 * s
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(2.0)
    _rect(x0, y0, w, h, (0.05, 0.06, 0.08, 0.80))
    _lines([(px0, py0 + ph), (px0, py0), (px0 + pw, py0)], GREY)
    for dec in (1, 10, 100, 1000):
        gx = px0 + pw * math.log10(dec) / 3
        _lines([(gx, py0), (gx, py0 - 4 * s)], GREY, strip=False)
        _text(gx - 8 * s, py0 - 18 * s, f"{dec}", 12 * s, GREY)
    for frac in (0.5, 1.0):
        _text(px0 - 38 * s, py0 + ph * frac - 5 * s, f"{frac:.0%}", 12 * s, GREY)
    for rho, rgb in ((5.0, (0.95, 0.35, 0.25)), (2.65, (0.95, 0.90, 0.75))):
        pts = []
        for k in range(61):
            d = 10 ** (3 * k / 60)
            pts.append((px0 + pw * k / 60, py0 + ph * M.partition(d, rho, d50, mode, t)))
        _lines(pts, (*rgb, 1.0))
        gx = px0 + pw * math.log10(M.d50_for(rho, d50)) / 3
        _lines([(gx, py0), (gx, py0 + ph)], (*rgb, 0.5), strip=False)
    _text(x0 + 10 * s, y0 + h - 20 * s, "Partition curve: % to underflow vs size (um)", 13 * s)
    _text(px0 + pw - 150 * s, py0 + ph * 0.25, "hematite", 12 * s, (0.95, 0.35, 0.25, 1))
    _text(px0 + pw - 150 * s, py0 + ph * 0.10, "silica / clay", 12 * s, (0.95, 0.90, 0.75, 1))
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")


def _labels(region, rv3d, mode, s):
    C, H, Z0 = E["cone_h"], M.TOP, E["z0"]
    ii = E["inlet"]
    items = [
        ("Feed slurry (tangential inlet)", (ii["len"] + 0.6, ii["y"], Z0 + C + ii["z"] + 0.45)),
        ("Vortex finder", (E["vf_r"] + 0.1, -0.3, Z0 + H + 0.25)),
        ("Overflow: slimes + water -> thickener", (-2.8, 0.0, Z0 + H + E["vf_top"] + 0.5)),
        ("Outer vortex (down)", (-M.wall_r(C * 0.6) - 0.1, -0.2, Z0 + C * 0.6)),
        ("Inner vortex (up)", (0.25, -0.4, Z0 + C * 0.85)),
        ("Apex / spigot", (0.35, -0.2, Z0 - 0.1)),
        ("Underflow: coarse hematite -> belt filter", (1.3, -1.2, Z0 - E["spigot_h"] - 1.1)),
    ]
    items.append(("Air core collapsed (roping)" if mode == "ROPING" else "Air core", (0.15, -0.25, Z0 + C * 0.35)))
    gpu.state.blend_set("ALPHA")
    for txt, co in items:
        p = location_3d_to_region_2d(region, rv3d, co)
        if p is None:
            continue
        blf.size(0, 14 * s)
        tw = blf.dimensions(0, txt)[0]
        _rect(p.x - 4 * s, p.y - 5 * s, tw + 8 * s, 20 * s, (0.05, 0.06, 0.08, 0.6))
        _text(p.x, p.y, txt, 14 * s, (1.0, 0.85, 0.4, 1) if "collapsed" in txt else WHITE)
    gpu.state.blend_set("NONE")


def draw():
    ctx = bpy.context
    scene, region, rv3d = ctx.scene, ctx.region, ctx.region_data
    if not hasattr(scene, "cyclone") or rv3d is None:
        return
    pd = scene.cyclone
    s = ctx.preferences.system.ui_scale * 0.58
    mode, t = _mode(pd), _time(scene)
    if pd.show_labels:
        _labels(region, rv3d, mode, s)
    if pd.show_panel:
        _panel(region, pd, mode, t, s)
        _chart(region, pd, mode, t, s)


# ------------------------------------------------------------------ UI
def _refresh(self, context):
    on_frame(context.scene)


class CycloneProps(bpy.types.PropertyGroup):
    mode: EnumProperty(name="Mode", update=_refresh, items=[
        ("NORMAL", "Normal", "Stable air core, umbrella spray"),
        ("ROPING", "Roping", "Apex overloaded: rope discharge, coarse lost to overflow"),
        ("PULSING", "Pulsing", "Unstable feed: surging, slimes bypass to underflow")])
    auto: BoolProperty(name="Auto mode from settings", default=False, update=_refresh,
                       description="Pick the mode from apex size, feed solids and pressure")
    apex_mm: FloatProperty(name="Apex (mm)", default=E["apex_mm"], min=50, max=130, update=_refresh)
    solids: FloatProperty(name="Feed solids (%)", default=E["feed_solids_pct"], min=15, max=55, update=_refresh)
    pressure: FloatProperty(name="Feed pressure (kPa)", default=E["pressure_kpa"], min=40, max=200,
                            update=_refresh)
    speed: FloatProperty(name="Speed", default=1.0, min=0.1, max=3.0, update=_refresh)
    show_labels: BoolProperty(name="Labels", default=True)
    show_panel: BoolProperty(name="Explanation + chart", default=True)
    show_air: BoolProperty(name="Air core", default=True, update=_refresh)


class CYCLONE_OT_play(bpy.types.Operator):
    bl_idname = "cyclone.play"
    bl_label = "Play / Pause"

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


class CYCLONE_OT_reset(bpy.types.Operator):
    bl_idname = "cyclone.reset"
    bl_label = "Reset"
    bl_description = "Normal mode, nominal settings"

    def execute(self, context):
        pd = context.scene.cyclone
        pd.auto, pd.mode = False, "NORMAL"
        pd.apex_mm, pd.solids, pd.pressure, pd.speed = E["apex_mm"], E["feed_solids_pct"], E["pressure_kpa"], 1.0
        return {"FINISHED"}


class CYCLONE_PT_main(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Cyclone"
    bl_label = "Hydrocyclone"

    def draw(self, context):
        pd = context.scene.cyclone
        L = self.layout
        row = L.row(align=True)
        row.operator("cyclone.play", icon="PLAY")
        row.operator("cyclone.reset", icon="FILE_REFRESH")
        b = L.box()
        b.label(text="Mode", icon="FORCE_VORTEX")
        r = b.row()
        r.enabled = not pd.auto
        r.prop(pd, "mode", expand=True)
        b.prop(pd, "auto")
        b = L.box()
        b.label(text="Operating settings", icon="SETTINGS")
        for p in ("apex_mm", "solids", "pressure"):
            b.prop(pd, p)
        if pd.auto:
            b.label(text=f"Underflow load {M.load_ratio(pd.apex_mm, pd.solids):.2f}x "
                         f"(ropes above {E['rope_load']:.2f}x)")
        b = L.box()
        b.label(text="View", icon="HIDE_OFF")
        b.prop(pd, "speed")
        col = b.column(align=True)
        for p in ("show_labels", "show_panel", "show_air"):
            col.prop(pd, p)


CLASSES = (CycloneProps, CYCLONE_OT_play, CYCLONE_OT_reset, CYCLONE_PT_main)


def register():
    global _handle
    unregister()
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.cyclone = PointerProperty(type=CycloneProps)
    bpy.app.handlers.frame_change_post.append(on_frame)
    if not bpy.app.background:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw, (), "WINDOW", "POST_PIXEL")
        bpy.app.timers.register(_setup_view, first_interval=0.5)


def unregister():
    global _handle
    for f in [f for f in bpy.app.handlers.frame_change_post if getattr(f, "__module__", "") == __name__]:
        bpy.app.handlers.frame_change_post.remove(f)
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None
    if hasattr(bpy.types.Scene, "cyclone"):
        del bpy.types.Scene.cyclone
    for c in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass


def _setup_view():
    """GUI only: EEVEE shading, camera view filling the viewport, sidebar on the Cyclone tab."""
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != "VIEW_3D":
                continue
            sp = area.spaces[0]
            sp.shading.type = "RENDERED"
            sp.region_3d.view_perspective = "CAMERA"
            for region in area.regions:
                if region.type == "UI":
                    try:
                        region.active_panel_category = "Cyclone"
                    except (AttributeError, TypeError):
                        pass
                elif region.type == "WINDOW":
                    with bpy.context.temp_override(window=win, area=area, region=region):
                        bpy.ops.view3d.view_center_camera()
            area.tag_redraw()
    on_frame(bpy.context.scene)
    return None


BOOT = '''# Registers the hydrocyclone explainer (sidebar, overlay, particles). Runs on file load.
import sys
ROOT = r"{root}"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from demo.explainer import live
live.register()
'''


def install_boot_text(root):
    t = bpy.data.texts.get("cyclone_boot.py") or bpy.data.texts.new("cyclone_boot.py")
    t.from_string(BOOT.format(root=root))
    t.use_module = True
