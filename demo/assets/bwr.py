"""Rail-mounted bucket wheel reclaimer on the +y side of the pile.

Hierarchy: BWR (travels in x) > BWR_Slew (yaw) > BWR_Luff (pitch) > boom, wheel.
The wheel centre is solved each frame to sit on the cut face: luff from the bench
height, slew from the lateral position, and machine travel takes up the rest.
"""
from __future__ import annotations

import math

from mathutils import Matrix, Vector

from demo import config
from demo.assets import _prims as P
from demo.assets import pile

G = config.YARD_GEOM
B = config.BWR_GEOM


def _bogies(mb, xs, ys, m, wheel_r=0.45):
    """Rail bogie groups: an equaliser beam per (x, y) with two 2-wheel bogies."""
    for bx in xs:
        for by in ys:
            mb.box((4.2, 0.6, 0.7), (bx, by, 1.75), m["safety"])
            for dx in (-1.1, 1.1):
                mb.box((1.9, 0.5, 0.5), (bx + dx, by, 1.05), m["dark"])
                for wx in (-0.55, 0.55):
                    mb.cyl(wheel_r, 0.22, (bx + dx + wx, by, wheel_r), m["dark"], rot=(math.pi / 2, 0, 0), n=14)


def _bucket(mb, mat, lip_mat):
    """One bucket in its own frame: x = direction of travel, z = radial out, y = axle.
    Curved shell from the cutting lip under and up the back, side plates, lip and teeth."""
    shell = [(0.85, 0.55), (0.7, -0.15), (0.35, -0.5), (-0.3, -0.55), (-0.7, -0.3), (-0.85, 0.15), (-0.8, 0.5)]
    wy = 0.8
    vs = [(t, s * wy, r) for t, r in shell for s in (-1, 1)]
    fs = [(2 * k, 2 * k + 2, 2 * k + 3, 2 * k + 1) for k in range(len(shell) - 1)]
    mb.add(vs, fs, mat)
    for s in (-1, 1):
        mb.add([(t, s * wy, r) for t, r in shell], [tuple(range(len(shell)))], mat)
    mb.bar((0.85, -wy, 0.55), (0.85, wy, 0.55), 0.12, lip_mat, caps=True)
    for k in range(5):
        ty = -wy + 0.15 + k * (2 * wy - 0.3) / 4
        mb.box((0.35, 0.12, 0.12), (1.0, ty, 0.5), lip_mat, rot=(0, 0.35, 0))


