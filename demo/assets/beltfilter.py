"""Horizontal vacuum belt filter: underflow slurry is fed at the tail, vacuum boxes pull
the water through the cloth (filtrate to the receivers and on to the thickener), and cake
drops off the head onto the product belt. One static mesh on an elevated operating deck."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St

F = config.FILTER_GEOM


def build(scene):
    col = P.collection("BeltFilter")
    m = St.mats()
    rubber = P.material("rubber")
    cloth = P.material("filter_cloth", (0.18, 0.20, 0.24, 1), roughness=0.9)
    pipe = P.material("pipe")
    x0, x1, y, z, w = F["x0"], F["x1"], F["y"], F["z"], F["width"]
    L = x1 - x0
    xm = (x0 + x1) / 2
    dz = z - 1.5                                      # operating deck level
    mb = P.Mesh()
    # cloth top run, return run, rubber carrier edges and curbs
    mb.box((L + 0.4, w, 0.08), (xm, y, z), cloth)
    mb.box((L + 0.4, w, 0.04), (xm, y, z - 0.95), cloth)
    for s in (-1, 1):
        mb.box((L + 0.4, 0.12, 0.22), (xm, y + s * (w / 2 + 0.06), z + 0.08), rubber)
    # main frame girders, cross members, drums with bearing blocks
    for s in (-1, 1):
        mb.box((L + 2.0, 0.3, 0.55), (xm, y + s * (w / 2 + 0.45), z - 0.45), m["safety"])
    for k in range(9):
        xx = x0 - 0.6 + k * (L + 1.2) / 8
        mb.bar((xx, y - w / 2 - 0.45, z - 0.7), (xx, y + w / 2 + 0.45, z - 0.7), 0.15, m["safety"], h=0.2)
    for xx in (x0 - 0.2, x1 + 0.2):
        mb.cyl(0.45, w + 0.3, (xx, y, z - 0.45), m["dark"], rot=(math.pi / 2, 0, 0), n=18)
        for s in (-1, 1):
            mb.box((0.5, 0.35, 0.45), (xx, y + s * (w / 2 + 0.45), z - 0.45), m["dark"])
            mb.cyl(0.12, 0.2, (xx, y + s * (w / 2 + 0.7), z - 0.45), m["galv"], rot=(math.pi / 2, 0, 0), n=10)
    # head drive: gearbox and motor; tail take-up cylinders
    mb.box((0.9, 0.8, 0.8), (x1 + 0.2, y - w / 2 - 1.1, z - 0.45), m["dark"])
    mb.cyl(0.3, 1.0, (x1 + 0.2, y - w / 2 - 1.9, z - 0.45), P.material("machinery"), rot=(math.pi / 2, 0, 0), n=14)
    for s in (-1, 1):
        mb.pipe((x0 - 0.2, y + s * (w / 2 + 0.75), z - 0.45), (x0 + 1.2, y + s * (w / 2 + 0.75), z - 0.45), 0.07,
                m["galv"], n=8, caps=True)
    # vacuum box and drop legs to the filtrate manifold
    mb.box((L * 0.85, w * 0.45, 0.4), (xm, y, z - 0.3), m["dark"])
    for k in range(6):
        xx = x0 + L * (k + 0.75) / 6.5
        mb.pipe((xx, y + 0.3, z - 0.5), (xx, y + 1.6, z - 1.1), 0.09, m["galv"], n=8)
    mb.pipe((x0 + 0.5, y + 1.6, z - 1.1), (x1 - 0.5, y + 1.6, z - 1.1), 0.2, m["galv"], n=12, caps=True)
    # cloth wash spray bars on the return run
    for k in range(3):
        xx = x0 + 1.0 + k * 0.6
        mb.pipe((xx, y - w / 2, z - 0.8), (xx, y + w / 2, z - 0.8), 0.04, m["galv"], n=6, caps=True)
    # feed distributor (fish-tail box) at the tail, cake chute at the head
    mb.box((0.8, w * 0.9, 0.5), (x0 + 0.5, y, z + 0.45), m["galv"])
    mb.box((0.4, w * 0.6, 0.3), (x0 + 0.5, y, z + 0.85), m["galv"])
    mb.box((1.0, w + 0.2, 0.25), (x1 + 0.75, y, z - 0.05), m["galv"])
    mb.box((1.1, 1.6, 1.3), (x1 + 0.9, y, z - 0.95), m["galv"])
    # filtrate receivers and vacuum pump on the +y side
    for k, xx in enumerate((x1 - 4.0, x1 - 2.2)):
        ry = y + 3.6
        mb.lathe([(0.0, 0.6), (0.45, 0.65), (0.65, 0.9), (0.65, 3.1), (0.45, 3.35), (0.0, 3.4)], m["galv"], n=20,
                 loc=(xx, ry, 0))
        for a in range(3):
            ang = a * 2 * math.pi / 3
            mb.bar((xx + 0.55 * math.cos(ang), ry + 0.55 * math.sin(ang), 0),
                   (xx + 0.55 * math.cos(ang), ry + 0.55 * math.sin(ang), 1.0), 0.1, m["galv"])
        mb.pipe((xx, ry, 3.4), (xx, ry, 3.7), 0.12, m["galv"], n=8)
        mb.pipe((xx, ry - 0.6, 2.6), (xx, y + 1.6, z - 1.1), 0.12, m["galv"], n=8)
        mb.pipe((xx, ry, 0.6), (xx, ry, 0.2), 0.1, pipe, n=8)
    mb.box((2.4, 1.2, 0.3), (x1 + 0.5, y + 5.6, 0.15), m["conc"])
    mb.box((1.4, 1.0, 1.1), (x1 + 0.1, y + 5.6, 0.85), P.material("machinery"))
    mb.cyl(0.35, 0.9, (x1 + 1.3, y + 5.6, 0.75), P.material("machinery"), rot=(0, math.pi / 2, 0), n=14)
    mb.pipe((x1 + 0.1, y + 5.6, 1.4), (x1 - 2.2, y + 3.6, 3.7), 0.1, m["galv"], n=8)
    # elevated operating deck on columns, handrails, stair from the ground
    dx0, dx1 = x0 - 0.9, x1 + 0.6
    dy = w / 2 + 2.0
    mb.box((dx1 - dx0, 2 * dy, 0.05), ((dx0 + dx1) / 2, y, dz - 0.025), m["grating"])
    for xx in (dx0, (dx0 + dx1) / 2, dx1):
        for s in (-1, 1):
            mb.bar((xx, y + s * dy, 0), (xx, y + s * dy, dz), 0.25, m["safety"], caps=True)
            mb.box((0.6, 0.6, 0.3), (xx, y + s * dy, 0.15), m["conc"])
        mb.bar((xx, y - dy, dz - 0.15), (xx, y + dy, dz - 0.15), 0.2, m["safety"], h=0.3)
    for s in (-1, 1):
        mb.bar((dx0, y + s * dy, dz - 0.15), (dx1, y + s * dy, dz - 0.15), 0.2, m["safety"], h=0.3)
        mb.bar((dx0, y + s * dy, 0.0), ((dx0 + dx1) / 2, y + s * dy, dz - 0.3), 0.1, m["safety"])
    sx = dx0 + 3.2                                    # stair lands on the -y edge
    St.handrail(mb, (dx0, y - dy, dz), (sx - 0.5, y - dy, dz), m["safety"], m["galv"])
    St.handrail(mb, (sx + 0.5, y - dy, dz), (dx1, y - dy, dz), m["safety"], m["galv"])
    St.handrail(mb, (dx0, y + dy, dz), (dx1, y + dy, dz), m["safety"], m["galv"])
    St.handrail(mb, (dx0, y - dy, dz), (dx0, y + dy, dz), m["safety"], m["galv"])
    St.handrail(mb, (dx1, y - dy, dz), (dx1, y + dy, dz), m["safety"], m["galv"])
    run = dz / config.STEEL["stair_rise"] * config.STEEL["stair_going"]
    St.stair(mb, (sx, y - dy - 0.6 - run, 0.0), (sx, y - dy - 0.6, dz))
    St.deck(mb, (sx, y - dy - 0.6, dz), (sx, y - dy, dz), 1.0)
    mb.obj("BeltFilter_Structure", col)
