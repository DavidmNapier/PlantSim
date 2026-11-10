"""Train load-out: conveyor from the reclaimer, bin on legs with chute and level gauge,
track, locomotive and the wagon rake. Each wagon's load shows its grade colour and
fill; flagged wagons carry a red beacon."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St
from demo.assets import belt

LG = config.LOADOUT_GEOM
N = config.TRAIN["wagons"]
LOAD_BELT = {**config.BELT, "start": LG["belt_start"], "end": LG["belt_end"], "n_lumps": 200,
             "idler_pitch": 2.5}


def _frustum(mb, x, y, z0, z1, h0, h1, mat):
    """Square hopper frustum: half-width h1 at z1 (top) down to h0 at z0."""
    v = [(x + sx * h, y + sy * h, z) for z, h in ((z0, h0), (z1, h1))
         for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    mb.add(v, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)


def _wagon_body(m):
    """Open gondola ore car: floor just under the load segments, ribbed sides, top chord,
    underframe, couplers, end ladders. Mesh is in wagon-local metres (origin on the rail top)."""
    L, W, H, dz = LG["wagon_len"], LG["wagon_w"], LG["wagon_h"], LG["deck_z"]
    mb = P.Mesh()
    wag = P.material("wagon")
    top = dz + H
    floor = dz + H - 0.95
    mb.box((L - 0.2, W - 0.2, 0.08), (0, 0, floor), wag)
    for s in (-1, 1):
        mb.box((L, 0.06, H - 0.25), (0, s * W / 2, dz + 0.25 + (H - 0.25) / 2), wag)
        mb.box((0.06, W, H - 0.25), (s * L / 2, 0, dz + 0.25 + (H - 0.25) / 2), wag)
        mb.box((L + 0.1, 0.18, 0.16), (0, s * (W / 2 + 0.03), top), wag)          # top chord
        mb.box((0.18, W + 0.1, 0.16), (s * (L / 2 + 0.03), 0, top), wag)
        mb.box((L, 0.14, 0.2), (0, s * (W / 2 + 0.03), dz + 0.3), wag)            # side sill
        nr = 11
        for k in range(1, nr):
            rx = -L / 2 + k * L / nr
            mb.box((0.1, 0.09, H - 0.3), (rx, s * (W / 2 + 0.06), dz + 0.3 + (H - 0.3) / 2), wag)
        for ry in (-0.8, 0.0, 0.8):
            mb.box((0.09, 0.1, H - 0.3), (s * (L / 2 + 0.06), ry, dz + 0.3 + (H - 0.3) / 2), wag)
        mb.box((0.5, 0.25, 0.25), (s * (L / 2 + 0.3), 0, dz - 0.1), m["dark"])     # coupler
        mb.box((0.25, 0.32, 0.3), (s * (L / 2 + 0.6), 0, dz - 0.1), m["dark"])
        for k in range(4):                                                         # end ladder rungs
            mb.bar((s * (L / 2 + 0.12), W / 2 - 0.5, dz + 0.4 + k * 0.45), (s * (L / 2 + 0.12), W / 2 - 0.05,
                   dz + 0.4 + k * 0.45), 0.04, m["safety"], caps=True)
    mb.box((L - 1.0, 0.5, 0.4), (0, 0, dz - 0.05), m["dark"])                      # centre sill
    mb.box((0.6, W - 0.4, 0.3), (L / 2 - 1.6, 0, dz), m["dark"])
    mb.box((0.6, W - 0.4, 0.3), (-L / 2 + 1.6, 0, dz), m["dark"])
    mb.cyl(0.25, 0.04, (L / 2 + 0.1, -W / 2 + 0.6, dz + 1.6), m["dark"], rot=(0, math.pi / 2, 0), n=12)
    return mb


def _bogie(m, axles=2, wb=1.8, wheel_r=0.46, frame_mat=None):
    """Bogie centred on its pivot: side frames, bolster, wheelsets (rail gauge 1.435 m)."""
    mb = P.Mesh()
    fm = frame_mat or m["dark"]
    g = 0.72
    xs = [(-wb / 2 + k * wb / (axles - 1)) for k in range(axles)] if axles > 1 else [0.0]
    span = xs[-1] - xs[0]
    for s in (-1, 1):
        mb.box((span + 1.0, 0.18, 0.35), (0, s * (g + 0.2), wheel_r + 0.05), fm)
        mb.box((span * 0.5, 0.18, 0.25), (0, s * (g + 0.2), wheel_r - 0.25), fm)
        for x in xs:
            mb.box((0.3, 0.24, 0.3), (x, s * (g + 0.2), wheel_r), m["dark"])
            mb.cyl(wheel_r, 0.14, (x, s * g, wheel_r), m["dark"], rot=(math.pi / 2, 0, 0), n=16)
    for x in xs:
        mb.pipe((x, -g, wheel_r), (x, g, wheel_r), 0.08, m["dark"], n=8)
    mb.box((0.5, 2 * g + 0.2, 0.3), (0, 0, wheel_r + 0.25), fm)
    return mb


def _loco(m):
    """Generic six-axle heavy-haul long-hood loco, cab at -x. Pilbara-style colours
    (ochre red, cream, dark roof, yellow/black nose), no real company's branding."""
    LL = LG["loco_len"]
    mb = P.Mesh()
    body, cream, dark = P.material("loco_body"), P.material("loco_cream"), P.material("loco_dark")
    h = LL / 2
    mb.box((LL, 3.1, 0.35), (0, 0, 1.6), dark)                                    # deck / underframe
    mb.box((LL - 0.2, 3.12, 0.12), (0, 0, 1.45), m["safety"])                     # yellow sole bar stripe
    for s in (-1, 1):
        St.handrail(mb, (-h + 3.8, s * 1.5, 1.78), (h - 0.3, s * 1.5, 1.78), m["safety"], None, h=1.0, pitch=2.0)
    for tx in (-h + 4.6, h - 4.6):
        mb.merge(_bogie(m, axles=3, wb=3.6, wheel_r=0.53, frame_mat=dark), (tx, 0, 0))
        for k in (-1, 0, 1):
            mb.box((0.6, 1.0, 0.5), (tx + k * 1.6, 0, 0.75), dark)                 # traction motors
    mb.box((6.5, 2.6, 1.0), (0, 0, 0.95), dark)                                   # fuel tank
    mb.box((6.6, 2.62, 0.12), (0, 0, 1.2), m["safety"])
    # long hood with a cream stripe, radiator section and fans at the rear
    hood0, hood1 = -h + 4.6, h - 0.6
    mb.box((hood1 - hood0, 2.4, 2.7), ((hood0 + hood1) / 2, 0, 1.78 + 1.35), body)
    for s in (-1, 1):
        mb.box((hood1 - hood0 - 0.2, 0.02, 0.25), ((hood0 + hood1) / 2, s * 1.21, 3.55), cream)
        for k in range(6):                                                         # hood doors
            mb.box((0.04, 0.02, 1.8), (hood0 + 1.5 + k * 1.6, s * 1.21, 2.6), dark)
    mb.box((4.2, 3.0, 3.0), (h - 2.7, 0, 1.78 + 1.5), body)
    mb.box((4.0, 3.02, 1.4), (h - 2.7, 0, 3.2), dark)                             # radiator grilles
    for k in range(3):
        mb.cyl(0.55, 0.15, (h - 4.1 + k * 1.3, 0, 4.85), dark, n=16)
    mb.box((0.8, 0.5, 0.4), (hood0 + 5.0, 0, 4.65), dark)                         # exhaust
    mb.box((hood1 - hood0, 2.2, 0.12), ((hood0 + hood1) / 2, 0, 4.5), dark)
    # cab and nose
    c0, c1 = -h + 1.4, -h + 4.6
    mb.box((c1 - c0, 3.1, 2.0), ((c0 + c1) / 2, 0, 2.78), body)
    mb.box((c1 - c0, 3.1, 1.2), ((c0 + c1) / 2, 0, 4.38), cream)
    mb.box((c1 - c0 + 0.1, 3.0, 0.15), ((c0 + c1) / 2, 0, 5.05), dark)
    mb.box((c1 - c0 - 0.6, 3.14, 0.7), ((c0 + c1) / 2 + 0.1, 0, 4.35), m["window"])   # side windows
    mb.boxm(P.xform((c0 - 0.05, 0, 4.3), (0, -0.25, 0), (0.1, 2.8, 0.8)), m["window"])  # windscreen
    mb.box((1.4, 2.8, 1.5), (-h + 0.7, 0, 2.55), m["safety"])                     # nose (yellow)
    for s in (-1, 1):
        mb.boxm(P.xform((-h - 0.03, s * 0.65, 2.5), (s * 0.7, 0, 0), (0.04, 0.25, 1.6)), dark)  # black chevron
        mb.box((0.06, 0.3, 0.18), (-h - 0.05, s * 0.9, 3.1), P.emissive("headlight", (1.0, 0.95, 0.8, 1), 4.0))
    mb.boxm(P.xform((-h - 0.2, 0, 0.75), (0, 0.5, 0), (0.12, 3.0, 0.9)), m["safety"])     # pilot / plough
    for s in (-1, 1):
        mb.box((0.6, 0.3, 0.3), (s * (h + 0.25), 0, 1.25), dark)                  # couplers
    return mb