def build(scene):
    import bpy
    from demo.assets import _steel as St
    col = P.collection("Reclaimer")
    m = St.mats()
    rubber = P.material("rubber")
    cw_mat = P.material("counterweight")
    x_a, x_b = G["x0"] - 30.0, G["x0"] + G["length"] + 30.0
    rails = P.Mesh()
    for s in (-1, 1):
        y = B["rail_y"] + 3.0 * s
        rails.box((x_b - x_a, 0.16, 0.18), ((x_a + x_b) / 2, y, 0.09), m["dark"])
        rails.box((x_b - x_a, 0.9, 0.12), ((x_a + x_b) / 2, y, 0.0), m["conc"])
    rails.obj("BWRRails", col)

    def empty(name, parent=None, loc=(0, 0, 0)):
        e = bpy.data.objects.new(name, None)
        col.objects.link(e)
        e.parent, e.location = parent, loc
        return e

    root = empty("BWR")
    # ---- undercarriage: bogies, portal, slew ring, cable reel, access stair
    mb = P.Mesh()
    _bogies(mb, (-4.5, 4.5), (-3.0, 3.0), m)
    for by in (-3.0, 3.0):
        mb.box((11.0, 1.0, 1.1), (0, by, 2.6), m["safety"])
    for bx in (-4.5, 4.5):
        mb.box((1.0, 7.0, 1.1), (bx, 0, 2.6), m["safety"])
    mb.box((5.0, 5.0, 0.8), (0, 0, 2.6), m["safety"])
    mb.cyl(3.5, 0.5, (0, 0, 3.35), m["dark"], n=32)
    mb.lathe([(3.55, 3.15), (3.7, 3.15), (3.7, 3.55), (3.55, 3.55)], m["galv"], n=48, smooth=False)
    mb.cyl(1.4, 1.0, (-6.4, 0, 2.4), m["dark"], rot=(math.pi / 2, 0, 0), n=20)          # cable reel
    for s in (-1, 1):
        mb.box((1.2, 0.15, 2.6), (-6.4, s * 0.6, 1.9), m["safety"])
    St.stair(mb, (2.0, -4.6, 0.0), (5.4, -4.6, 3.15))
    St.walkway(mb, (-5.5, -3.9, 3.15), (5.5, -3.9, 3.15), 0.9, rails=(False, True))
    mb.obj("BWR_Base", col, root)

    slew = empty("BWR_Slew", root, (0, 0, 3.6))
    ph = B["pivot_h"] - 3.6
    # ---- slewing superstructure: deck, machinery house, pivot pylons, operator cab
    mb = P.Mesh()
    mb.box((11.0, 7.0, 0.6), (-1.5, 0, 0.3), m["safety"])
    St.shed(mb, -4.5, 0.0, 4.5, 5.0, 3.6, pitch=8.0, doors=(("+y", 0.8, 1.0, 2.1),), wall=P.material("clad"))
    for s in (-1, 1):
        y = s * 1.6
        mb.prism([(-1.8, -0.2), (1.8, -0.2), (0.7, 0.2), (-0.7, 0.2)], 0.0, 1.0, m["safety"],
                 loc=(0, y, 0.6), rot=(math.pi / 2, 0, 0))          # pylon side plate (thickness along y)
        mb.boxm(P.along((-1.8, y, 0.6), (-0.4, y, ph), 0.5, 0.35), m["safety"])
        mb.boxm(P.along((1.8, y, 0.6), (0.4, y, ph), 0.5, 0.35), m["safety"])
        mb.cyl(0.55, 0.5, (0, y, ph), m["dark"], rot=(math.pi / 2, 0, 0), n=16)
    mb.bar((-0.6, -1.6, ph - 1.5), (-0.6, 1.6, ph - 1.5), 0.4, m["safety"])
    # operator cab on a bracket at the front-right of the deck
    cx, cy, cz = 3.4, 3.3, 3.6
    mb.bar((1.5, 2.4, 0.6), (cx - 0.8, cy, cz - 1.2), 0.3, m["safety"])
    mb.box((2.6, 2.2, 0.25), (cx, cy, cz - 1.25), m["safety"])
    mb.box((2.4, 2.0, 2.1), (cx, cy, cz), m["clad"])
    mb.box((2.46, 2.06, 0.9), (cx + 0.02, cy, cz + 0.25), m["window"])
    mb.box((2.7, 2.3, 0.15), (cx, cy, cz + 1.1), m["trim"])
    St.walkway(mb, (-6.5, -3.4, 0.6), (4.0, -3.4, 0.6), 0.8, rails=(False, True))
    St.handrail(mb, (-7.0, -3.5, 0.6), (-7.0, 3.5, 0.6), m["safety"], m["galv"])
    mb.obj("BWR_Superstructure", col, slew)

    luff = empty("BWR_Luff", slew, (0, 0, ph))
    L = B["boom_len"]
    cwl = B["cw_len"]
    # ---- luffing boom: lattice box truss, conveyor, walkway, mast and stays, counterweight boom
    mb = P.Mesh()
    St.truss(mb, (1.0, 0, 0.9), (L - 4.2, 0, 0.9), 2.6, 2.8, m["safety"], panel=2.8, chord=0.22,
             member=0.12, depth1=1.8)
    for s in (-1, 1):       # boom root plates to the pivot
        mb.boxm(P.along((-0.6, s * 1.3, 0), (1.2, s * 1.3, 0.2), 1.6, 0.12, roll_up=(0, 1, 0)), m["safety"])
        mb.boxm(P.along((L - 4.4, s * 1.25, -0.3), (L - 0.2, s * 1.0, 0.0), 1.8, 0.14, roll_up=(0, 1, 0)),
                m["safety"])
    mb.box((L - 4.0, 1.4, 0.04), ((L - 4.0) / 2 + 1.0, 0, 1.12), rubber)
    for k in range(int((L - 5) // 2.0)):
        x = 1.5 + k * 2.0
        mb.pipe((x, -0.75, 1.0), (x, 0.75, 1.0), 0.07, m["dark"], n=6)
    St.walkway(mb, (1.0, 1.85, 0.75), (L - 4.5, 1.85, 0.75), 0.8, rails=(False, True))
    mb.box((2.2, 1.6, 1.4), (L - 2.6, 0, 1.0), m["galv"])                     # wheel discharge chute
    mb.box((1.2, 1.0, 1.2), (L, -2.1, 0.0), m["dark"])                        # wheel gearbox
    mb.cyl(0.4, 1.4, (L - 1.3, -2.1, 0.0), P.material("machinery"), rot=(0, math.pi / 2, 0), n=14)
    mb.cyl(0.35, 3.0, (L, 0, 0), m["dark"], rot=(math.pi / 2, 0, 0), n=14)   # wheel shaft
    # A-frame mast (luffs with the boom) and stays
    apex = (-1.5, 0.0, 12.0)
    for s in (-1, 1):
        St.truss(mb, (-0.5, s * 1.4, 1.0), (apex[0], s * 0.5, apex[2]), 0.7, 0.7, m["safety"], panel=1.6,
                 chord=0.14, member=0.07)
    mb.box((1.2, 1.6, 0.8), apex, m["safety"])
    for s in (-1, 1):
        for tgt in ((L * 0.55, s * 1.3, 0.9), (L - 4.5, s * 1.0, 0.9), (-cwl + 1.0, s * 1.0, 1.6)):
            mb.pipe((apex[0], s * 0.5, apex[2]), tgt, 0.05, m["galv"], n=6)
    St.truss(mb, (-1.2, 0, 1.4), (-cwl + 2.0, 0, 1.4), 2.2, 2.0, m["safety"], panel=2.4, chord=0.2,
             member=0.1)
    mb.box((4.4, 3.6, 3.6), (-cwl, 0, -0.4), cw_mat)
    for k in range(5):
        mb.box((0.15, 3.7, 3.7), (-cwl - 1.8 + k * 0.9, 0, -0.4), m["safety"])
    mb.obj("BWR_Boom", col, luff)

    wheel = empty("BWR_Wheel", luff, (L, 0, 0))
    R = B["wheel_r"]
    # ---- bucket wheel: hub, twin rims, spokes, buckets with teeth
    mb = P.Mesh()
    rot_y = (math.pi / 2, 0, 0)
    mb.cyl(0.9, 1.8, (0, 0, 0), m["safety"], rot=rot_y, n=18)
    for s in (-1, 1):
        mb.lathe([(R * 0.72, -0.15), (R * 0.86, -0.15), (R * 0.86, 0.15), (R * 0.72, 0.15)], m["safety"], n=40,
                 loc=(0, s * 0.75, 0), rot=rot_y, smooth=False)
        for k in range(B["buckets"]):
            a = 2 * math.pi * (k + 0.5) / B["buckets"]
            mb.bar((0.8 * math.cos(a), s * 0.75, 0.8 * math.sin(a)),
                   (R * 0.75 * math.cos(a), s * 0.75, R * 0.75 * math.sin(a)), 0.22, m["safety"], h=0.12)
    mb.lathe([(R * 0.7, -0.75), (R * 0.7, 0.75)], m["dark"], n=40, rot=rot_y)      # ring chute drum
    for k in range(B["buckets"]):
        a = 2 * math.pi * k / B["buckets"]
        rr = (math.cos(a), 0.0, math.sin(a))
        tt = (math.sin(a), 0.0, -math.cos(a))           # travel direction for +spin about y
        M = Matrix((tt, (0.0, 1.0, 0.0), rr)).transposed().to_4x4()
        M.translation = Vector(rr) * (R * 0.92)
        with mb.at(M=M):
            _bucket(mb, m["dark"], m["galv"])
    mb.obj("BWR_WheelBody", col, wheel)
    park(None)
    return root


def _set(x, yaw, pitch, spin):
    import bpy
    o = bpy.data.objects
    o["BWR"].location = (x, B["rail_y"], 0.0)
    o["BWR_Slew"].rotation_euler = (0.0, 0.0, yaw)
    o["BWR_Luff"].rotation_euler = (0.0, -pitch, 0.0)
    o["BWR_Wheel"].rotation_euler = (0.0, spin, 0.0)


PARK_X = G["x0"] + G["length"] + 25.0      # east end, out of the cyclone and stacking shots
TRANSIT_MIN = 2.0                            # sim minutes to travel to the first cut


def park(minute):
    """Parked at the east end with the boom along the rail; travels to the first cut
    in the TRANSIT_MIN minutes before reclaim starts."""
    start = config.STOCKPILE["reclaim_start_min"]
    if minute is None or minute < start - TRANSIT_MIN or minute >= start:
        _set(PARK_X, 0.0, 0.05, 0.0)
        return
    s0 = pile.state_cache.get(0)
    h, hw = (s0[-1][0], s0[-1][1]) if s0 else (8.0, 10.0)
    x1, yaw1, pitch1 = reach(wheel_target(0, 0.0, h, hw))
    f = (minute - (start - TRANSIT_MIN)) / TRANSIT_MIN
    f = f * f * (3 - 2 * f)                  # ease in/out
    _set(PARK_X + (x1 - PARK_X) * f, yaw1 * f, 0.05 + (pitch1 - 0.05) * f, 0.0)


def reach(target):
    """(machine x, yaw, pitch) putting the wheel centre on target (x, y, z)."""
    tx, ty, tz = target
    L = B["boom_len"]
    s = max(-0.6, min(0.6, (tz - B["pivot_h"]) / L))
    pitch = math.asin(s)
    r = L * math.cos(pitch)
    dy = max(-r * 0.999, min(r * 0.999, ty - B["rail_y"]))
    yaw = math.asin(dy / r)                       # dy < 0: boom reaches toward the pile (-y)
    # choose the branch with the boom ahead of the machine (wheel at +x of machine)
    x = tx - r * math.cos(yaw)
    return x, yaw, pitch


def wheel_target(j, frac, h, hw):
    """Wheel centre for slice j at cut fraction frac, following pile.bench_cut: luff
    and reposition at the start of each bench, then slew across it on the cut line."""
    nb = B["benches"]
    K = B["block_slices"]
    dx = G["length"] / config.STOCKPILE["slices"]
    j = j - j % K                                      # first slice of the cut block
    x = G["x0"] + (j + B["face_frac"] * K) * dx - B["wheel_r"] * 0.4
    c = pile.bench_cut(j // K, frac, h, hw)
    b = c["bench"]

    def z_of(bb):
        return h * (1.0 - (bb + 0.5) / nb) + B["wheel_r"] * 0.3
    z = z_of(b)
    e = B["ease"]
    if c["v"] < e and (j > 0 or b > 0):              # reposition from where the last bench ended
        pb = b - 1 if b > 0 else nb - 1
        w_prev = hw * (1.0 - (nb - 1 - pb) / nb)
        y_prev = c["sgn"] * (w_prev + 0.5)            # previous bench slewed the other way
        k = c["v"] / e
        k = k * k * (3 - 2 * k)
        y = y_prev + (c["y"] - y_prev) * k
        z = z_of(pb) + (z - z_of(pb)) * k
        return x, y, z
    return x, c["y"], z


def update(scene, minute: float, frame: int):
    front = pile.reclaim_front(None, minute)
    if front is None:
        park(minute)
        return
    j, frac, h, hw = front
    x, yaw, pitch = reach(wheel_target(j, frac, h, hw))
    spin = frame / scene.render.fps * B["wheel_rps"] * 2 * math.pi
    _set(x, yaw, pitch, spin)
