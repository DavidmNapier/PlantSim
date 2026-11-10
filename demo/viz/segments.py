"""Ore and slurry drawn as tonnage segments on belts, inside glass pipes and in wagons.

Each parcel is a block along its belt/pipe: its length is the time it occupies on the
conveyor, its height is proportional to its dry tonnes (vs that stream's typical parcel),
and it is split into stacked bands, one per selected metric (top = first metric).

Product streams (cake, reclaimed, wagons) are coloured against the absolute targets in
config.METRICS. Upstream streams (feed, slurries, tailings) are coloured against their
own normal: green at the stream's median, red when it moves the bad way.
"""
from __future__ import annotations

import bisect
import math
import statistics

from demo import config
from demo.viz import colors

NAME = "Segments"
_rel = {}          # (src, metric) -> (median, span)
_nominal = {}      # src -> typical dry t per parcel
_streams = []


def _straight(cfg, dz=0.0):
    (x0, y0, z0), (x1, y1, z1) = cfg["start"], cfg["end"]
    return [(x0, y0, z0 + dz), (x1, y1, z1 + dz)]


def streams():
    """Conveyors in flow order. off/lag in sim minutes: a parcel made at minute t sits on
    this conveyor between minutes t+off and t+off+lag."""
    if _streams:
        return _streams
    from demo.assets import conveyors, crusher, loadout, stacker
    lag = config.PLAYBACK["belt_lag_min"]
    po = config.PLAYBACK["product_off_min"]
    F, Pp = config.FILTER_GEOM, config.PIPES
    fz = F["z"] + 0.05
    mid = F["x0"] + 0.45 * (F["x1"] - F["x0"])
    belt = dict(kind="belt", w=0.75, h=0.6)
    S = [
        dict(belt, name="feed", path=_straight(crusher.CRUSHER_BELT), src="feed", off=0.0, lag=lag, w=1.0, rel=True),
        dict(belt, name="lump", path=_straight(conveyors.LINKS["LumpBelt"]), src="lump", off=1.0, lag=6.0,
             w=0.7, h=0.45, rel=True),
        dict(kind="pipe", name="fines", path=Pp["FeedSlurry"]["pts"], r=Pp["FeedSlurry"]["r"], src="fines",
             off=1.0, lag=4.0, rel=True),
        dict(kind="pipe", name="underflow", path=Pp["Underflow"]["pts"], r=Pp["Underflow"]["r"], src="underflow",
             off=0.0, lag=1.0, rel=True),
        dict(kind="pipe", name="overflow", path=Pp["Overflow"]["pts"], r=Pp["Overflow"]["r"], src="slimes",
             off=0.0, lag=3.0, rel=True),
        dict(belt, name="filter_wet", path=[(F["x0"] + 0.9, F["y"], fz), (mid, F["y"], fz)], src="underflow",
             off=1.0, lag=1.0, w=2.0, h=0.5, rel=True),
        dict(belt, name="filter_cake", path=[(mid, F["y"], fz), (F["x1"], F["y"], fz)], src="product",
             off=2.0, lag=1.0, w=2.0, h=0.4, rel=False),
        dict(belt, name="product", path=_straight(config.BELT), src="product", off=po, lag=lag, rel=False),
        dict(belt, name="transfer", path=_straight(conveyors.LINKS["TransferBelt"]), src="product",
             off=po + lag, lag=3.0, rel=False),
        dict(belt, name="yard", path=_straight(stacker.YARD_BELT), src="product", off=po + 3.0 + lag, lag=8.0,
             rel=False),
        dict(belt, name="reclaim", path=_straight(conveyors.LINKS["ReclaimBelt"]), src="reclaimed", off=0.0,
             lag=3.0, rel=False),
        dict(belt, name="load", path=_straight(loadout.LOAD_BELT), src="reclaimed", off=3.0, lag=2.0, rel=False),
    ]
    _streams.extend(S)
    return _streams


# ------------------------------------------------------------------ data
def _value(p, metric):
    return colors.metric_value(p, metric)