def build(scene):
    import bpy
    col = P.collection("Loadout")
    m = St.mats()
    cx, ty, w = LG["chute_x"], LG["track_y"], LG["bin_w"]
    z0, z1 = LG["bin_z"]
    mb = P.Mesh()
    # bin with stiffeners and ring girders, hopper, flask gate and telescopic chute
    mb.box((w, w, z1 - z0), (cx, ty, (z0 + z1) / 2), m["galv"])
    for k in range(1, 4):
        for s in (-1, 1):
            off = -w / 2 + k * w / 4
            mb.box((0.15, 0.2, z1 - z0), (cx + off, ty + s * (w / 2 + 0.08), (z0 + z1) / 2), m["galv"])
            mb.box((0.2, 0.15, z1 - z0), (cx + s * (w / 2 + 0.08), ty + off, (z0 + z1) / 2), m["galv"])
    for z in (z0 + 0.2, (z0 + z1) / 2, z1 - 0.2):
        mb.box((w + 0.4, w + 0.4, 0.3), (cx, ty, z), m["safety"])
    _frustum(mb, cx, ty, LG["hopper_z"], z0, 0.8, w / 2, m["galv"])
    mb.box((1.8, 1.8, 0.9), (cx, ty, LG["hopper_z"] - 0.3), m["safety"])           # flask gate
    mb.cyl(0.25, 0.8, (cx + 1.2, ty, LG["hopper_z"] + 0.1), m["dark"], rot=(0, math.pi / 2, 0), n=10)
    mb.box((1.3, 1.3, LG["hopper_z"] - LG["chute_z"]), (cx, ty, (LG["hopper_z"] + LG["chute_z"]) / 2 - 0.4),
           m["dark"])
    # load-out structure: braced columns clear of the train, floors at bin bottom and top
    sx, sy = w / 2 + 2.0, w / 2 + 1.0
    St.tower(mb, cx, ty, 2 * sx, 2 * sy, [z0, z1], m["safety"], m["safety"], floors=False, xbrace="y",
             col_w=0.45)
    for z in (z0, z1):
        for s in (-1, 1):
            St.deck(mb, (cx - sx, ty + s * (w / 2 + 0.5), z), (cx + sx, ty + s * (w / 2 + 0.5), z), 1.0)
            St.deck(mb, (cx + s * (w / 2 + 1.0), ty - sy, z), (cx + s * (w / 2 + 1.0), ty + sy, z), 2.0)
    # head house over the bin where the load belt discharges
    mb.box((w + 3.0, w + 2.0, 3.4), (cx, ty, z1 + 1.7), m["clad"])
    St._gable_roof(mb, cx, ty, w + 3.0, w + 2.0, z1 + 3.4, 6.0, m)
    St.stair_tower_flights(mb, cx + sx + 0.6, ty + sy + 1.2, 0.0, z1, 0.0, run=4.0)
    # track: ballast, sleepers near the plant, rails
    x_a, x_b = cx - 400.0, cx + 400.0
    mb.add([(x_a, ty - 2.4, 0.0), (x_b, ty - 2.4, 0.0), (x_b, ty - 1.4, 0.35), (x_a, ty - 1.4, 0.35),
            (x_a, ty + 1.4, 0.35), (x_b, ty + 1.4, 0.35), (x_b, ty + 2.4, 0.0), (x_a, ty + 2.4, 0.0)],
           [(0, 1, 2, 3), (3, 2, 5, 4), (4, 5, 6, 7)], P.material("ballast", (0.36, 0.30, 0.27, 1), roughness=0.95,
                                                                 dust=0.6))
    for k in range(int((LG["sleeper_x"][1] - LG["sleeper_x"][0]) / 0.68)):
        mb.box((0.25, 2.5, 0.12), (LG["sleeper_x"][0] + k * 0.68, ty, 0.39), m["conc"])
    for s in (-1, 1):
        mb.box((x_b - x_a, 0.08, 0.16), ((x_a + x_b) / 2, ty + 0.72 * s, 0.53), m["dark"])
    mb.obj("Loadout_Structure", col)
    g = P.box("Bin_GaugeFrame", (0.3, 0.6, z1 - z0), (cx - w / 2 - 0.6, ty - w / 2 + 0.6, (z0 + z1) / 2),
              m["dark"], col)
    g = P.box("Bin_GaugeLevel", (0.4, 0.5, 1.0), (0, 0, 0.5), P.material("gauge", (0.2, 0.8, 0.3, 1)), col)
    g.location = (cx - w / 2 - 0.65, ty - w / 2 + 0.6, z0)        # mesh spans z 0..1 above origin
    belt.build(scene, "LoadBelt", LOAD_BELT)

    # locomotives: two units on one root, sharing one mesh
    loco = bpy.data.objects.new("Loco", None)
    col.objects.link(loco)
    lm = _loco(m).obj("Loco_Unit1", col, loco)
    u2 = bpy.data.objects.new("Loco_Unit2", lm.data)
    col.objects.link(u2)
    u2.parent, u2.location = loco, (-(LG["loco_len"] + 1.2), 0, 0)

    # wagon template meshes, shared by every wagon (linked duplicates)
    L, W, H, dz = LG["wagon_len"], LG["wagon_w"], LG["wagon_h"], LG["deck_z"]
    tmpl = {
        "body": _wagon_body(m).obj("tmpl_body", col),
        "bogie": _bogie(m).obj("tmpl_bogie", col),
        "beacon": P.cylinder("tmpl_beacon", 0.35, 0.7, (0, 0, 0), _beacon_mat(), col, verts=12),
    }
    for i in range(1, N + 1):
        root = bpy.data.objects.new(f"Wagon{i:02d}", None)
        col.objects.link(root)
        for part, offs in (("body", [(0, 0, 0)]),
                           ("bogie", [(-L / 2 + 1.6, 0, 0), (L / 2 - 1.6, 0, 0)]),
                           ("beacon", [(L / 2 - 0.8, W / 2 - 0.3, dz + H + 0.4)])):
            for k, off in enumerate(offs):
                o = bpy.data.objects.new(f"W{i:02d}_{part}{k}", tmpl[part].data)
                col.objects.link(o)
                o.parent, o.location = root, off
    # wagon loads are drawn as banded tonnage segments by demo/viz/segments.py
    for o in tmpl.values():
        o.hide_viewport = o.hide_render = True


