"""Desliming cyclone cluster: 5 cyclones around a feed manifold, one see-through
hero cyclone with animated particles (coarse product vs slimes)."""
from __future__ import annotations

import math
import random

from demo import config
from demo.assets import _prims as P

G = config.CYCLONE_GEOM
H = config.HERO


def centre(i: int):
    # rotate so the hero cyclone faces +x (clear view between the legs, above the belt)
    a = 2 * math.pi * (i - config.CYCLONE["hero"]) / config.CYCLONE["count"]
    return G["ring_r"] * math.cos(a), G["ring_r"] * math.sin(a)


def apex_z():
    return G["head_z"] - G["cone_h"] - G["spigot_h"]


def _flange(mb, x, y, z, r, mat, n=24, t=0.035, w=0.05):
    mb.lathe([(r - 0.01, z - t), (r + w, z - t), (r + w, z + t), (r - 0.01, z + t)], mat, n=n, loc=(x, y, 0),
             smooth=False)


def _knife_gate(mb, p, d, mat_body, mat_act):
    """Knife-gate valve centred at p on a pipe running along d."""
    from mathutils import Vector
    p, d = Vector(p), Vector(d).normalized()
    mb.boxm(P.along(p - d * 0.07, p + d * 0.07, 0.34, 0.30), mat_body)        # body
    mb.boxm(P.along(p + Vector((0, 0, 0.15)), p + Vector((0, 0, 0.55)), 0.10, 0.22, roll_up=d), mat_body)
    mb.cyl(0.06, 0.40, (p.x, p.y, p.z + 0.75), mat_act, n=10)                  # pneumatic actuator
    mb.cyl(0.08, 0.05, (p.x, p.y, p.z + 0.97), mat_act, n=10)
    for s in (-1, 1):
        mb.cyl_m(P.along(p + d * (s * 0.09), p + d * (s * 0.12), 0.24), mat_body, n=10)   # flanges


def _one(i, col, mb, hero):
    from mathutils import Vector
    x, y = centre(i)
    steel = P.material("steel")
    rubber = P.material("rubber")
    hdpe = P.material("hdpe")
    hz, hh, ch = G["head_z"], G["head_h"], G["cone_h"]
    hr, ar = G["head_r"], G["apex_r"]
    sz = hz - ch - G["spigot_h"]
    if hero:      # see-through body (separate objects: glass is blended)
        body = P.material("glass")
        P.cylinder(f"Cyc{i + 1}_Head", hr, hh, (x, y, hz + hh / 2), body, col, verts=24)
        P.cone(f"Cyc{i + 1}_Cone", hr, ar, ch, (x, y, hz - ch / 2), body, col, verts=24)
    else:
        mb.lathe([(ar * 1.15, hz - ch), (hr * 0.55, hz - ch * 0.45), (hr * 0.55 + 0.01, hz - ch * 0.45),
                  (hr, hz), (hr, hz + hh), (hr * 0.4, hz + hh + 0.02)], P.material("cyclone"), n=20,
                 loc=(x, y, 0))
    mb.lathe([(ar * 1.3, sz), (ar * 1.3, hz - ch), (ar * 0.5, hz - ch + 0.01)], rubber, n=12, loc=(x, y, 0))
    for z, r in ((hz, hr), (hz + hh, hr), (hz - ch * 0.45, hr * 0.55 + 0.01), (hz - ch, ar * 1.2)):
        _flange(mb, x, y, z, r + 0.005, steel, n=20)
    # vortex finder / overflow riser into the launder above
    vf_top = G["of_launder_z"]
    mb.pipe((x, y, hz + hh), (x, y, vf_top - 0.1), G["vf_r"] * 1.2, hdpe, n=12)
    _flange(mb, x, y, hz + hh + 0.25, G["vf_r"] * 1.2, steel, n=12, w=0.04)
    # tangential feed inlet box and feed pipe from the manifold with a knife-gate valve
    a = math.atan2(y, x)
    tx, ty = -math.sin(a), math.cos(a)
    cx_, cy_ = math.cos(a), math.sin(a)
    iz = hz + hh * 0.65
    ib = Vector((x + tx * hr * 0.75 - cx_ * hr * 0.55, y + ty * hr * 0.75 - cy_ * hr * 0.55, iz))
    t = Vector((tx, ty, 0))
    mb.boxm(P.along(ib - t * 0.25, ib + t * 0.1, 0.2, 0.26), steel)
    mz = sum(G["manifold_z"]) / 2
    m0 = Vector((G["manifold_r"] * math.cos(a + 0.35), G["manifold_r"] * math.sin(a + 0.35), mz))
    mb.pipe(m0, ib - t * 0.25, 0.08, P.material("pipe"), n=10)
    _knife_gate(mb, m0.lerp(ib, 0.45), ib - m0, P.material("steel_dark"), P.material("safety"))