def prepare(records, yard):
    """Per-stream typical tonnes and 'normal' colour ranges; call after each recompute."""
    _rel.clear()
    _nominal.clear()
    srcs = {s["src"] for s in streams()}
    for src in srcs:
        if src == "reclaimed":
            ps = [p for *_, p in yard.reclaimed] if yard else []
        else:
            ps = [getattr(r, src) for r in records if getattr(r, src, None) is not None]
        if not ps:
            continue
        _nominal[src] = statistics.median(p.dry_t for p in ps)
        normal = [p for p, r in zip(ps, records) if all(c == "NORMAL" for c in r.conditions)] \
            if src != "reclaimed" else ps
        normal = normal or ps
        for metric, (_, _, lo, hi, _) in config.METRICS.items():
            vals = sorted(_value(p, metric) for p in normal)
            med = vals[len(vals) // 2]
            span = max(vals[int(0.95 * (len(vals) - 1))] - vals[int(0.05 * (len(vals) - 1))],
                       0.25 * (hi - lo), 0.02 * abs(med), 1e-6)
            _rel[(src, metric)] = (med, span)
    if yard:
        _nominal["wagon"] = config.TRAIN["payload_t"]


def colour(src, metric, v, rel):
    if not rel or (src, metric) not in _rel:
        return colors.rgba(metric, v)
    med, span = _rel[(src, metric)]
    better_high = config.METRICS[metric][4]
    d = (med - v) if better_high else (v - med)
    b = min(1.0, max(0.0, 0.15 + 0.85 * d / span))
    g, m, r = config.RAMP
    a, c, f = (g, m, b * 2) if b < 0.5 else (m, r, b * 2 - 1)
    return (*(a[i] + (c[i] - a[i]) * f for i in range(3)), 1.0)


def _items(stream, minute, records, rec_min, yard):
    """[(t_start, t_end, parcel)] currently on this conveyor."""
    hi = minute - stream["off"]
    lo = hi - stream["lag"]
    if stream["src"] == "reclaimed":
        if not yard:
            return []
        rate = config.STOCKPILE["reclaim_tph"] / 60.0
        return [(t, t + p.dry_t / rate, p) for t, _, p in yard.reclaimed if t <= hi and t + p.dry_t / rate >= lo]
    dt = config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60.0
    i0 = max(0, bisect.bisect_left(rec_min, lo - dt))
    i1 = bisect.bisect_right(rec_min, hi)
    return [(r.minute, r.minute + dt, getattr(r, stream["src"])) for r in records[i0:i1]]


# ------------------------------------------------------------------ geometry
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _frame(u):
    side = _cross(u, (0.0, 0.0, 1.0))
    side = _norm(side) if abs(u[2]) < 0.99 else (0.0, 1.0, 0.0)
    up = _norm(_cross(side, u))
    return side, up


class _Mesh:
    def __init__(self):
        self.verts, self.faces, self.cols = [], [], []

    _F = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (1, 5, 7, 3), (0, 2, 6, 4))

    def box(self, o, u, side, up, L, W, H, rgba):
        """Box from origin o (centre of its bottom-start edge) along u, width W, height H."""
        i = len(self.verts)
        ox, oy, oz = o
        hw = W / 2
        ax, ay, az = u[0] * L, u[1] * L, u[2] * L
        bx, by, bz = side[0] * hw, side[1] * hw, side[2] * hw
        cx, cy, cz = up[0] * H, up[1] * H, up[2] * H
        p0 = (ox - bx, oy - by, oz - bz)               # a = 0, b = -W/2
        p1 = (ox + bx, oy + by, oz + bz)               # a = 0, b = +W/2
        q0 = (p0[0] + ax, p0[1] + ay, p0[2] + az)
        q1 = (p1[0] + ax, p1[1] + ay, p1[2] + az)
        # vertex index = i + 4*a + 2*b + c
        self.verts.extend((p0, (p0[0] + cx, p0[1] + cy, p0[2] + cz), p1, (p1[0] + cx, p1[1] + cy, p1[2] + cz),
                           q0, (q0[0] + cx, q0[1] + cy, q0[2] + cz), q1, (q1[0] + cx, q1[1] + cy, q1[2] + cz)))
        self.faces.extend((i + a, i + b, i + c, i + d) for a, b, c, d in self._F)
        self.cols.extend((rgba,) * 6)

    def banded(self, o, u, side, up, L, W, H, colours):
        n = len(colours)
        for k, rgba in enumerate(colours):          # k = 0 is the top band
            z = H * (n - 1 - k) / n
            ob = (o[0] + up[0] * z, o[1] + up[1] * z, o[2] + up[2] * z)
            self.box(ob, u, side, up, L, W, H / n * 0.96, rgba)


