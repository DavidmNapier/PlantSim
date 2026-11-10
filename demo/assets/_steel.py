"""Structural steel kit on top of _prims.Mesh: handrails with kick plates, grating
walkways, stairs, box trusses, trestle bents, braced towers, transfer towers and clad
sheds. Every function adds geometry to a Mesh `mb` in its current frame."""
from __future__ import annotations

import math

from mathutils import Vector

from demo import config
from demo.assets import _prims as P

S = config.STEEL


def mats():
    return {"galv": P.material("galv"), "safety": P.material("safety"), "grating": P.material("grating"),
            "dark": P.material("steel_dark"), "conc": P.material("concrete"), "clad": P.material("clad"),
            "roof": P.material("roof"), "door": P.material("roller_door"), "trim": P.material("trim"),
            "window": P.material("window")}


def frame(p0, p1):
    """(u along, side horizontal-left, up) unit vectors for a path p0 -> p1."""
    p0, p1 = Vector(p0), Vector(p1)
    u = (p1 - p0).normalized()
    side = Vector((-u.y, u.x, 0.0))
    side = side.normalized() if side.length > 1e-6 else Vector((0, 1, 0))
    return u, side, u.cross(side)


# ------------------------------------------------------------------ handrails, decks, stairs
def handrail(mb, p0, p1, rail=None, kick=None, h=None, pitch=None, end_posts=True):
    """Handrail along floor-level points p0 -> p1: vertical posts, top and mid rails,
    kick plate (set kick=None to omit)."""
    rail = rail or P.material("safety")
    h = h or S["rail_h"]
    pitch = pitch or S["post_pitch"]
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    n = max(1, math.ceil(L / pitch))
    up = Vector((0, 0, 1))
    for k in range(0 if end_posts else 1, n + 1 if end_posts else n):
        c = p0.lerp(p1, k / n)
        mb.bar(c, c + up * h, S["post_w"], rail)
    for z in (h, S["mid_h"]):
        mb.bar(p0 + up * z, p1 + up * z, S["rail_w"], rail, caps=True)
    if kick is not None:
        _, side, _ = frame(p0, p1)
        kz = up * (S["kick_h"] / 2)
        mb.bar(p0 + kz, p1 + kz, 0.012, kick, h=S["kick_h"])


def deck(mb, p0, p1, width, mat=None, t=None):
    """Grating deck strip centred on p0 -> p1 (top surface at the path)."""
    mat = mat or P.material("grating")
    t = t or S["deck_t"]
    u, side, up = frame(p0, p1)
    off = up * (-t / 2)
    mb.boxm(P.along(Vector(p0) + off, Vector(p1) + off, width, t, roll_up=up), mat)