def _u_channel(mb, r, z, w, h, mat, n=40):
    """Ring launder: U section of width w and height h centred on radius r, floor at z."""
    t = 0.03
    prof = [(r - w / 2, z + h), (r - w / 2, z), (r + w / 2, z), (r + w / 2, z + h),
            (r + w / 2 - t, z + h), (r + w / 2 - t, z + t), (r - w / 2 + t, z + t), (r - w / 2 + t, z + h)]
    mb.lathe(prof, mat, n=n, smooth=False)


def build(scene):
    from mathutils import Vector
    from demo.assets import _steel as St
    col = P.collection("Cyclones")
    deck_col = P.collection("CycloneDeck")
    m = St.mats()
    pipe = P.material("pipe")
    mb = P.Mesh()
    for i in range(config.CYCLONE["count"]):
        _one(i, col, mb, hero=(i == config.CYCLONE["hero"]))
    # feed distributor (manifold): dished heads, flanges, pressure gauge
    z0, z1 = G["manifold_z"]
    mr = G["manifold_r"]
    mb.lathe([(0.0, z0 - 0.15), (mr * 0.7, z0 - 0.1), (mr, z0), (mr, z1), (mr * 0.7, z1 + 0.1), (0.0, z1 + 0.15)],
             pipe, n=24)
    for z in (z0 + 0.05, z1 - 0.05, (z0 + z1) / 2):
        _flange(mb, 0, 0, z, mr, m["galv"], n=24, w=0.06)
    mb.pipe((0, 0, z1 + 0.1), (0, 0, z1 + 0.45), 0.03, m["galv"], n=8)
    mb.cyl(0.09, 0.05, (0, 0.0, z1 + 0.5), m["galv"], rot=(math.pi / 2, 0, 0), n=14)
    # launders: overflow ring above the heads, underflow ring under the apexes
    _u_channel(mb, G["ring_r"], G["of_launder_z"] - 0.2, 0.55, 0.4, m["galv"])
    _u_channel(mb, G["ring_r"], G["uf_launder_z"] - 0.25, 0.6, 0.35, m["galv"])
    mb.lathe([(G["ring_r"] - 0.06, G["head_z"] - 0.06), (G["ring_r"] + 0.45, G["head_z"] - 0.06),
              (G["ring_r"] + 0.45, G["head_z"]), (G["ring_r"] - 0.06, G["head_z"])], m["safety"], n=40,
             smooth=False)
    # 4-column frame, beams at underflow, head and deck levels, bracing on the far faces
    c = G["frame_half"]
    dz = G["of_launder_z"] - 0.2
    corners = [(c, c), (c, -c), (-c, -c), (-c, c)]
    for cx, cy in corners:
        mb.bar((cx, cy, 0), (cx, cy, dz), 0.22, m["safety"], caps=True)
        mb.box((0.6, 0.6, 0.3), (cx, cy, 0.15), m["conc"])
    for z in (G["uf_launder_z"] - 0.3, G["head_z"] - 0.12, dz - 0.14):
        for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
            if z < dz - 0.2 and (ax == bx == c or ay == by == -c):
                continue                     # camera-facing faces stay open below the deck (hero view)
            mb.bar((ax, ay, z), (bx, by, z), 0.2, m["safety"], h=0.28, caps=True)
    for (ax, ay), (bx, by), bays in (((-c, -c), (-c, c), 1), ((-c, c), (c, c), 2)):   # far faces (-x, +y)
        for za, zb in ((0.0, G["uf_launder_z"] - 0.3), (G["uf_launder_z"] - 0.3, G["head_z"] - 0.12))[:bays]:
            mb.bar((ax, ay, za), (bx, by, zb), 0.1, m["safety"])
            mb.bar((bx, by, za), (ax, ay, zb), 0.1, m["safety"])
    for k in (1, 2, 3):     # support arms from the ring beam out to the far frame faces
        a = 2 * math.pi * (k + 0.5) / 5
        p = Vector((math.cos(a), math.sin(a), 0))
        mb.bar(p * (G["ring_r"] + 0.4) + Vector((0, 0, G["head_z"] - 0.1)),
               p * (c * 1.1) + Vector((0, 0, G["head_z"] - 0.1)), 0.14, m["safety"], h=0.2)
    # operating deck around the overflow launder (own collection: no shadow), handrails, stair
    dk = P.Mesh()
    cell = 0.5
    rin = G["ring_r"] + 0.32
    n = int(round(2 * c / cell))
    for ix in range(n):
        for iy in range(n):
            px, py = -c + (ix + 0.5) * cell, -c + (iy + 0.5) * cell
            if math.hypot(px, py) > rin:
                dk.box((cell, cell, 0.05), (px, py, dz - 0.025), m["grating"])
    dk.obj("CycloneDeck", deck_col)
    for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
        if ay == c and by == c:              # stair arrives on the +y face
            St.handrail(mb, (ax, ay, dz), (-0.2 * c, by, dz), m["safety"], m["galv"])
            continue
        St.handrail(mb, (ax, ay, dz), (bx, by, dz), m["safety"], m["galv"])
    St.stair_tower_flights(mb, -c + 0.3, c + 1.1, 0.0, dz, yaw=0.0, run=3.6)
    mb.obj("CycloneCluster", col)

    hx, hy = centre(config.CYCLONE["hero"])
    coarse = P.point_cloud("Hero_Coarse", H["n_coarse"], P.material("ore", roughness=0.8),
                           H["radius"], col)
    slimes = P.point_cloud("Hero_Slimes", H["n_slimes"], P.material("slimes", roughness=0.8),
                           H["radius"] * 0.8, col)
    for o in (coarse, slimes):
        o.location = (hx, hy, 0.0)
    update(scene, "NORMAL", 1)


