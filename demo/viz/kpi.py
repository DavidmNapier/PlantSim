"""Viewport overlay: KPI panel, alerts, floating parcel tags and 3D labels."""
from __future__ import annotations

import time

import blf
import bpy
import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from demo import config
from demo.viz import colors

_handle = None
WHITE, GREY = (1, 1, 1, 1), (0.75, 0.78, 0.82, 1)
GOOD, BAD, WARN = (0.35, 0.85, 0.45, 1), (1.0, 0.35, 0.3, 1), (1.0, 0.8, 0.2, 1)


def _rect(x, y, w, h, rgba):
    sh = gpu.shader.from_builtin("UNIFORM_COLOR")
    b = batch_for_shader(sh, "TRIS", {"pos": [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]},
                         indices=[(0, 1, 2), (0, 2, 3)])
    sh.uniform_float("color", rgba)
    b.draw(sh)


def _text(x, y, s, size, rgba=WHITE):
    blf.size(0, size)
    blf.color(0, *rgba)
    blf.position(0, x, y, 0)
    blf.draw(0, s)
    return blf.dimensions(0, s)[0]


def _grade_ok(k, v):
    t = config.TARGETS[k]
    tol = config.ALERT_TOL.get(k, 0.5)
    return v >= t - tol if k == "Fe" else v <= t + tol


def _kpi(region, snap, s):
    rec = snap["rec"]
    p = rec.product
    lines = []                                        # list of [(text, colour), ...]
    m = snap["minute"]
    lines.append([("WET PLANT  |  LIVE MATERIAL TRACKING", WHITE),
                  (f"   {int(m // 60):02d}:{int(m % 60):02d}", GREY)])
    rate = colors.metric_value(p, "tonnes")
    feed_rate = colors.metric_value(rec.feed, "tonnes")
    lines.append([(f"Feed {feed_rate:,.0f} t/h   Product {rate:,.0f} t/h   ", WHITE),
                  (f"Yield {p.dry_t / (rec.feed.dry_t - rec.lump.dry_t):.1%}", WHITE)])
    lines.append([(f"Product today {snap['cum']:,.0f} t", WHITE)])
    row = []
    for k in ("Fe", "SiO2", "Al2O3"):
        v = p.q[k]
        row.append((f"{k} {v:.2f}% ", GOOD if _grade_ok(k, v) else BAD))
        row.append((f"(tgt {config.TARGETS[k]})   ", GREY))
    lines.append(row)
    lines.append([(f"Moisture {p.moisture:.1f}%   P80 {p.q['p80_mm']:.1f} mm", WHITE)])
    from demo import runtime
    names = " | ".join(config.METRICS[b][0] for b in runtime.bands(bpy.context.scene.plantdemo))
    lines.append([("Segments: height = tonnes, bands top->bottom: ", GREY), (names, WHITE)])
    row = [("Cyclones  ", GREY)]
    for (name, y, _), cond in zip(rec.per_cyclone, rec.conditions):
        col = GOOD if cond == "NORMAL" else (WARN if cond == "ROPING" else BAD)
        row.append((f"{name} {y:.0%}{'' if cond == 'NORMAL' else ' ' + cond}  ", col))
    lines.append(row)

    alerts = list(rec.alerts) if m < config.SIM_MINUTES else []
    yard = snap.get("yard")
    if yard is not None:
        lines_y, alert_y = _yard_lines(snap, m, yard)
        lines += lines_y
        alerts += alert_y
    lh = int(22 * s)
    w = int(560 * s)
    h = lh * (len(lines) + len(alerts)) + int(20 * s)
    x0 = int(20 * s)
    y0 = region.height - h - int(60 * s)
    gpu.state.blend_set("ALPHA")
    _rect(x0, y0, w, h, (0.05, 0.06, 0.08, 0.78))
    if alerts:
        flash = 0.55 + 0.35 * abs((time.time() % 1.0) - 0.5) * 2
        _rect(x0, y0, w, lh * len(alerts) + int(10 * s), (0.55, 0.05, 0.05, flash))
    y = y0 + h - lh
    for ln in lines:
        x = x0 + int(12 * s)
        for txt, c in ln:
            x += _text(x, y, txt, 15 * s if ln is not lines[0] else 16 * s, c)
        y -= lh
    for a in alerts:
        _text(x0 + int(12 * s), y, "ALERT  " + a, 15 * s, WHITE)
        y -= lh
    gpu.state.blend_set("NONE")


