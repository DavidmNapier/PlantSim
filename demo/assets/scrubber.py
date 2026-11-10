"""Rotary scrubber drum on trunnion rollers with girth gear and drive (spins during
playback), feed chute, discharge chute to the screens and a side walkway."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St

U = config.UPSTREAM


def build(scene):
    import bpy
    col = P.collection("Scrubber")
    m = St.mats()
    x, y = U["scrubber_xy"]
    z, r, L = U["scrubber_z"], U["scrubber_r"], U["scrubber_len"]
    drum = bpy.data.objects.new("Scrubber_Drum", None)
    col.objects.link(drum)
    drum.location = (x, y, z)
    shell = P.material("scrubber", (0.25, 0.40, 0.30, 1), metallic=0.4, roughness=0.5, dust=0.6)
    mb = P.Mesh()
    rx = (0, math.pi / 2, 0)
    mb.lathe([(r * 0.55, -L / 2 - 0.3), (r * 0.8, -L / 2), (r, -L / 2 + 0.4), (r, L / 2 - 0.4), (r * 0.8, L / 2),
              (r * 0.6, L / 2 + 0.3)], shell, n=24, rot=rx)
    for s in (-1, 1):            # riding tyres
        mb.lathe([(r, s * L * 0.3 - 0.25), (r + 0.18, s * L * 0.3 - 0.25), (r + 0.18, s * L * 0.3 + 0.25),
                  (r, s * L * 0.3 + 0.25)], m["galv"], n=32, rot=rx, smooth=False)
    mb.lathe([(r, L * 0.1 - 0.15), (r + 0.35, L * 0.1 - 0.15), (r + 0.35, L * 0.1 + 0.15), (r, L * 0.1 + 0.15)],
             m["dark"], n=48, rot=rx, smooth=False)                               # girth gear
    for k in range(48):
        a = 2 * math.pi * k / 48
        mb.box((0.28, 0.1, 0.1), (L * 0.1, (r + 0.4) * math.cos(a), (r + 0.4) * math.sin(a)), m["dark"], rot=(a, 0, 0))
    for k in range(8):           # shell flanges / lifter bolt rows show the rotation
        a = k * math.pi / 4
        mb.box((L * 0.8, 0.22, 0.1), (0, (r + 0.04) * math.cos(a), (r + 0.04) * math.sin(a)), m["dark"], rot=(a, 0, 0))
    mb.obj("Scrubber_Shell", col, drum)

    sm = P.Mesh()
    for s in (-1, 1):            # trunnion roller pairs on concrete piers
        px = x + s * L * 0.3
        sm.box((1.6, 5.0, z - r - 0.6), (px, y, (z - r - 0.6) / 2), m["conc"])
        for sy in (-1, 1):
            sm.cyl(0.45, 0.5, (px, y + sy * r * 0.62, z - r * 0.85), m["dark"], rot=(0, math.pi / 2, 0), n=14)
            sm.box((1.0, 0.8, 0.5), (px, y + sy * r * 0.62, z - r - 0.4), m["dark"])
    sm.box((2.0, 1.6, 1.4), (x + L * 0.1, y - r - 1.4, z - r + 0.4), m["dark"])          # gearbox
    sm.cyl(0.45, 1.6, (x + L * 0.1 + 1.8, y - r - 1.4, z - r + 0.4), P.material("machinery"),
           rot=(0, math.pi / 2, 0), n=14)
    sm.box((3.0, 2.0, 0.5), (x + L * 0.1 + 0.8, y - r - 1.4, z - r - 0.6), m["conc"])
    # feed chute from the crusher belt head, discharge chute to the screen
    v = [(x - L / 2 - 1.0 + sx * hw, y + sy * hw, zz) for zz, hw in ((z + 0.8, 0.8), (z + 2.8, 1.4))
         for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    sm.add(v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], m["galv"])
    sm.box((2.4, 2.6, 2.0), (x + L / 2 + 1.0, y, z - 0.6), m["galv"])
    sm.box((1.0, 1.6, 1.0), (x + L / 2 + 2.6, y, z - 1.3), m["galv"])
    # side walkway at drum-centre height with handrails, stair down
    wz = z - 0.6
    St.walkway(sm, (x - L / 2, y + r + 1.0, wz), (x + L / 2, y + r + 1.0, wz), 1.0)
    for k in range(4):
        px = x - L / 2 + k * L / 3
        sm.bar((px, y + r + 1.4, 0), (px, y + r + 1.4, wz), 0.15, m["galv"])
    St.stair(sm, (x - L / 2 - 0.5 - wz / 0.2 * 0.25, y + r + 1.0, 0), (x - L / 2 - 0.5, y + r + 1.0, wz))
    sm.obj("Scrubber_Structure", col)


def update(scene, frame):
    import bpy
    t = frame / scene.render.fps
    bpy.data.objects["Scrubber_Drum"].rotation_euler = (t * U["scrubber_rpm"] / 60 * 2 * math.pi, 0, 0)