# ------------------------------------------------------------------ particles
def _r_at(z):
    """Inner radius of the hero cyclone at height z."""
    hz, ch = G["head_z"], G["cone_h"]
    if z >= hz:
        return G["head_r"]
    f = max(0.0, (z - (hz - ch)) / ch)
    return G["apex_r"] + f * (G["head_r"] - G["apex_r"])


_rand_cache = {}


def _randoms(n, seed):
    """Per-particle random constants, computed once."""
    if (n, seed) not in _rand_cache:
        rng = random.Random(seed)
        _rand_cache[(n, seed)] = [tuple(rng.random() for _ in range(5)) for _ in range(n)]
    return _rand_cache[(n, seed)]


def particle_coords(n, seed, kind, condition, t):
    """Local (x, y, z) for n particles. kind='coarse' (product) or 'slimes'.
    Pure math so playback is cheap and deterministic."""
    top = G["head_z"] + G["head_h"] * 0.8
    az = apex_z()
    wrong = (H["coarse_to_of"] if kind == "coarse" else H["slimes_to_uf"])[condition]
    if condition == "PULSING":            # bypass comes in surges
        wrong *= 0.5 + 0.5 * math.sin(2 * math.pi * t / 1.5)
    spray = H["spray_r"][condition]
    if condition == "PULSING":
        spray *= 0.4 + 0.6 * abs(math.sin(2 * math.pi * t / 1.5))
    out = []
    for u0, ph, sp, w, jit in _randoms(n, seed):
        p = (u0 + t / H["cycle_s"] * (0.8 + 0.4 * sp)) % 1.0
        to_uf = (kind == "coarse") != (w < wrong)
        if to_uf:
            if p < 0.7:                                    # spiral down the wall
                f = p / 0.7
                if condition == "ROPING":
                    f = f ** 0.45                          # crowding near the apex
                z = top - f * (top - az)
                r = _r_at(z) * (0.85 - 0.1 * jit)
                ang = ph * 6.283 + f * H["laps"] * 6.283 + t * 2.0
            else:                                          # discharge spray / rope
                f = (p - 0.7) / 0.3
                z = az - f * (az - G["uf_launder_z"] - 0.1)
                r = spray * f * (0.3 + 0.7 * jit)
                ang = ph * 6.283
        else:
            if p < 0.15:                                   # brief outer spiral
                f = p / 0.15
                z = top - f * (top - (G["head_z"] - G["cone_h"] * 0.5))
                r = _r_at(z) * 0.8
            else:                                          # inner vortex up and out
                f = (p - 0.15) / 0.85
                zl = G["head_z"] - G["cone_h"] * 0.5
                z = zl + f * (G["of_launder_z"] - zl)
                r = G["vf_r"] * 0.6 * (0.5 + 0.5 * jit)
            ang = ph * 6.283 + p * H["laps"] * 6.283 + t * 3.0
        if condition == "PULSING":
            r *= 1.0 + 0.35 * math.sin(t * 9 + ph * 20)
        out += (r * math.cos(ang), r * math.sin(ang), z)
    return out


def update(scene, condition: str, frame: int):
    import bpy
    t = frame / scene.render.fps
    for name, n, kind, seed in (("Hero_Coarse", H["n_coarse"], "coarse", 1),
                                ("Hero_Slimes", H["n_slimes"], "slimes", 2)):
        P.set_points(bpy.data.objects[name], particle_coords(n, seed, kind, condition, t))
