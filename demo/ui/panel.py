"""Presenter sidebar: 3D viewport > N > 'Plant Demo'."""
from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

from demo import config

C = config.CYCLONE


def _rt():
    from demo import runtime
    return runtime


def _cyc_changed(self, context):
    rt = _rt()
    if not rt.STATE["mute"]:
        rt.add_event(context.scene)


def _recompute(self, context):
    rt = _rt()
    if not rt.STATE["mute"]:
        rt.recompute(context.scene)


def _speed(self, context):
    context.scene.render.fps = max(6, int(round(config.STORY_FPS * self.speed)))


def _redraw(self, context):
    _rt().on_frame(context.scene)


def _pick_cyclone(self, context):
    """Show the chosen cyclone's current settings without logging an event."""
    rt = _rt()
    events = [e for e in rt.STATE["events"] if e[1] == int(self.cyclone)]
    kw = events[-1][2] if events else dict(condition="NORMAL", apex_mm=C["apex_mm"],
                                           feed_solids_pct=C["feed_solids_pct"],
                                           pressure_kpa=C["pressure_kpa"])
    rt.STATE["mute"] = True
    try:
        for k, v in kw.items():
            setattr(self, k, v)
    finally:
        rt.STATE["mute"] = False


BAND_ITEMS = [("NONE", "(none)", "")] + [(k, v[0], "") for k, v in config.METRICS.items()]


class PlantDemoProps(bpy.types.PropertyGroup):
    cyclone: EnumProperty(name="Cyclone", update=_pick_cyclone, default=str(C["hero"]),
                          items=[(str(i), f"C{i + 1}", "") for i in range(C["count"])])
    condition: EnumProperty(name="Condition", update=_cyc_changed, items=[
        ("NORMAL", "Normal", "Spray underflow, clean split"),
        ("ROPING", "Roping", "Apex overloaded, product lost to overflow"),
        ("PULSING", "Pulsing", "Unstable feed, slimes bypass into product")])
    apex_mm: FloatProperty(name="Apex (mm)", default=C["apex_mm"], min=60, max=120,
                           update=_cyc_changed)
    feed_solids_pct: FloatProperty(name="Feed solids (%)", default=C["feed_solids_pct"],
                                   min=20, max=50, update=_cyc_changed)
    pressure_kpa: FloatProperty(name="Feed pressure (kPa)", default=C["pressure_kpa"],
                                min=60, max=200, update=_cyc_changed)
    use_schedule: BoolProperty(name="Scripted fault (storyline)", default=True,
                               update=_recompute)
    metric: EnumProperty(name="Band 1 (top)", default="Fe", update=_redraw,
                         items=[(k, v[0], "") for k, v in config.METRICS.items()],
                         description="Top band; also used for tags, pile ends and the stacker stream")
    band2: EnumProperty(name="Band 2", default="Al2O3", update=_redraw, items=BAND_ITEMS)
    band3: EnumProperty(name="Band 3", default="SiO2", update=_redraw, items=BAND_ITEMS)
    band4: EnumProperty(name="Band 4", default="moisture", update=_redraw, items=BAND_ITEMS)
    show_kpi: BoolProperty(name="KPI panel", default=True)
    show_tags: BoolProperty(name="Parcel tags", default=True)
    show_labels: BoolProperty(name="Labels", default=True)
    show_heatmap: BoolProperty(name="Pile heatmap", default=True, update=_redraw)
    seed: IntProperty(name="Random seed", default=config.SEED, min=0, update=_recompute)
    story: BoolProperty(name="Story timeline", default=True, update=_recompute,
                        description="Timeline plays the 7 chapters; off = continuous sim time")
    speed: FloatProperty(name="Speed", default=1.0, min=0.25, max=4.0, update=_speed,
                         description="Playback speed multiplier")


class PLANTDEMO_OT_reset(bpy.types.Operator):
    bl_idname = "plantdemo.reset"
    bl_label = "Reset scenario"
    bl_description = "Clear live changes, all cyclones normal, back to start"

    def execute(self, context):
        rt = _rt()
        pd = context.scene.plantdemo
        rt.STATE["events"].clear()
        rt.STATE["mute"] = True
        try:
            pd.condition, pd.apex_mm = "NORMAL", C["apex_mm"]
            pd.feed_solids_pct, pd.pressure_kpa = C["feed_solids_pct"], C["pressure_kpa"]
        finally:
            rt.STATE["mute"] = False
        context.scene.frame_set(context.scene.frame_start)
        rt.recompute(context.scene)
        return {"FINISHED"}


