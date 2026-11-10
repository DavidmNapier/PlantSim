"""Primary crusher station: concrete station with pilasters, ROM dump pocket with liner
walls and wheel stop, rock breaker, clad crusher building with crane house, baghouse dust
collector, e-room on stilts, ROM pad with windrows and its haul ramp; and the crusher
discharge belt."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St
from demo.assets import belt

U = config.UPSTREAM
CRUSHER_BELT = {**config.BELT, "start": U["crusher_belt"][0], "end": U["crusher_belt"][1],
                "width": 1.4, "n_lumps": 220, "lump_r": 0.12}


def _windrow(mb, p0, p1, h, mat):
    """Triangular dirt safety bund along p0 -> p1 (z from the points)."""
    from mathutils import Vector
    p0, p1 = Vector(p0), Vector(p1)
    u, side, up = St.frame(p0, p1)
    s = side * h * 1.2
    v = [p0 - s, p1 - s, p1 + up * h, p0 + up * h, p0 + s, p1 + s]
    mb.add(v, [(0, 1, 2, 3), (3, 2, 5, 4), (0, 3, 4), (1, 5, 2)], mat)


def build(scene):
    col = P.collection("Crusher")
    m = St.mats()
    conc = m["conc"]
    dirt = P.material("pad_dirt", (0.52, 0.30, 0.18, 1), roughness=0.95)
    x, y = U["crusher_xy"]
    h = U["rom_h"]
    top = h - 5.0                                       # station roof = ROM pad level
    mb = P.Mesh()
    # concrete station with pilasters and a capping band
    mb.box((16.0, 14.0, top), (x, y, top / 2), conc)
    for k in range(5):
        for s in (-1, 1):
            mb.box((0.6, 0.4, top), (x - 6.4 + k * 3.2, y + s * 7.1, top / 2), conc)
    mb.box((16.4, 14.4, 0.5), (x, y, top - 0.25), conc)
    # dump pocket: liner walls on three sides, open toward the pad, hopper throat, wheel stop
    pw, pd = 12.0, 11.0
    mb.box((0.8, pd + 1.6, 4.0), (x + pw / 2 - 1.6, y, top + 2.0), conc)
    for s in (-1, 1):
        mb.box((pw, 0.8, 4.0), (x - 1.6, y + s * (pd / 2 + 0.4), top + 2.0), conc)
        mb.box((pw - 0.4, 0.06, 3.2), (x - 1.6, y + s * (pd / 2 - 0.03), top + 1.9), m["dark"])   # liners
    mb.box((0.06, pd, 3.2), (x + pw / 2 - 2.03, y, top + 1.9), m["dark"])
    v = []
    for z, hw in ((top + 0.02, (pw / 2 - 0.5, pd / 2)), (top - 4.0, (2.0, 2.0))):
        v += [(x - 1.6 + sx * hw[0], y + sy * hw[1], z) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    mb.add(v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["dark"])
    mb.box((1.2, pd, 1.2), (x - 1.6 - pw / 2 - 0.6, y, top + 0.6), m["safety"])                # wheel stop
    for k in range(6):
        mb.box((0.25, pd + 0.02, 1.22), (x - 1.6 - pw / 2 - 0.6, y - pd / 2 + 0.9 + k * 1.9, top + 0.6),
               P.material("stripe_black", (0.05, 0.05, 0.05, 1)))
    # rock breaker on a pedestal on the +y wall
    bx, by, bz = x + 1.5, y + pd / 2 + 0.4, top + 4.0
    mb.cyl(0.9, 1.2, (bx, by, bz + 0.6), m["safety"], n=16)
    mb.bar((bx, by, bz + 1.2), (bx - 3.0, by - 2.5, bz + 3.0), 0.6, m["safety"], caps=True)
    mb.bar((bx - 3.0, by - 2.5, bz + 3.0), (bx - 5.0, by - 4.5, bz + 0.5), 0.45, m["safety"], caps=True)
    mb.bar((bx - 5.0, by - 4.5, bz + 0.5), (bx - 5.0, by - 4.5, bz - 1.5), 0.35, m["dark"], caps=True)
    mb.pipe((bx, by, bz + 1.5), (bx - 3.0, by - 2.5, bz + 3.6), 0.12, m["galv"], n=8)
    # crusher building with crane house on the downstream side of the pocket
    with mb.at((0, 0, top)):
        St.shed(mb, x + 5.5, y, 6.0, 15.0, 9.0, pitch=8.0, doors=(("+x", 3.0, 3.5, 4.0),), vents=2, plinth=0.0)
    St.stair(mb, (x + 3.0, y - 9.2, 0.0), (x + 3.0 + top / 0.2 * 0.25 * 0.5, y - 9.2, top / 2))
    St.stair(mb, (x + 6.0, y - 9.2, top / 2), (x + 6.0 - top / 0.2 * 0.25 * 0.5, y - 10.3, top))
    St.walkway(mb, (x - 8.0, y - 7.6, top), (x + 8.0, y - 7.6, top), 1.0, rails=(False, True))
    # e-room (transportable) on stilts and its stair
    ex, ey = x + 4.5, y - 13.0
    mb.box((7.0, 3.2, 3.0), (ex, ey, 2.4 + 1.5), P.material("clad_green"))
    mb.box((7.4, 3.6, 0.15), (ex, ey, 5.5), m["roof"])
    for sx in (-3.2, 0.0, 3.2):
        for sy in (-1.3, 1.3):
            mb.bar((ex + sx, ey + sy, 0), (ex + sx, ey + sy, 2.4), 0.2, m["galv"])
    St.stair(mb, (ex - 6.5, ey - 2.2, 0), (ex - 3.5, ey - 2.2, 2.4))
    St.walkway(mb, (ex - 3.5, ey - 2.2, 2.4), (ex + 3.5, ey - 2.2, 2.4), 1.0, rails=(False, True))
    for sx in (-2.0, 1.0):
        mb.box((0.9, 0.06, 2.1), (ex + sx, ey - 1.63, 3.45), m["trim"])
    # baghouse dust collector with hopper, stack and duct into the station
    dx, dy = x - 3.0, y - 12.0
    mb.box((3.2, 3.2, 4.5), (dx, dy, 7.25), m["galv"])
    v = [(dx + sx * hw, dy + sy * hw, z) for z, hw in ((5.0, 1.6), (3.2, 0.4))
         for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    mb.add(v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["galv"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.bar((dx + sx * 1.5, dy + sy * 1.5, 0), (dx + sx * 1.5, dy + sy * 1.5, 5.0), 0.22, m["galv"])
    mb.pipe((dx, dy + 1.6, 8.5), (dx, y - 7.0, 6.5), 0.45, m["galv"], n=12)
    mb.pipe((dx + 1.0, dy, 9.5), (dx + 1.0, dy, 13.0), 0.35, m["galv"], n=12, caps=True)
    mb.box((1.6, 1.4, 1.6), (dx + 2.4, dy, 6.5), P.material("machinery"))
    # ROM pad, windrows and the haul ramp up to it
    px0, px1 = x - 1.6 - pw / 2 - 1.2, x - 1.6 - pw / 2 - 1.2 - U["rom_pad"][0]
    pyw = U["rom_pad"][1]
    mb.box((px0 - px1, pyw, top), ((px0 + px1) / 2, y, top / 2 - 0.01), dirt)
    for s in (-1, 1):
        _windrow(mb, (px1, y + s * (pyw / 2 - 1.0), top), (px0, y + s * (pyw / 2 - 1.0), top), 1.4, dirt)
    rl = U["ramp_len"]
    rw = 14.0
    v = [(px1, y - rw / 2, top), (px1, y + rw / 2, top), (px1 - rl, y + rw / 2, 0.0), (px1 - rl, y - rw / 2, 0.0)]
    mb.add(v, [(0, 3, 2, 1)], dirt)
    for s in (-1, 1):
        mb.add([(px1, y + s * rw / 2, top), (px1 - rl, y + s * rw / 2, 0.0), (px1, y + s * (rw / 2 + top * 1.3), 0.0)],
               [(0, 1, 2)], dirt)
        _windrow(mb, (px1 - rl, y + s * (rw / 2 - 1.0), 0.0), (px1, y + s * (rw / 2 - 1.0), top), 1.4, dirt)
    # ROM pad light tower
    mb.bar((px1 + 3, y + pyw / 2 - 2.5, top), (px1 + 3, y + pyw / 2 - 2.5, top + 14.0), 0.3, m["galv"])
    mb.box((1.6, 0.3, 0.6), (px1 + 3, y + pyw / 2 - 2.5, top + 14.0), P.emissive("lamp", (1.0, 0.95, 0.8, 1), 0.6))
    # discharge apron feeder house onto the crusher belt
    mb.box((5.0, 4.0, 3.0), (x + 9.5, y, 1.5), conc)
    mb.box((4.0, 3.0, 1.2), (x + 10.0, y, 3.6), m["galv"])
    mb.obj("Crusher_Structure", col)
    belt.build(scene, "CrusherBelt", CRUSHER_BELT)


def update(scene, frame, colour_fn):
    belt.update(scene, frame, "CrusherBelt", CRUSHER_BELT, colour_fn=colour_fn)