def _beacon_mat():
    return P.emissive("beacon", (1.0, 0.1, 0.05, 1), 6.0)


# ------------------------------------------------------------------ animation
def train_state(yard, minute: float):
    """(head index position, [(wagon, fill 0..1), ...]). Index position p means wagon
    number p+1 is centred under the chute (0.5 steps between wagons)."""
    ws = yard.wagons
    if not ws:
        return -1.0, []
    starts = [w.minute for w in ws]
    ends = starts[1:] + [starts[-1] + config.TRAIN["payload_t"] / config.STOCKPILE["reclaim_tph"] * 60]
    fills, pos = [], -1.5
    for i, (w, a, b) in enumerate(zip(ws, starts, ends)):
        f = min(1.0, max(0.0, (minute - a) / max(b - a, 1e-6)))
        fills.append((w, f))
        if minute >= a:
            pos = i + f - 0.5 + 0.5 * (f >= 1.0)
    if minute < starts[0]:   # approach
        pos = -1.5 + max(0.0, 1.0 - (starts[0] - minute) / 3.0)
    return pos, fills


def wagon_x(i: int, pos: float) -> float:
    """World x of wagon i (0-based) given the head index position. The train runs
    toward -x: empties queue east of the chute, loaded wagons pull west past the yard."""
    return LG["chute_x"] - (pos - i) * LG["spacing"]