class PLANTDEMO_OT_chapter(bpy.types.Operator):
    bl_idname = "plantdemo.chapter"
    bl_label = "Chapter"
    bl_description = "Jump camera and timeline to this chapter"
    index: IntProperty(default=1, min=1, max=7)

    def execute(self, context):
        from demo.story import chapters
        scene = context.scene
        pd = scene.plantdemo
        rt = _rt()
        if not pd.story or not pd.use_schedule:
            rt.STATE["mute"] = True
            pd.story = pd.use_schedule = True
            rt.STATE["mute"] = False
            rt.recompute(scene)
        ch = chapters.chapters()[self.index - 1]
        scene.frame_set(ch[2])
        scene.camera = bpy.data.objects.get(f"Cam_Ch{self.index}", scene.camera)
        for area in context.screen.areas:              # look through the chapter camera
            if area.type == "VIEW_3D":
                area.spaces[0].region_3d.view_perspective = "CAMERA"
                region = [r for r in area.regions if r.type == "WINDOW"][0]
                with context.temp_override(area=area, region=region):
                    bpy.ops.view3d.view_center_camera()
        return {"FINISHED"}


class PLANTDEMO_OT_play(bpy.types.Operator):
    bl_idname = "plantdemo.play"
    bl_label = "Play / Pause"

    def execute(self, context):
        bpy.ops.screen.animation_play()
        return {"FINISHED"}


class PLANTDEMO_OT_present(bpy.types.Operator):
    bl_idname = "plantdemo.present"
    bl_label = "Present"
    bl_description = "Toggle full-screen 3D view through the presenter camera (sidebar kept)"

    def execute(self, context):
        bpy.ops.screen.screen_full_area(use_hide_panels=False)
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                region = [r for r in area.regions if r.type == "WINDOW"][0]
                with context.temp_override(area=area, region=region):
                    area.spaces[0].region_3d.view_perspective = "CAMERA"
                    bpy.ops.view3d.view_center_camera()
        return {"FINISHED"}


class PLANTDEMO_PT_main(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Plant Demo"
    bl_label = "Plant Demo"

    def draw(self, context):
        pd = context.scene.plantdemo
        L = self.layout
        row = L.row(align=True)
        row.operator("plantdemo.play", icon="PLAY")
        row.operator("plantdemo.reset", icon="FILE_REFRESH", text="Reset")
        L.operator("plantdemo.present", icon="FULLSCREEN_ENTER")

        b = L.box()
        b.label(text="Story", icon="SEQUENCE")
        row = b.row(align=True)
        for i in range(1, 8):
            row.operator("plantdemo.chapter", text=str(i)).index = i
        row = b.row(align=True)
        row.prop(pd, "story")
        row.prop(pd, "speed")

        b = L.box()
        b.label(text="Cyclone", icon="FORCE_VORTEX")
        b.row().prop(pd, "cyclone", expand=True)
        b.row().prop(pd, "condition", expand=True)
        b.prop(pd, "apex_mm")
        b.prop(pd, "feed_solids_pct")
        b.prop(pd, "pressure_kpa")
        b.prop(pd, "use_schedule")

        b = L.box()
        b.label(text="Metric bands (segment height = tonnes)", icon="COLOR")
        col = b.column(align=True)
        for p in ("metric", "band2", "band3", "band4"):
            col.prop(pd, p)

        b = L.box()
        b.label(text="Display", icon="HIDE_OFF")
        col = b.column(align=True)
        for p in ("show_kpi", "show_tags", "show_labels", "show_heatmap"):
            col.prop(pd, p)

        b = L.box()
        b.label(text="Scenario", icon="SETTINGS")
        b.prop(pd, "seed")


CLASSES = (PlantDemoProps, PLANTDEMO_OT_reset, PLANTDEMO_OT_play, PLANTDEMO_OT_present, PLANTDEMO_OT_chapter,
           PLANTDEMO_PT_main)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.plantdemo = PointerProperty(type=PlantDemoProps)


def unregister():
    if hasattr(bpy.types.Scene, "plantdemo"):
        del bpy.types.Scene.plantdemo
    for c in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass
