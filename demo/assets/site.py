"""Static site dressing: roads, clad sheds with roller doors, transportable admin and
control buildings, substation with transformers and fence, the tailings thickener,
process water tanks, light towers and distant berms."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St

ROADS = [((-320.0, 0.0), (-238.0, 0.0), 12.0),     # haul road to the foot of the ROM ramp
         ((-240.0, -50.0), (240.0, -50.0), 7.0),   # service road
         ((-240.0, -50.0), (-240.0, -8.0), 7.0),
         ((-20.0, -50.0), (-20.0, -10.0), 6.0)]
BERMS = [((-320.0, 180.0), 120.0), ((380.0, -220.0), 140.0), ((40.0, 300.0), 130.0),
         ((-340.0, -240.0), 110.0), ((420.0, 200.0), 120.0)]
THICKENER = {"xy": (-18.0, 22.0), "r": 9.0, "h": 3.2}
S = config.SITE


def _thickener(mb, m):
    x, y = THICKENER["xy"]
    r, h = THICKENER["r"], THICKENER["h"]
    mb.cyl(r + 0.6, 0.4, (x, y, 0.2), m["conc"], n=48)
    mb.lathe([(r, 0.4), (r, h), (r - 0.08, h), (r - 0.08, 0.4)], m["galv"], n=48, loc=(x, y, 0), smooth=True)
    for z in (1.2, 2.2):
        mb.lathe([(r, z - 0.06), (r + 0.12, z - 0.06), (r + 0.12, z + 0.06), (r, z + 0.06)], m["galv"], n=48,
                 loc=(x, y, 0), smooth=False)
    # overflow launder around the rim
    t = 0.04
    mb.lathe([(r + 0.0, h), (r + 0.0, h - 0.5), (r + 0.6, h - 0.5), (r + 0.6, h + 0.05), (r + 0.6 - t, h + 0.05),
              (r + 0.6 - t, h - 0.5 + t), (r + t, h - 0.5 + t)], m["galv"], n=48, loc=(x, y, 0), smooth=False)
    mb.cyl(r - 0.3, 0.05, (x, y, h - 0.25), P.material("tailings", (0.55, 0.45, 0.30, 1), roughness=0.2), n=48)
    # half bridge from the rim to the centre drive, walkway with handrails
    St.truss(mb, (x - r - 0.8, y, h + 1.6), (x, y, h + 1.6), 1.6, 1.2, m["safety"], panel=1.8, chord=0.12,
             member=0.07)
    St.walkway(mb, (x - r - 0.8, y, h + 1.65), (x + 0.8, y, h + 1.65), 1.4)
    mb.cyl(1.4, 1.2, (x, y, h + 2.3), m["dark"], n=20)                         # rake drive
    mb.cyl(1.6, 1.6, (x, y, h - 0.4), m["galv"], n=20)                         # feedwell
    mb.box((0.8, 0.8, 0.6), (x + 1.2, y + 0.8, h + 2.2), P.material("machinery"))
    St.stair(mb, (x - r - 6.0, y - 1.5, 0.0), (x - r - 1.6, y - 1.5, h + 1.65))
    # underflow pump house
    mb.box((4.0, 3.0, 2.8), (x + r + 4.0, y + 3.0, 1.4), P.material("clad"))
    mb.box((4.4, 3.4, 0.15), (x + r + 4.0, y + 3.0, 2.9), m["roof"])


def _transformer(mb, x, y, m):
    mb.box((2.0, 1.6, 2.0), (x, y, 1.2), P.material("transformer", (0.45, 0.50, 0.42, 1), dust=0.6))
    for k in range(6):
        mb.box((0.05, 1.9, 1.5), (x - 0.9 + k * 0.36, y, 1.1), P.material("transformer"))
    for k in range(3):
        mb.cyl(0.08, 0.6, (x - 0.5 + k * 0.5, y, 2.5), P.material("insulator", (0.45, 0.30, 0.20, 1)), n=8)
    mb.box((2.4, 2.0, 0.2), (x, y, 0.1), m["conc"])


def _fence(mb, x0, y0, x1, y1, m):
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L // 3.0))
        for k in range(n):
            px, py = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            mb.bar((px, py, 0), (px, py, 2.4), 0.06, m["galv"])
        for z in (0.1, 2.4):
            mb.bar((ax, ay, z), (bx, by, z), 0.04, m["galv"], caps=True)
        mb.boxm(P.along((ax, ay, 1.25), (bx, by, 1.25), 0.01, 2.3), P.material("fence_mesh", (0.5, 0.52, 0.53, 0.35)))


def _light_tower(mb, x, y, h, m):
    mb.bar((x, y, 0), (x, y, h), 0.35, m["galv"], caps=True)
    mb.box((1.2, 1.2, 0.5), (x, y, 0.25), m["conc"])
    mb.box((1.6, 0.3, 0.6), (x, y, h + 0.3), P.emissive("lamp", (1.0, 0.95, 0.8, 1), 0.6))


def build(scene):
    import bpy
    col = P.collection("Site")
    m = St.mats()
    mb = P.Mesh()
    road = P.material("road", (0.30, 0.27, 0.25, 1), roughness=0.95)
    for (x0, y0), (x1, y1), w in ROADS:
        L = math.hypot(x1 - x0, y1 - y0)
        mb.box((L + w, w, 0.06), ((x0 + x1) / 2, (y0 + y1) / 2, 0.03), road, rot=(0, 0, math.atan2(y1 - y0, x1 - x0)))
    # workshop: clad portal-frame shed with roller doors facing the service road
    x, y, sx, sy, h = S["workshop"]
    doors = [("+y", -sx / 2 + 5.0 + k * 7.5, 6.0, 7.0) for k in range(3)] + [("-x", 0.0, 5.0, 6.0)]
    St.shed(mb, x, y, sx, sy, h, pitch=8.0, doors=doors, vents=4,
            windows=[("-y", -8.0, 6.0, 1.0, 5.5), ("-y", 8.0, 6.0, 1.0, 5.5)])
    mb.box((10.0, 8.0, 0.2), (x + sx / 2 - 6.0, y + sy / 2 + 5.0, 0.1), m["conc"])           # wash pad apron
    # admin and control room: transportables with verandahs
    for key in ("admin", "control"):
        x, y, sx, sy, h = S[key]
        mb.box((sx, sy, h - 0.6), (x, y, 0.6 + (h - 0.6) / 2), P.material("clad_green"))
        mb.box((sx + 0.4, sy + 0.4, 0.2), (x, y, h + 0.1), m["roof"])
        for bx in range(int(sx // 2.5)):
            mb.bar((x - sx / 2 + 1.25 + bx * 2.5, y - sy / 2 - 1.0, 0.6),
                   (x - sx / 2 + 1.25 + bx * 2.5, y - sy / 2 - 1.0, h), 0.08, m["galv"])
            mb.box((1.4, 0.06, 0.9), (x - sx / 2 + 1.25 + bx * 2.5, y - sy / 2 - 0.02, 2.2), m["window"])
        mb.box((sx + 0.4, 2.4, 0.1), (x, y - sy / 2 - 0.8, h + 0.05), m["roof"])               # verandah roof
        mb.box((sx, 2.0, 0.15), (x, y - sy / 2 - 0.9, 0.55), P.material("deck_timber", (0.45, 0.35, 0.25, 1),
                                                                      dust=0.8))
        for k in range(int(sx // 3.0) + 1):
            mb.bar((x - sx / 2 + k * sx / int(sx // 3.0), y + sy / 2 - 0.3, 0), (x - sx / 2 + k * sx / int(sx // 3.0),
                   y + sy / 2 - 0.3, 0.6), 0.15, m["conc"])
    # substation: building, transformers, fence
    x, y, sx, sy, h = S["substation"]
    St.shed(mb, x, y, sx, sy, h, pitch=5.0, doors=[("-y", 0.0, 2.0, 2.4)])
    for k in range(2):
        _transformer(mb, x - 2.0 + k * 4.0, y - sy / 2 - 4.0, m)
    _fence(mb, x - sx / 2 - 2.0, y - sy / 2 - 7.0, x + sx / 2 + 2.0, y + sy / 2 + 1.5, m)
    for k in range(4):                                                           # overhead line poles
        px = x - 30.0 - k * 40.0
        mb.bar((px, y, 0), (px, y, 12.0), 0.3, P.material("pole", (0.40, 0.33, 0.26, 1), dust=0.6))
        mb.bar((px, y - 1.5, 11.5), (px, y + 1.5, 11.5), 0.15, m["galv"])
    _thickener(mb, m)
    # process water tanks
    for tx, ty, tr, th in S["tanks"]:
        mb.cyl(tr + 0.4, 0.3, (tx, ty, 0.15), m["conc"], n=32)
        mb.lathe([(tr, 0.3), (tr, th), (tr * 0.98, th + 0.15), (0.0, th + 0.6)], m["galv"], n=32, loc=(tx, ty, 0))
        for z in [0.3 + k * (th - 0.3) / 5 for k in range(1, 5)]:
            mb.lathe([(tr, z - 0.04), (tr + 0.06, z - 0.04), (tr + 0.06, z + 0.04), (tr, z + 0.04)], m["galv"],
                     n=32, loc=(tx, ty, 0), smooth=False)
        n = int(th / 0.35)
        for k in range(n):                                                    # caged ladder rungs
            mb.bar((tx + tr + 0.15, ty - 0.25, 0.3 + k * 0.35), (tx + tr + 0.15, ty + 0.25, 0.3 + k * 0.35), 0.03,
                   m["galv"], caps=True)
        for s in (-1, 1):
            mb.bar((tx + tr + 0.15, ty + s * 0.25, 0.3), (tx + tr + 0.15, ty + s * 0.25, th + 0.9), 0.05, m["galv"])
    for lx, ly in S["light_towers"]:
        _light_tower(mb, lx, ly, 16.0, m)
    mb.obj("Site_Dressing", col)
    hill = P.material("berm", (0.50, 0.32, 0.20, 1), roughness=0.95)
    for i, ((bx, by), r) in enumerate(BERMS):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=r, location=(bx, by, 0))
        o = bpy.context.active_object
        o.scale = (1.0, 0.7, 0.12)
        P._finish(o, f"Berm{i}", hill, col, smooth=True)
