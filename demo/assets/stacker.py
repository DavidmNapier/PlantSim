"""Rail-mounted luffing stacker beside the pile, the yard conveyor feeding it, and the
discharge stream from the boom tip onto the pile crest."""
from __future__ import annotations

import math
import random

from mathutils import Vector

from demo import config
from demo.assets import _prims as P
from demo.assets import belt, pile
from demo.sim.stockyard import stacker_pos

G = config.YARD_GEOM
YARD_BELT = {**config.BELT, "start": (G["x0"] - G["tail_back"], G["yard_belt_y"], G["yard_belt_z"]),
             "end": (G["x0"] + G["length"] + 8.0, G["yard_belt_y"], G["yard_belt_z"]),
             "n_lumps": 260, "idler_pitch": 3.0}


def build(scene):
    import bpy
    from demo.assets import _steel as St
    col = P.collection("Stacker")
    m = St.mats()
    rubber = P.material("rubber")
    x_a, x_b = G["x0"] - 30.0, G["x0"] + G["length"] + 12.0
    rails = P.Mesh()
    for s in (-1, 1):
        y = G["rail_y"] + 2.0 * s
        rails.box((x_b - x_a, 0.16, 0.18), ((x_a + x_b) / 2, y, 0.09), m["dark"])
        rails.box((x_b - x_a, 0.9, 0.12), ((x_a + x_b) / 2, y, 0.0), m["conc"])
    ty = G["yard_belt_y"] - G["rail_y"]          # tripper rides on the yard belt stringers (local y)
    rails.obj("StackerRails", col)
    belt.build(scene, "YardBelt", YARD_BELT, walk_side=-1, hoods=False)

    root = bpy.data.objects.new("Stacker", None)
    col.objects.link(root)
    ph = G["boom_pivot_h"]
    mb = P.Mesh()
    # bogies and portal
    for bx in (-3.0, 3.0):
        for by in (-2.0, 2.0):
            mb.box((2.2, 0.5, 0.5), (bx, by, 0.9), m["dark"])
            for wx in (-0.6, 0.6):
                mb.cyl(0.4, 0.2, (bx + wx, by, 0.4), m["dark"], rot=(math.pi / 2, 0, 0), n=14)
    for by in (-2.0, 2.0):
        mb.box((8.0, 0.9, 1.0), (0, by, 1.6), m["safety"])
    mb.box((8.0, 5.0, 0.5), (0, 0, 2.3), m["safety"])
    # lattice tower up to the pivot, platform with handrails, stair
    St.tower(mb, 0, 0, 2.4, 2.4, [ph - 0.9], m["safety"], m["safety"], floors=False, rails=False, col_w=0.25)
    mb.box((3.4, 3.4, 0.08), (0, 0, ph - 0.94), m["grating"])
    for (ax, ay), (bx_, by_) in (((-1.7, -1.7), (1.7, -1.7)), ((1.7, -1.7), (1.7, 1.7)), ((-1.7, -1.7), (-1.7, 1.7))):
        St.handrail(mb, (ax, ay, ph - 0.9), (bx_, by_, ph - 0.9), m["safety"], m["galv"])
    St.stair_tower_flights(mb, -1.0, 2.3, 2.55, ph - 0.9, 0.0, run=2.6)
    mb.box((1.4, 2.0, 1.6), (2.8, -1.8, 3.35), P.material("machinery"))        # e-house / drives
    mb.cyl(1.2, 0.9, (-3.9, 0, 2.3), m["dark"], rot=(0, math.pi / 2, 0), n=18)  # cable reel
    # tripper car: inclined belt truss lifting the yard belt up to the boom feed chute
    tl, hz = G["tripper_len"], G["tripper_head_z"]
    t0 = Vector((-tl - 2.0, ty, G["yard_belt_z"] + 0.3))
    t1 = Vector((-2.0, ty, hz))
    St.truss(mb, t0 + Vector((0, 0, -0.1)), t1 + Vector((0, 0, -0.1)), 1.8, 1.1, m["galv"], panel=2.0,
             chord=0.12, member=0.07, top_brace=False)
    u = (t1 - t0).normalized()
    mb.boxm(P.along(t0 + Vector((0, 0, 0.12)), t1 + Vector((0, 0, 0.12)), 1.1, 0.04, roll_up=(0, 0, 1)), rubber)
    St.handrail(mb, t0 + Vector((0, 1.0, 0.0)), t1 + Vector((0, 1.0, 0.0)), m["safety"], m["galv"], pitch=2.5)
    sw = YARD_BELT["width"] / 2 + 0.22
    bz = G["yard_belt_z"]
    for k in range(4):
        p = t0.lerp(t1, (k + 0.5) / 4)
        for s in (-1, 1):
            mb.bar(Vector((p.x, ty + sw * s, bz + 0.3)), Vector((p.x, ty + 0.9 * s, p.z - 1.0)), 0.16, m["safety"],
                   caps=True)
            mb.cyl(0.18, 0.12, (p.x, ty + sw * s, bz + 0.25), m["dark"], rot=(math.pi / 2, 0, 0), n=10)
    mb.cyl(0.35, 1.3, t1 + Vector((0, 0, -0.15)), m["dark"], rot=(math.pi / 2, 0, 0), n=14)
    mb.boxm(P.along(t1 + Vector((0.3, 0, -0.2)), Vector((0.0, -0.6, ph + 0.9)), 1.2, 1.0), m["galv"])  # feed chute
    mb.bar((-2.5, ty, hz - 1.2), (-0.8, -1.2, ph - 1.0), 0.3, m["safety"])     # tripper drawbar / head support
    for s in (-1, 1):
        mb.bar((-2.5, ty + sw * s, bz + 0.3), (-2.5, ty + 0.9 * s, hz - 1.2), 0.25, m["safety"], caps=True)
    mb.obj("Stacker_Base", col, root)

    pivot = bpy.data.objects.new("Stacker_BoomPivot", None)
    col.objects.link(pivot)
    pivot.parent = root
    pivot.location = (0, 0, ph)
    L = G["boom_len"]
    mb = P.Mesh()
    # lattice boom along +y, conveyor on top, walkway, head pulley and hood
    St.truss(mb, (0, 0.6, 0.8), (0, L - 0.8, 0.8), 1.8, 1.8, m["safety"], panel=2.4, chord=0.16, member=0.09,
             depth1=1.0)
    mb.box((1.1, L - 0.4, 0.04), (0, L / 2 + 0.2, 1.0), rubber)
    for k in range(int(L // 2.0)):
        y = 1.0 + k * 2.0
        mb.pipe((-0.6, y, 0.9), (0.6, y, 0.9), 0.06, m["dark"], n=6)
    St.walkway(mb, (1.35, 0.8, 0.6), (1.35, L - 1.5, 0.6), 0.7, rails=(True, False))
    mb.cyl(0.5, 1.6, (0, L, 0.6), m["dark"], rot=(0, math.pi / 2, 0), n=14)
    mb.box((1.8, 1.6, 1.2), (0, L - 0.3, 1.1), m["galv"])                    # head hood
    for s in (-1, 1):
        mb.boxm(P.along((s * 0.9, -0.4, -0.2), (s * 0.9, 1.4, 0.6), 1.2, 0.12, roll_up=(1, 0, 0)), m["safety"])
        mb.cyl(0.45, 0.3, (s * 0.95, 0, 0), m["dark"], rot=(0, math.pi / 2, 0), n=14)
    # A-frame mast, stays, counterweight tail boom
    apex = (0.0, -1.0, 6.5)
    for s in (-1, 1):
        mb.bar((s * 0.9, 0.2, 0.8), (s * 0.3, apex[1], apex[2]), 0.25, m["safety"], caps=True)
    mb.box((1.0, 0.8, 0.6), apex, m["safety"])
    cw = G["cw_len"]
    for s in (-1, 1):
        for tgt in ((s * 0.9, L * 0.6, 0.8), (s * 0.9, L - 1.5, 0.8), (s * 0.9, -cw + 0.8, 0.8)):
            mb.pipe((s * 0.3, apex[1], apex[2]), tgt, 0.045, m["galv"], n=6)
    St.truss(mb, (0, -0.4, 0.8), (0, -cw + 1.0, 0.8), 1.6, 1.4, m["safety"], panel=2.0, chord=0.16, member=0.09)
    mb.box((3.2, 2.6, 2.8), (0, -cw, -0.2), P.material("counterweight"))
    for k in range(4):
        mb.box((3.3, 0.12, 2.9), (0, -cw - 1.0 + k * 0.67, -0.2), m["safety"])
    # operator cab on the boom side
    mb.box((1.8, 1.8, 0.2), (-1.9, 2.0, -0.9), m["safety"])
    mb.box((1.6, 1.6, 1.9), (-1.9, 2.0, 0.1), m["clad"])
    mb.box((1.66, 1.66, 0.8), (-1.9, 2.0, 0.35), m["window"])
    mb.bar((-1.0, 2.0, -0.6), (-0.9, 2.0, 0.5), 0.2, m["safety"])
    mb.obj("Stacker_Boom", col, pivot)
    P.point_cloud("Stacker_Stream", G["stream_n"], P.attr_material("ore_metric"), 0.22, col,
                  colour_attr=True)
    return root


def x_at(minute: float) -> float:
    if minute >= config.SIM_MINUTES:
        return G["x0"] + G["length"] + 4.0           # parked past the pile end
    f, _ = stacker_pos(minute)
    return G["x0"] + f * G["length"]


def update(scene, minute: float, colour_rgba_linear, frame: int):
    import bpy
    x = x_at(minute)
    bpy.data.objects["Stacker"].location = (x, G["rail_y"], 0.0)
    crest = pile.height_at(None, minute, x)
    stacking = minute < config.SIM_MINUTES
    target = crest + G["drop_h"] if stacking else G["boom_pivot_h"] + 4.0
    s = max(-0.5, min(0.6, (target - G["boom_pivot_h"]) / G["boom_len"]))
    ang = math.asin(s)
    bpy.data.objects["Stacker_BoomPivot"].rotation_euler = (ang, 0.0, 0.0)
    tip_y = G["rail_y"] + G["boom_len"] * math.cos(ang)
    tip_z = G["boom_pivot_h"] + G["boom_len"] * math.sin(ang)
    # stream: falling ore from the head pulley to the crest
    rng = random.Random(3)
    n = G["stream_n"]
    t = frame / scene.render.fps
    coords = []
    for i in range(n):
        f = ((i + rng.random()) / n + t * 1.5) % 1.0
        if not stacking:
            coords += (x, 0.0, -50.0)
            continue
        z = tip_z - f * (tip_z - crest)
        coords += (x + (rng.random() - 0.5) * 0.8, tip_y + 0.6 * f + (rng.random() - 0.5) * 0.6, z)
    stream = bpy.data.objects["Stacker_Stream"]
    P.set_points(stream, coords)
    P.set_colours(stream, list(colour_rgba_linear) * n)
