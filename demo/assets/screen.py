"""Inclined vibrating screen on springs: lump (oversize) off the end, fines through
the deck to the slurry sump that feeds the cyclones. The deck shakes during playback."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P

U = config.UPSTREAM


def build(scene):
    import bpy
    col = P.collection("Screen")
    steel = P.material("steel", metallic=0.6, roughness=0.45)
    dark = P.material("steel_dark", metallic=0.5, roughness=0.5)
    safety = P.material("safety")
    conc = P.material("concrete", (0.62, 0.60, 0.56, 1), roughness=0.9)
    x, y = U["screen_xy"]
    z, L, W = U["screen_z"], U["screen_len"], U["screen_w"]
    tilt = math.radians(U["screen_deg"])
    body = bpy.data.objects.new("Screen_Body", None)
    col.objects.link(body)
    body.location = (x, y, z)
    body.rotation_euler = (0, tilt, 0)              # discharge end (+x) lower
    parts = [P.box("Screen_Deck", (L, W, 0.15), (0, 0, 0), P.material("screen_mesh", (0.15, 0.15, 0.15, 1)), col),
             P.box("Screen_Deck2", (L, W, 0.12), (0, 0, -0.7), P.material("screen_mesh"), col)]
    for s in (-1, 1):
        parts.append(P.box(f"Screen_Side{s}", (L, 0.15, 1.6), (0, s * W / 2, 0.1), safety, col))
    parts.append(P.box("Screen_Exciter", (0.8, W + 0.6, 0.8), (-0.6, 0, 1.3), dark, col))
    for o in parts:
        o.parent = body
    for sx in (-1, 1):
        for sy in (-1, 1):
            zz = z - sx * L / 2 * math.sin(tilt) - 1.2
            P.cylinder(f"Screen_Spring{sx}{sy}", 0.18, 0.6, (x + sx * L / 2 * 0.9, y + sy * (W / 2 + 0.2), zz),
                       steel, col, verts=8)
            P.box(f"Screen_Post{sx}{sy}", (0.5, 0.5, zz - 0.3), (x + sx * L / 2 * 0.9, y + sy * (W / 2 + 0.2),
                                                               (zz - 0.3) / 2), safety, col)
    P.box("Screen_Sump", (L * 0.8, W + 1.0, 1.6), (x, y, 0.8), conc, col)
    # screen house frame: columns, crane beam with hoist, access platform and stair
    from demo.assets import _steel as St
    mb = P.Mesh()
    galv = P.material("galv")
    xs, ys, top = (x - 4.2, x + 3.2), (y - 3.0, y + 3.0), 8.5
    for cx in xs:
        for cy in ys:
            mb.bar((cx, cy, 0), (cx, cy, top), 0.3, galv, caps=True)
            mb.box((0.7, 0.7, 0.3), (cx, cy, 0.15), conc)
        mb.bar((cx, ys[0], top), (cx, ys[1], top), 0.3, galv, caps=True)
        mb.bar((cx, ys[0], 0.0), (cx, ys[1], top - 0.3), 0.12, galv)
    for cy in ys:
        mb.bar((xs[0], cy, top), (xs[1], cy, top), 0.3, galv, caps=True)
    mb.bar((xs[0] - 1.5, y, top - 0.4), (xs[1] + 1.5, y, top - 0.4), 0.25, safety, h=0.4, caps=True)   # monorail
    mb.box((0.8, 0.6, 0.7), (x - 1.0, y, top - 1.0), safety)
    pz = 3.6
    St.walkway(mb, (xs[0], y + 2.5, pz), (xs[1], y + 2.5, pz), 1.1, rails=(True, False))
    St.handrail(mb, (xs[0], y + 1.95, pz), (xs[0] + 1.0, y + 1.95, pz), safety, galv)
    St.stair(mb, (xs[1] + 0.6 + pz / 0.2 * 0.25, y + 2.5, 0.0), (xs[1] + 0.6, y + 2.5, pz))
    mb.obj("Screen_Structure", col)
    P.box("Screen_LumpChute", (1.6, 2.0, 1.2), (x + L / 2 + 0.9, y - 1.5, z - L / 2 * math.sin(tilt) - 1.2),
          steel, col)


def update(scene, frame):
    import bpy
    t = frame / scene.render.fps
    a = 0.04 * math.sin(2 * math.pi * U["screen_hz"] * t)
    x, y = U["screen_xy"]
    bpy.data.objects["Screen_Body"].location = (x + a, y, U["screen_z"] + a)