def _fault_window(w, records):
    """'C3 pulsing 62-70 min, 0.9 t' for a flagged wagon."""
    flag = config.TRAIN["flag_conditions"]
    tr = [(mm, t, b) for mm, t, b in w.trace(records) if any(x.split(":")[1] in flag for x in b)]
    if not tr:
        return ""
    names = sorted({x for _, _, b in tr for x in b if x.split(":")[1] in flag})
    dt = config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60
    return (f"{', '.join(n.replace(':', ' ').lower().capitalize() for n in names)} "
            f"@ {tr[0][0]:.0f}-{tr[-1][0] + dt:.0f} min, {w.fault_t:.1f} t")


def _yard_lines(snap, m, yard):
    from demo.assets import loadout
    from demo.sim.stockyard import stacker_pos
    lines, alerts = [], []
    if m < config.SIM_MINUTES:
        layer = stacker_pos(m)[1] + 1
        lines.append([(f"Stockpile {snap['cum']:,.0f} t   chevron layer {layer}/{yard.pile.layers}", WHITE)])
        return lines, alerts
    _, fills = loadout.train_state(yard, m)
    done = [w for w, f in fills if f >= 1.0]
    flagged = [w for w in done if w.flagged]
    rec_t = sum(p.dry_t for t0, _, p in yard.reclaimed if t0 <= m)
    lines.append([(f"Reclaimed {rec_t:,.0f} t   Wagons {len(done)}/{len(yard.wagons)}   ", WHITE),
                  (f"Flagged {len(flagged)}", BAD if flagged else GOOD)])
    if done:
        from statistics import pstdev
        al_in = pstdev(r.product.q["Al2O3"] for r in snap["records"])
        al_out = pstdev(w.parcel.q["Al2O3"] for w in done) if len(done) > 1 else 0.0
        lines.append([("Blending  Al2O3 SD ", GREY), (f"{al_in:.3f} stacked -> {al_out:.3f} wagons", WHITE),
                      (f"  (-{(1 - al_out / al_in):.0%})" if len(done) > 1 else "", GOOD)])
    if flagged:
        w = flagged[-1]
        alerts.append(f"Wagon {w.index:02d} flagged: {_fault_window(w, snap['records'])}")
    return lines, alerts


def _wagon_tags(region, rv3d, snap, pd, s):
    from demo.assets import loadout
    for co, w, f in loadout.wagon_tag_points(snap["yard"], snap["minute"]):
        v = colors.metric_value(w.parcel, pd.metric)
        lines = [f"Wagon {w.index:02d}  {w.parcel.dry_t * f:.0f} t", colors.fmt(pd.metric, v)]
        if w.flagged and f >= 1.0:
            lines.append("FLAG " + _fault_window(w, snap["records"]))
        _tag(region, rv3d, co, lines, s, BAD if (w.flagged and f >= 1.0) else colors.rgba(pd.metric, v),
             width=250 if len(lines) > 2 else 150)


def _tag(region, rv3d, co, lines, s, accent=WHITE, width=170):
    p = location_3d_to_region_2d(region, rv3d, co)
    if p is None or not (0 < p.x < region.width and 0 < p.y < region.height):
        return
    lh = int(16 * s)
    w = int(width * s)
    h = lh * len(lines) + int(8 * s)
    gpu.state.blend_set("ALPHA")
    _rect(p.x, p.y, w, h, (0.05, 0.06, 0.08, 0.72))
    _rect(p.x, p.y, int(4 * s), h, accent)
    y = p.y + h - lh
    for ln in lines:
        _text(p.x + int(8 * s), y + int(3 * s), ln, 12 * s)
        y -= lh
    gpu.state.blend_set("NONE")


