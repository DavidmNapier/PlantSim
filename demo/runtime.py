"""Live side of the demo: precompute the sim when settings change, then play it
back from the frame handler. Registered on file load by the boot text block."""
from __future__ import annotations

import bisect

import bpy
from bpy.app.handlers import persistent

from demo import config
from demo.assets import (belt, bwr, conveyors, crusher, cyclone, loadout, pile, scales, scrubber,
                         screen, stacker)
from demo.sim import stockyard, wetplant
from demo.sim.equipment import CycloneSettings
from demo.viz import colors, segments

STATE = {"records": [], "minutes": [], "cum": [], "events": [], "mute": False}


# ------------------------------------------------------------------ time + data
def frame_to_min(scene, frame=None) -> float:
    f = scene.frame_current if frame is None else frame
    if getattr(scene, "plantdemo", None) is not None and scene.plantdemo.story:
        from demo.story import chapters
        return chapters.minute_at(f)
    return max(0.0, (f - 1) / config.STORY_FPS * config.PLAYBACK["sim_min_per_s"])


def index_at(minute: float) -> int:
    return max(0, bisect.bisect_right(STATE["minutes"], minute) - 1)


def _settings_fn(use_schedule: bool):
    n = config.CYCLONE["count"]
    events = sorted(STATE["events"], key=lambda e: e[0])

    def fn(minute):
        """Scripted fault (if on) as the baseline; live presenter events override it
        for their cyclone from the minute they were made."""
        base = [CycloneSettings() for _ in range(n)]
        if use_schedule:
            base = wetplant.settings_at(minute, base, config.FAULT_SCHEDULE)
        for m, idx, kw in events:
            if m <= minute:
                base[idx] = CycloneSettings(**kw)
        return base
    return fn


def recompute(scene=None):
    scene = scene or bpy.context.scene
    pd = scene.plantdemo
    recs = wetplant.run(seed=pd.seed, settings_fn=_settings_fn(pd.use_schedule))
    STATE["records"] = recs
    STATE["minutes"] = [r.minute for r in recs]
    cum, total = [], 0.0
    for r in recs:
        total += r.product.dry_t
        cum.append(total)
    STATE["cum"] = cum
    STATE["yard"] = stockyard.run_yard(recs)
    pile.invalidate()
    segments.prepare(recs, STATE["yard"])
    on_frame(scene)


def add_event(scene):
    """Presenter changed a cyclone setting: applies from the current sim minute on."""
    pd = scene.plantdemo
    kw = dict(condition=pd.condition, apex_mm=pd.apex_mm,
              feed_solids_pct=pd.feed_solids_pct, pressure_kpa=pd.pressure_kpa)
    m = frame_to_min(scene)
    if STATE["minutes"]:               # apply from the current parcel so KPIs react at once
        m = STATE["minutes"][index_at(m)]
    STATE["events"].append((m, int(pd.cyclone), kw))
    recompute(scene)


def snapshot(scene):
    """Everything the overlay needs for the current frame."""
    if not STATE["records"]:
        return None
    m = frame_to_min(scene)
    i = index_at(m)
    rec = STATE["records"][i]
    lag = config.PLAYBACK["belt_lag_min"]
    po = config.PLAYBACK["product_off_min"]
    on_belt = [r for r in STATE["records"][max(0, i - 40):i + 1] if m - po - lag <= r.minute <= m - po]
    return {"minute": m, "rec": rec, "cum": STATE["cum"][i], "on_belt": on_belt,
            "yard": STATE.get("yard"), "records": STATE["records"]}


def bands(pd):
    """Metrics shown as stacked bands (top first)."""
    return [b for b in (pd.metric, pd.band2, pd.band3, pd.band4) if b != "NONE"] or [pd.metric]


