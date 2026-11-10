"""Straight conveyor between two points: belt, stringers, idler sets, legs and
travelling ore lumps (GN instances). Reused by later conveyors."""
from __future__ import annotations

import math
import random

from mathutils import Vector

from demo import config
from demo.assets import _prims as P


def build(scene, name="ProductBelt", cfg=config.BELT, lumps=False, walk_side=None, gallery=None,
          hoods=True, head=True, tail=True):
    """Belt structure as one mesh `{name}_Structure`: troughed belt on 3-roll idler sets,
    return rollers, channel stringers, head/tail pulleys, walkway with handrail and kick
    plate on one side, hood hoops; ground legs for low belts, a box-truss gallery on
    trestle bents for high ones. Ore is drawn as tonnage segments by demo/viz/segments.py;
    lumps=True adds the old moving-lump point cloud instead."""
    from demo.assets import _steel as St
    C = config.CONVEYOR
    col = P.collection(name)
    a, b = Vector(cfg["start"]), Vector(cfg["end"])
    d = b - a
    L = d.length
    u, side, up = St.frame(a, b)
    w = cfg["width"]
    m = St.mats()
    rubber = P.material("rubber", roughness=0.9)
    roll = P.material("steel_dark")
    mb = P.Mesh()
    ws = walk_side if walk_side is not None else cfg.get("walk_side", 1)
    ww = C["walkway_w"]
    tan = math.tan(math.radians(C["trough_deg"]))
    c_w = w * 0.38                                     # centre roll length

    def at(s_, lat=0.0, h=0.0):
        return a + u * s_ + side * lat + up * h

    # troughed top run + flat return run
    for s0, s1 in ((-c_w / 2, c_w / 2),):
        mb.add([at(0, s0, 0.12), at(L, s0, 0.12), at(L, s1, 0.12), at(0, s1, 0.12)], [(0, 1, 2, 3)], rubber)
    for sg in (-1, 1):
        e0, e1 = c_w / 2 * sg, (w / 2 + 0.05) * sg
        z1 = 0.12 + (w / 2 + 0.05 - c_w / 2) * tan
        mb.add([at(0, e0, 0.12), at(L, e0, 0.12), at(L, e1, z1), at(0, e1, z1)], [(0, 1, 2, 3)], rubber)
    mb.add([at(0, -w / 2, -0.38), at(L, -w / 2, -0.38), at(L, w / 2, -0.38), at(0, w / 2, -0.38)],
           [(0, 1, 2, 3)], rubber)
    # stringers (channel) both sides
    for sg in (-1, 1):
        mb.bar(at(0, sg * (w / 2 + 0.22), -0.05), at(L, sg * (w / 2 + 0.22), -0.05), 0.08, m["galv"], h=0.3,
               caps=True)
    n = max(1, int(L // cfg["idler_pitch"]))
    r = C["roll_r"]
    for k in range(n + 1):
        s_ = k * L / n
        mb.bar(at(s_, -(w / 2 + 0.22), -0.06), at(s_, w / 2 + 0.22, -0.06), 0.06, m["galv"], h=0.08)
        mb.pipe(at(s_, -c_w / 2, 0.12 - r), at(s_, c_w / 2, 0.12 - r), r, roll, n=8)
        for sg in (-1, 1):
            mb.pipe(at(s_, sg * c_w / 2, 0.12 - r), at(s_, sg * (w / 2 + 0.05), 0.12 - r + (w / 2 + 0.05 - c_w / 2) * tan),
                    r, roll, n=8)
        if k % 2 == 0:
            mb.pipe(at(s_, -w / 2, -0.38 - r), at(s_, w / 2, -0.38 - r), r, roll, n=8)
        if hoods and k % C["hoop_every"] == 0 and 0 < k < n:     # hood hoop over the belt
            R = w / 2 + 0.25
            pts = [at(s_, R * math.cos(t), 0.05 + R * 0.9 * math.sin(t)) for t in
                   [math.pi * j / 6 for j in range(7)]]
            for p0, p1 in zip(pts, pts[1:]):
                mb.bar(p0, p1, 0.05, m["galv"])
    # pulleys
    for s_, on in ((0.0, tail), (L, head)):
        if on:
            mb.cyl_m(P.along(at(s_, -w / 2 - 0.1, -0.13), at(s_, w / 2 + 0.1, -0.13), 0.5), m["dark"], n=14)
            for sg in (-1, 1):
                mb.box((0.35, 0.12, 0.35), at(s_, sg * (w / 2 + 0.22), -0.13), m["safety"])
    # walkway along one side, deck just below belt level, handrail on the outside
    wo = ws * (w / 2 + 0.3 + ww / 2)
    p0, p1 = at(0, wo, -0.2), at(L, wo, -0.2)
    St.deck(mb, p0, p1, ww)
    St.handrail(mb, at(0, wo + ws * (ww / 2 - 0.03), -0.2), at(L, wo + ws * (ww / 2 - 0.03), -0.2),
                m["safety"], m["galv"])
    # supports
    lat_c = ws * (ww / 2 + 0.15)            # structure centre shifted toward the walkway
    top_w = w + 0.6 + ww
    if max(a.z, b.z) > C["gallery_min_z"] and gallery is not False:
        dep = C["truss_depth"]
        St.truss(mb, at(0, lat_c, -0.26), at(L, lat_c, -0.26), top_w, dep, m["galv"], panel=2.5,
                 chord=0.14, member=0.08, top_brace=False)
        pitch = C["trestle_pitch"]
        nb = max(1, round(L / pitch))
        yaw = math.atan2(u.y, u.x)
        for k in range(nb + 1):
            c = at(k * L / nb, lat_c, -0.26) - Vector((0, 0, dep))
            if c.z > 0.8:
                St.bent(mb, c, top_w + 0.4, yaw, m["galv"], col_w=0.3)
            else:
                for sg in (-1, 1):
                    f = c + side * (sg * top_w / 2)
                    mb.bar(Vector((f.x, f.y, 0.0)), f + Vector((0, 0, dep * 0.5)), 0.2, m["galv"])
    else:
        for k in range(0, n + 1, 2):
            s_ = k * L / n
            for lat in (-(w / 2 + 0.22), w / 2 + 0.22, wo + ws * ww / 2):
                foot = at(s_, lat, -0.2)
                if foot.z > 0.05:
                    mb.bar(Vector((foot.x, foot.y, 0.0)), foot, 0.1, m["galv"])
            if at(s_, 0, -0.2).z > 0.8:
                mb.bar(Vector((*at(s_, -(w / 2 + 0.22), 0)[:2], 0.25)), Vector((*at(s_, wo, 0)[:2], 0.25)),
                       0.08, m["galv"])
    mb.obj(f"{name}_Structure", col)
    if not lumps:
        return None
    lumps = P.point_cloud(f"{name}_Lumps", cfg["n_lumps"], P.attr_material("ore_metric"),
                          cfg["lump_r"], col, colour_attr=True)
    lumps["belt"] = (*a, *b)
    update(scene, 1, name, cfg)
    return lumps


_layout = {}       # belt name -> static per-lump layout (computed once)
COLOUR_BUCKETS = 24  # colour lookups per belt per frame (lumps share the nearest bucket)


def _static(name, cfg, seed=7):
    key = (name, cfg["start"], cfg["end"], cfg["n_lumps"])
    if key not in _layout:
        rng = random.Random(seed)
        a, b = Vector(cfg["start"]), Vector(cfg["end"])
        d = b - a
        u = d.normalized()
        side = Vector((-u.y, u.x, 0)).normalized()
        n = cfg["n_lumps"]
        lumps = []
        for i in range(n):
            s0 = (i + rng.random() * 0.8) / n * d.length
            lat = (rng.random() - 0.5) * cfg["width"] * 0.5
            dz = 0.18 + rng.random() * 0.05
            lumps.append((s0, a.x + side.x * lat, a.y + side.y * lat, a.z + dz))
        _layout[key] = (d.length, (u.x, u.y, u.z), lumps)
    return _layout[key]


def lump_coords(cfg, t, name="belt"):
    """Lumps spread along the belt, moving at belt speed, slight random scatter."""
    L, (ux, uy, uz), lumps = _static(name, cfg)
    v = cfg["speed_mps"] * t
    out, fracs = [], []
    for s0, bx, by, bz in lumps:
        s = (s0 + v) % L
        out += (bx + ux * s, by + uy * s, bz + uz * s)
        fracs.append(s / L)
    return out, fracs


def update(scene, frame, name="ProductBelt", cfg=config.BELT, colour_fn=None):
    """colour_fn(fraction_along_belt) -> rgba. Default: plain ore colour."""
    import bpy
    obj = bpy.data.objects.get(f"{name}_Lumps")
    if obj is None:                      # belt drawn with segments instead
        return
    coords, fracs = lump_coords(cfg, frame / scene.render.fps, name)
    P.set_points(obj, coords)
    fn = colour_fn or (lambda f: config.COLORS["ore"])
    nb = COLOUR_BUCKETS
    table = [tuple(fn((k + 0.5) / nb)) for k in range(nb)]
    flat = []
    for f in fracs:
        flat += table[min(nb - 1, int(f * nb))]
    P.set_colours(obj, flat)