def _tags(region, rv3d, snap, pd, s):
    lag = config.PLAYBACK["belt_lag_min"]
    a, b = Vector(config.BELT["start"]), Vector(config.BELT["end"])
    recs = snap["on_belt"]
    step = max(1, len(recs) // config.PLAYBACK["tags_on_belt"])
    for r in recs[::step]:
        f = (snap["minute"] - config.PLAYBACK["product_off_min"] - r.minute) / lag
        co = a + (b - a) * f + Vector((0, 0, 1.2))
        p = r.product
        v = colors.metric_value(p, pd.metric)
        acc = colors.rgba(pd.metric, v)
        fault = [t.split(":")[1] + " " + t.split(":")[2].lower() for t in sorted(p.tags)]
        lines = [p.id + ("  FAULT " + ",".join(fault) if fault else ""),
                 f"{p.dry_t:.0f} t   {colors.fmt(pd.metric, v)}",
                 f"Fe {p.q['Fe']:.1f}  Al2O3 {p.q['Al2O3']:.2f}  SiO2 {p.q['SiO2']:.1f}"]
        _tag(region, rv3d, co, lines, s, acc)


def _feed_tags(region, rv3d, snap, pd, s):
    """Chapter 2: crusher-discharge parcels as they are born (ID, block, tonnes, grade)."""
    from demo.assets import crusher
    from demo import runtime
    cfg = crusher.CRUSHER_BELT
    a, b = Vector(cfg["start"]), Vector(cfg["end"])
    lag = config.PLAYBACK["belt_lag_min"]
    m = snap["minute"]
    recs = [r for r in runtime.STATE["records"] if m - lag <= r.minute <= m]
    step = max(1, len(recs) // config.PLAYBACK["tags_on_belt"])
    for r in recs[::step]:
        f = (m - r.minute) / lag
        co = a + (b - a) * f + Vector((0, 0, 0.8))
        p = r.feed
        _tag(region, rv3d, co, [f"{p.id}  {p.source}", f"{p.dry_t:.0f} t   {p.moisture:.1f}% H2O",
                                f"Fe {p.q['Fe']:.1f}  Al2O3 {p.q['Al2O3']:.2f}  SiO2 {p.q['SiO2']:.1f}"],
             s, GREY)


def _caption(region, scene, s):
    from demo.story import chapters
    i, title, *_ = chapters.chapter_at(scene.frame_current)
    txt = f"{i}/7   {title}"
    blf.size(0, 22 * s)
    w = blf.dimensions(0, txt)[0]
    x, y = (region.width - w) / 2, int(28 * s)
    gpu.state.blend_set("ALPHA")
    _rect(x - 16 * s, y - 12 * s, w + 32 * s, 44 * s, (0.05, 0.06, 0.08, 0.72))
    gpu.state.blend_set("NONE")
    _text(x, y, txt, 22 * s, WHITE)


def draw():
    ctx = bpy.context
    scene, region, rv3d = ctx.scene, ctx.region, ctx.region_data
    if not hasattr(scene, "plantdemo") or rv3d is None:
        return
    from demo import runtime
    snap = runtime.snapshot(scene)
    if snap is None:
        return
    pd = scene.plantdemo
    s = ctx.preferences.system.ui_scale * config.PLAYBACK["overlay_scale"]
    if pd.show_labels:
        for name, co in config.LABELS.items():
            p = location_3d_to_region_2d(region, rv3d, co)
            if p is not None:
                _text(p.x, p.y, name, 14 * s, WHITE)
    overview = False
    if pd.story:                                  # no floating tags in the wide overview chapters
        from demo.story import chapters
        overview = chapters.chapter_at(scene.frame_current)[0] in (1, 7)
    if pd.show_tags and not overview:
        if snap["minute"] < config.SIM_MINUTES:
            _tags(region, rv3d, snap, pd, s)
        if snap.get("yard") is not None:
            _wagon_tags(region, rv3d, snap, pd, s)
        if snap["minute"] < config.SIM_MINUTES:
            _feed_tags(region, rv3d, snap, pd, s)
    if pd.show_kpi:
        _kpi(region, snap, s)
    if pd.story:
        _caption(region, scene, s)


def register():
    global _handle
    if _handle is None and not bpy.app.background:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw, (), "WINDOW", "POST_PIXEL")


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None