def _path_pieces(path):
    out, s = [], 0.0
    for a, b in zip(path, path[1:]):
        d = _sub(b, a)
        L = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2)
        out.append((s, s + L, a, _norm(d)))
        s += L
    return out, s


def _emit(mesh, stream, f0, f1, height, colours):
    pieces, total = stream.setdefault("_pieces", _path_pieces(stream["path"]))
    sa, sb = f0 * total, f1 * total
    gap = 0.04 * (sb - sa)
    sa, sb = sa + gap, sb - gap
    for p0, p1, a, u in pieces:
        lo, hi = max(sa, p0), min(sb, p1)
        if hi - lo <= 1e-3:
            continue
        side, up = _frame(u)
        o = (a[0] + u[0] * (lo - p0), a[1] + u[1] * (lo - p0), a[2] + u[2] * (lo - p0))
        if stream["kind"] == "pipe":
            r = stream["r"]
            W, H = 1.2 * r, min(1.6 * r, height)
            o = (o[0] - up[0] * H / 2, o[1] - up[1] * H / 2, o[2] - up[2] * H / 2)
        else:
            W, H = stream["w"], height
            o = (o[0] + up[0] * 0.14, o[1] + up[1] * 0.14, o[2] + up[2] * 0.14)
        mesh.banded(o, u, side, up, hi - lo, W, H, colours)


def build(scene):
    import bpy
    from demo.assets import _prims as P
    me = bpy.data.meshes.new(NAME)
    o = bpy.data.objects.new(NAME, me)
    P.collection("Segments").objects.link(o)
    me.materials.append(P.attr_material("segments", attr_type="GEOMETRY", roughness=0.6))
    # Rebuilt every frame along every belt: if it cast shadows, every shadow page over the
    # detailed belt structures would be redrawn each frame (about 5 fps at 1080p).
    o.visible_shadow = False
    return o


def update(scene, minute, metrics, records, yard):
    import bpy
    o = bpy.data.objects.get(NAME)
    if o is None or not records:
        return
    mesh = _Mesh()
    rec_min = [r.minute for r in records]
    for st in streams():
        nominal = _nominal.get(st["src"], 1.0)
        hmax = st["h"] if st["kind"] == "belt" else 1.6 * st["r"]
        for t0, t1, p in _items(st, minute, records, rec_min, yard):
            if p is None:
                continue
            hi = minute - st["off"]
            f_head = min(1.0, (hi - t0) / st["lag"])
            f_tail = max(0.0, (hi - t1) / st["lag"])
            if f_head <= f_tail:
                continue
            h = hmax * min(1.4, p.dry_t / nominal)
            cols = [colors.to_linear(colour(st["src"], m, _value(p, m), st["rel"])) for m in metrics]
            _emit(mesh, st, f_tail, f_head, h, cols)
    if yard is not None:
        _wagons(mesh, yard, minute, metrics)
    me = o.data
    me.clear_geometry()
    me.from_pydata(mesh.verts, [], mesh.faces)
    if "col" not in me.attributes:
        me.attributes.new("col", "FLOAT_COLOR", "FACE")
    flat = [v for c in mesh.cols for v in c]
    if flat:
        me.attributes["col"].data.foreach_set("color", flat)
    me.update()


def _wagons(mesh, yard, minute, metrics):
    from demo.assets import loadout
    LG = config.LOADOUT_GEOM
    pos, fills = loadout.train_state(yard, minute)
    L, W = LG["wagon_len"] - 0.6, LG["wagon_w"] - 0.5
    z = LG["deck_z"] + LG["wagon_h"] - 0.9
    for i, (w, f) in enumerate(fills):
        if f <= 0:
            continue
        x = loadout.wagon_x(i, pos)
        cols = [colors.to_linear(colors.rgba(m, _value(w.parcel, m))) for m in metrics]
        mesh.banded((x - L / 2, LG["track_y"], z), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                    L, W, 0.15 + 1.5 * f, cols)