def update(scene, yard, minute: float, metric: str, frame: int, belt_colour):
    import bpy
    obs = bpy.data.objects
    pos, fills = train_state(yard, minute)
    ty = LG["track_y"]
    blink = (frame // 6) % 2 == 0
    for i, (w, f) in enumerate(fills):
        root = obs[f"Wagon{i + 1:02d}"]
        root.location = (wagon_x(i, pos), ty, 0.0)
        b = obs[f"W{i + 1:02d}_beacon0"]
        b.hide_viewport = b.hide_render = not (w.flagged and f >= 1.0 and blink)
    obs["Loco"].location = (wagon_x(-1, pos) - (LG["loco_len"] - LG["wagon_len"]) / 2 - 1.0, ty, 0.0)
    # bin level: drawn down as each wagon loads, topped up between wagons (illustrative)
    active = [f for _, f in fills if 0.0 < f < 1.0]
    level = 0.85 - 0.5 * active[0] if active else 0.85
    g = obs["Bin_GaugeLevel"]
    z0, z1 = LG["bin_z"]
    g.scale = (1.0, 1.0, level * (z1 - z0))
    belt.update(scene, frame, "LoadBelt", LOAD_BELT, colour_fn=belt_colour)


def wagon_tag_points(yard, minute):
    """[(world xyz, wagon, fill)] for loaded/loading wagons (used by the overlay)."""
    pos, fills = train_state(yard, minute)
    out = []
    for i, (w, f) in enumerate(fills):
        if f > 0:
            out.append(((wagon_x(i, pos), LG["track_y"], LG["deck_z"] + LG["wagon_h"] + 1.5), w, f))
    return out