# ------------------------------------------------------------------ frame handler
@persistent
def on_frame(scene, *_):
    if not STATE["records"] or not hasattr(scene, "plantdemo"):
        return
    pd = scene.plantdemo
    m = frame_to_min(scene)
    rec = STATE["records"][index_at(m)]
    cyclone.update(scene, rec.conditions[config.CYCLONE["hero"]], scene.frame_current)
    lag = config.PLAYBACK["belt_lag_min"]
    recs = STATE["records"]

    def colour(frac):  # lump at belt fraction `frac` left the cyclone `frac*lag` ago
        p = recs[index_at(m - frac * lag)].product
        return colors.to_linear(colors.rgba(pd.metric, colors.metric_value(p, pd.metric)))
    belt.update(scene, scene.frame_current, colour_fn=colour)
    segments.update(scene, m, bands(pd), recs, STATE.get("yard"))
    if "Scrubber_Drum" in bpy.data.objects:      # upstream plant (P3)
        ore = colors.to_linear(config.COLORS["ore"])
        crusher.update(scene, scene.frame_current, lambda f: ore)
        scrubber.update(scene, scene.frame_current)
        screen.update(scene, scene.frame_current)

    # stockyard: pile (heatmap), stacker, yard belt
    yard = STATE.get("yard")
    if yard is not None and "Pile" in bpy.data.objects:
        pile.update(scene, yard, m, bands(pd), pd.show_heatmap)
        now = colour(0.0) if m < config.SIM_MINUTES else config.COLORS["ore"]
        stacker.update(scene, m, now, scene.frame_current)
        bwr.update(scene, m, scene.frame_current)
        rec_min = [r[0] for r in yard.reclaimed]

        def reclaim_colour(frac):   # lumps on the load-out belt: cut that left the BWR earlier
            i = max(0, bisect.bisect_right(rec_min, m - frac * 2.0) - 1)
            if not yard.reclaimed or m - frac * 2.0 < rec_min[0]:
                return colors.to_linear(config.COLORS["ore"])
            p = yard.reclaimed[i][2]
            return colors.to_linear(colors.rgba(pd.metric, colors.metric_value(p, pd.metric)))
        loadout.update(scene, yard, m, pd.metric, scene.frame_current, reclaim_colour)
        if "TransferBelt_Lumps" in bpy.data.objects:
            ore = colors.to_linear(config.COLORS["ore"])
            conveyors.update(scene, scene.frame_current,
                             lambda f: colour(0.0) if m < config.SIM_MINUTES else ore,
                             lambda f: reclaim_colour(0.3 + f * 0.7), ore)
        if "TP3_Led" in bpy.data.objects:
            pos = loadout.train_state(yard, m)[0] if m >= config.STOCKPILE["reclaim_start_min"] else -1.0
            scales.update(scene, m, pos + 0.5 if pos >= 0 else -1.0)
        belt.update(scene, scene.frame_current, "YardBelt", stacker.YARD_BELT,
                    colour_fn=lambda f: colour(1.0 + f * 0.5) if m < config.SIM_MINUTES
                    else config.COLORS["ore"])


@persistent
def on_load(*_):
    scene = bpy.context.scene
    STATE["events"].clear()
    if hasattr(scene, "plantdemo"):
        recompute(scene)
    if not bpy.app.background:
        bpy.app.timers.register(_show_tab, first_interval=0.5)


def _show_tab():
    """Open the sidebar on the Plant Demo tab (best effort; API varies by version)."""
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "UI":
                        try:
                            region.active_panel_category = "Plant Demo"
                        except (AttributeError, TypeError):
                            pass
                    elif region.type == "WINDOW":   # camera frame fills the viewport
                        sh = area.spaces[0].shading     # live colours need EEVEE, not Solid
                        if sh.type != "RENDERED":
                            sh.type = "RENDERED"
                            sh.use_scene_lights_render = sh.use_scene_world_render = True
                        with bpy.context.temp_override(window=win, area=area, region=region):
                            bpy.ops.view3d.view_center_camera()
                area.tag_redraw()
    return None


# ------------------------------------------------------------------ register
def register():
    from demo.ui import panel
    from demo.viz import kpi
    unregister()
    panel.register()
    kpi.register()
    bpy.app.handlers.frame_change_post.append(on_frame)
    bpy.app.handlers.load_post.append(on_load)


def unregister():
    for h in (bpy.app.handlers.frame_change_post, bpy.app.handlers.load_post):
        for f in [f for f in h if getattr(f, "__module__", "") == __name__]:
            h.remove(f)
    try:
        from demo.ui import panel
        from demo.viz import kpi
        kpi.unregister()
        panel.unregister()
    except Exception:
        pass


BOOT = '''# Registers the live demo (sidebar, KPI overlay, playback). Runs on file load.
import sys
ROOT = r"{root}"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from demo import runtime
runtime.register()
runtime.on_load()
'''


def install_boot_text(root: str):
    t = bpy.data.texts.get("plantdemo_boot.py") or bpy.data.texts.new("plantdemo_boot.py")
    t.from_string(BOOT.format(root=root))
    t.use_module = True