def walkway(mb, p0, p1, width, rails=(True, True), rail=None, kick=None, grating=None, support=None):
    """Deck plus handrails on the chosen sides (left, right of travel)."""
    kick = kick if kick is not None else P.material("galv")
    deck(mb, p0, p1, width, grating)
    u, side, up = frame(p0, p1)
    for s, on in zip((1, -1), rails):
        if on:
            o = side * (s * (width / 2 - 0.03))
            handrail(mb, Vector(p0) + o, Vector(p1) + o, rail, kick)
    if support:      # cross-beams under the deck every ~2.5 m
        n = max(1, int((Vector(p1) - Vector(p0)).length // 2.5))
        for k in range(n + 1):
            c = Vector(p0).lerp(Vector(p1), k / n) - up * 0.12
            mb.bar(c - side * width / 2, c + side * width / 2, 0.15, support, h=0.18)


def stair(mb, base, top, width=None, rail=None, mat=None, grating=None):
    """Straight flight from floor point base to floor point top (centreline)."""
    width = width or S["stair_w"]
    rail = rail or P.material("safety")
    mat = mat or P.material("galv")
    grating = grating or P.material("grating")
    b, t = Vector(base), Vector(top)
    u, side, up = frame(b, t)
    rise = t.z - b.z
    n = max(2, round(rise / S["stair_rise"]))
    for s in (-1, 1):
        o = side * (s * width / 2)
        mb.bar(b + o - Vector((0, 0, 0.15)), t + o - Vector((0, 0, 0.15)), 0.04, mat, h=0.25)
        handrail(mb, b + o, t + o, rail, None, pitch=2.5)
    for k in range(1, n):
        c = b.lerp(t, k / n)
        mb.boxm(P.along(c - side * width / 2, c + side * width / 2, S["stair_going"] + 0.02, 0.04), grating)


def stair_tower_flights(mb, x, y, z0, z1, yaw=0.0, width=None, run=None):
    """Switch-back stair from z0 to z1 on a footprint at (x, y), landings every ~3.6 m."""
    width = width or S["stair_w"]
    rail = P.material("safety")
    grating = P.material("grating")
    galv = P.material("galv")
    levels = max(1, math.ceil((z1 - z0) / 3.6))
    dz = (z1 - z0) / levels
    run = run or dz / S["stair_rise"] * S["stair_going"]
    with mb.at((x, y, 0), (0, 0, yaw)):
        for k in range(levels):
            za, zb = z0 + k * dz, z0 + (k + 1) * dz
            s = 1 if k % 2 == 0 else -1
            y0 = s * width / 2 + s * 0.05
            xa, xb = (0.0, run) if s > 0 else (run, 0.0)
            stair(mb, (xa, y0, za), (xb, y0, zb), width, rail, galv, grating)
            # landing at the top of this flight
            lx = run + 0.7 if s > 0 else -0.7
            deck(mb, (lx - 0.7, 0, zb), (lx + 0.7, 0, zb), 2 * width + 0.2, grating)
            handrail(mb, (lx + 0.7 * s, -width - 0.1, zb), (lx + 0.7 * s, width + 0.1, zb), rail, galv)
            for cy in (-width - 0.1, width + 0.1):
                mb.bar((lx + 0.7 * s, cy, 0), (lx + 0.7 * s, cy, zb), 0.12, galv)


# ------------------------------------------------------------------ trusses and bents
def truss(mb, p0, p1, width, depth, mat, panel=3.0, chord=0.16, member=0.09, top_brace=True,
          depth1=None):
    """Box truss: top chords run along p0 -> p1 at +-width/2; bottom chords `depth` below
    (in the path's up frame). depth1 tapers the depth toward p1. Warren side diagonals,
    lateral bracing top and bottom."""
    p0, p1 = Vector(p0), Vector(p1)
    u, side, up = frame(p0, p1)
    L = (p1 - p0).length
    n = max(1, round(L / panel))
    depth1 = depth if depth1 is None else depth1

    def pt(i, s, bottom):
        f = i / n
        d = depth + (depth1 - depth) * f
        return p0 + (p1 - p0) * f + side * (s * width / 2) - up * (d if bottom else 0.0)

    for s in (-1, 1):
        for bottom in (False, True):
            mb.bar(pt(0, s, bottom), pt(n, s, bottom), chord, mat, caps=True)
    for i in range(n + 1):
        for s in (-1, 1):
            mb.bar(pt(i, s, False), pt(i, s, True), member, mat)
        mb.bar(pt(i, -1, True), pt(i, 1, True), member, mat)
        if top_brace:
            mb.bar(pt(i, -1, False), pt(i, 1, False), member, mat)
    for i in range(n):
        a, b = (i, i + 1) if i % 2 == 0 else (i + 1, i)
        for s in (-1, 1):
            mb.bar(pt(a, s, False), pt(b, s, True), member, mat)
        mb.bar(pt(i, -1, True), pt(i + 1, 1, True), member * 0.8, mat)
        if top_brace:
            mb.bar(pt(i, 1, False), pt(i + 1, -1, False), member * 0.8, mat)


def plane_truss(mb, p0, p1, depth, mat, panel=2.0, chord=0.12, member=0.07, normal_side=None):
    """Single flat Warren truss below the line p0 -> p1 (for booms' side frames etc.)."""
    p0, p1 = Vector(p0), Vector(p1)
    u, side, up = frame(p0, p1)
    L = (p1 - p0).length
    n = max(1, round(L / panel))
    top = [p0.lerp(p1, i / n) for i in range(n + 1)]
    bot = [t - up * depth for t in top]
    mb.bar(top[0], top[-1], chord, mat, caps=True)
    mb.bar(bot[0], bot[-1], chord, mat, caps=True)
    for i in range(n + 1):
        mb.bar(top[i], bot[i], member, mat)
    for i in range(n):
        mb.bar(top[i], bot[i + 1], member, mat) if i % 2 == 0 else mb.bar(bot[i], top[i + 1], member, mat)


def bent(mb, centre_top, width, yaw, mat, col_w=0.3, brace=None):
    """Trestle bent: two columns from the ground to a crosshead at centre_top, X-braced
    between ground and crosshead when taller than 4 m."""
    c = Vector(centre_top)
    side = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
    a, b = c - side * width / 2, c + side * width / 2
    for p in (a, b):
        mb.bar(Vector((p.x, p.y, 0.0)), p, col_w, mat, caps=True)
        mb.box((col_w * 2.2, col_w * 2.2, 0.4), (p.x, p.y, 0.2), P.material("concrete"))
    mb.bar(a - side * 0.2, b + side * 0.2, col_w * 0.9, mat, caps=True)
    brace = brace or mat
    if c.z > 4.0:
        nb = max(1, int(c.z // 5.0))
        for k in range(nb):
            z0, z1 = c.z * k / nb, c.z * (k + 1) / nb
            mb.bar(Vector((a.x, a.y, z0)), Vector((b.x, b.y, z1)), 0.1, brace)
            mb.bar(Vector((b.x, b.y, z0)), Vector((a.x, a.y, z1)), 0.1, brace)
            if k:
                mb.bar(Vector((a.x, a.y, z0)), Vector((b.x, b.y, z0)), 0.12, brace)


def tower(mb, x, y, w, d, levels, col_mat=None, brace_mat=None, floors=True, rails=True, xbrace="xy",
          col_w=0.35, open_side=None):
    """Braced 4-column tower with beams and grating floors at each level in `levels`.
    open_side: '+x', '-x', '+y' or '-y' face left without handrail (stair access)."""
    col_mat = col_mat or P.material("galv")
    brace_mat = brace_mat or col_mat
    rail = P.material("safety")
    kick = P.material("galv")
    zs = [0.0] + list(levels)
    hx, hy = w / 2, d / 2
    corners = [(x - hx, y - hy), (x + hx, y - hy), (x + hx, y + hy), (x - hx, y + hy)]
    for cx, cy in corners:
        mb.bar((cx, cy, 0), (cx, cy, zs[-1]), col_w, col_mat, caps=True)
        mb.box((col_w * 2.5, col_w * 2.5, 0.4), (cx, cy, 0.2), P.material("concrete"))
    faces = [(0, 1, "-y"), (1, 2, "+x"), (2, 3, "+y"), (3, 0, "-x")]
    for z0, z1 in zip(zs, zs[1:]):
        for i, j, f in faces:
            (ax, ay), (bx, by) = corners[i], corners[j]
            mb.bar((ax, ay, z1), (bx, by, z1), col_w * 0.8, col_mat, caps=True)
            if ("x" in xbrace and f in ("+x", "-x")) or ("y" in xbrace and f in ("+y", "-y")):
                mb.bar((ax, ay, z0), (bx, by, z1), 0.12, brace_mat)
                mb.bar((bx, by, z0), (ax, ay, z1), 0.12, brace_mat)
    for z in levels:
        if floors:
            mb.box((w + 0.2, d + 0.2, S["deck_t"]), (x, y, z - S["deck_t"] / 2), P.material("grating"))
        if rails:
            for i, j, f in faces:
                if f == open_side:
                    continue
                (ax, ay), (bx, by) = corners[i], corners[j]
                handrail(mb, (ax, ay, z), (bx, by, z), rail, kick)


def transfer_tower(mb, x, y, top, w=5.0, d=5.0, clad=True, stair_side="-y", yaw=0.0):
    """Transfer tower: braced frame with grating floors every ~3.5 m up to `top`, a clad
    head house above the top floor (clad=True) and an external switch-back stair."""
    m = mats()
    n = max(1, round(top / 3.5))
    levels = [top * (k + 1) / n for k in range(n)]
    with mb.at((x, y, 0), (0, 0, yaw)):
        tower(mb, 0, 0, w, d, levels, m["galv"], m["galv"], open_side=stair_side)
        if clad:
            hh = 3.2
            mb.box((w + 0.3, d + 0.3, hh), (0, 0, top + hh / 2), m["clad"])
            _gable_roof(mb, 0, 0, w + 0.3, d + 0.3, top + hh, 8.0, m)
            s = -1 if stair_side == "-y" else 1
            mb.box((1.0, 0.06, 2.1), (-w / 4, s * (d / 2 + 0.18), top + 1.05), m["trim"])
        s = -1 if stair_side == "-y" else 1
        run = min(max(w - 0.8, 2.4), 4.4)
        stair_tower_flights(mb, -w / 2 + 0.3, s * (d / 2 + 1.1), 0.0, top, 0.0, run=run)


# ------------------------------------------------------------------ sheds
def _gable_roof(mb, x, y, sx, sy, z, pitch_deg, m, overhang=0.4):
    """Gable roof with the ridge along x, gutters along the eaves."""
    rise = math.tan(math.radians(pitch_deg)) * (sy / 2 + overhang)
    hx = sx / 2 + overhang
    for s in (-1, 1):
        e = (y + s * (sy / 2 + overhang), z - math.tan(math.radians(pitch_deg)) * overhang + 0.0)
        ridge = (y, z + math.tan(math.radians(pitch_deg)) * sy / 2)
        p0 = Vector((x, e[0], e[1]))
        p1 = Vector((x, ridge[0], ridge[1] + 0.05))
        mid = (p0 + p1) / 2
        slope = (p1 - p0)
        ang = math.atan2(slope.z, abs(slope.y))
        mb.box((2 * hx, slope.length, 0.06), mid, m["roof"], rot=(-s * ang, 0, 0))
        mb.bar((x - hx, e[0], e[1] - 0.05), (x + hx, e[0], e[1] - 0.05), 0.14, m["galv"], caps=True)   # gutter
    gz = z + math.tan(math.radians(pitch_deg)) * sy / 2
    mb.bar((x - hx, y, gz + 0.05), (x + hx, y, gz + 0.05), 0.2, m["roof"], h=0.08, caps=True)       # ridge cap
    for s in (-1, 1):      # gable infill triangles
        gx = x + s * sx / 2
        mb.poly([(gx, y - sy / 2, z), (gx, y + sy / 2, z), (gx, y, gz)], m["clad"])
    del rise


def shed(mb, x, y, sx, sy, h, pitch=10.0, doors=(), wall=None, vents=0, plinth=0.3, windows=()):
    """Clad portal-frame shed with the ridge along x. doors: [(face, offset, width, height)]
    face in '+y', '-y', '+x', '-x', offset along the face from its centre. windows: same
    tuple shape with a sill height as the 5th item."""
    m = mats()
    wall = wall or m["clad"]
    mb.box((sx + 0.6, sy + 0.6, plinth), (x, y, plinth / 2), m["conc"])
    mb.box((sx, sy, h - plinth), (x, y, plinth + (h - plinth) / 2), wall, skip=("+z", "-z"))
    _gable_roof(mb, x, y, sx, sy, h, pitch, m)
    for k in range(int(sx // 7) + 1):         # portal frame columns showing at the corners/bays
        px = x - sx / 2 + k * sx / max(1, int(sx // 7))
        for s in (-1, 1):
            mb.box((0.12, 0.06, h - plinth), (px, y + s * (sy / 2 + 0.03), plinth + (h - plinth) / 2), m["trim"])
    for face, off, w, dh in doors:
        _opening(mb, x, y, sx, sy, face, off, w, dh, plinth, m["door"], m)
        _hood(mb, x, y, sx, sy, face, off, w, plinth + dh, m)
    for face, off, w, dh, sill in windows:
        _opening(mb, x, y, sx, sy, face, off, w, dh, sill, m["window"], m)
    gz = h + math.tan(math.radians(pitch)) * sy / 2
    for k in range(vents):
        vx = x - sx / 2 + (k + 0.5) * sx / vents
        mb.box((1.2, 1.2, 0.6), (vx, y, gz + 0.3), m["galv"])
        mb.box((1.5, 1.5, 0.08), (vx, y, gz + 0.65), m["galv"])
    for cx, cy in ((x - sx / 2, y - sy / 2), (x + sx / 2, y - sy / 2), (x - sx / 2, y + sy / 2),
                   (x + sx / 2, y + sy / 2)):
        mb.bar((cx, cy, plinth), (cx, cy, h), 0.1, m["galv"])     # downpipes


def _face_frame(x, y, sx, sy, face, off):
    if face == "-y":
        return Vector((x + off, y - sy / 2, 0)), Vector((1, 0, 0)), Vector((0, -1, 0))
    if face == "+y":
        return Vector((x + off, y + sy / 2, 0)), Vector((1, 0, 0)), Vector((0, 1, 0))
    if face == "+x":
        return Vector((x + sx / 2, y + off, 0)), Vector((0, 1, 0)), Vector((1, 0, 0))
    return Vector((x - sx / 2, y + off, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))


def _opening(mb, x, y, sx, sy, face, off, w, h, z0, mat, m):
    c, t, n = _face_frame(x, y, sx, sy, face, off)
    size = (w if t.x else 0.06, w if t.y else 0.06, h)
    mb.box(size, c + n * 0.04 + Vector((0, 0, z0 + h / 2)), mat)
    for s in (-1, 1):     # jambs
        mb.box((0.12 if t.x else 0.12, 0.12, h), c + t * (s * (w / 2 + 0.06)) + n * 0.06 + Vector((0, 0, z0 + h / 2)),
               m["trim"])


def _hood(mb, x, y, sx, sy, face, off, w, z, m):
    c, t, n = _face_frame(x, y, sx, sy, face, off)
    size = (w + 0.4 if t.x else 0.5, w + 0.4 if t.y else 0.5, 0.5)
    mb.box(size, c + n * 0.25 + Vector((0, 0, z + 0.25)), m["trim"])
