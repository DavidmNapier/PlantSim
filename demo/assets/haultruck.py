"""Rigid-frame haul trucks (~220 t class, generic) at the ROM pad: one dumping into the
pocket with its tray raised, one queued, one heading back down the ramp. Two shared
meshes (tray down / tray up) placed as linked duplicates from config.TRUCKS."""
from __future__ import annotations

import math

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St

T = config.TRUCK_GEOM


def _wheel(mb, x, y, m, dual=False):
    r = T["wheel_r"]
    tyre = [(r * 0.62, -0.55), (r * 0.86, -0.62), (r, -0.45), (r, 0.45), (r * 0.86, 0.62), (r * 0.62, 0.55)]
    ys = (y - 0.6 * (1 if y > 0 else -1), y + 0.6 * (1 if y > 0 else -1)) if dual else (y,)
    for yy in ys:
        mb.lathe(tyre, P.material("tyre"), n=20, loc=(x, yy, r), rot=(math.pi / 2, 0, 0))
        mb.cyl(r * 0.62, 1.0, (x, yy, r), m["galv"], rot=(math.pi / 2, 0, 0), n=16)


def _tray(mb, m, body):
    """Dump body in hinge-local coordinates (hinge at the origin, front toward +x)."""
    L0, L1 = -1.9, T["tray_front"] - T["hinge_x"]
    w, h = T["tray_w"], T["tray_h"]
    fz = 0.5
    mb.box((L1 - L0, w, 0.25), ((L0 + L1) / 2, 0, fz), body)                     # floor
    for s in (-1, 1):
        mb.box((L1 - L0, 0.2, h), ((L0 + L1) / 2, s * w / 2, fz + h / 2), body)    # sides
        mb.box((L1 - L0, 0.4, 0.3), ((L0 + L1) / 2, s * (w / 2 + 0.1), fz + h), body)
        for k in range(6):
            mb.box((0.25, 0.3, h - 0.3), (L0 + 0.8 + k * (L1 - L0 - 1.6) / 5, s * (w / 2 + 0.2), fz + h / 2), body)
    mb.box((0.3, w, h + 1.0), (L1, 0, fz + (h + 1.0) / 2), body)                  # front wall
    mb.box((T["canopy"], w + 0.6, 0.25), (L1 + T["canopy"] / 2, 0, fz + h + 0.9), body)   # canopy over the cab
    for s in (-1, 1):
        mb.box((L1 - L0, 0.5, 0.5), ((L0 + L1) / 2, s * 1.0, fz - 0.35), m["dark"])   # body rails


def _truck(raised: bool):
    m = St.mats()
    yel = P.material("truck_yellow")
    body = P.material("truck_tray", (0.55, 0.50, 0.45, 1), roughness=0.7, dust=1.0)
    mb = P.Mesh()
    r = T["wheel_r"]
    fx, rx = T["front_axle"], T["rear_axle"]
    for s in (-1, 1):
        mb.box((fx - rx + 4.5, 0.6, 1.0), ((fx + rx) / 2 + 0.4, s * 0.9, r + 0.1), yel)   # frame rails
        _wheel(mb, fx, s * 2.6, m)
        _wheel(mb, rx, s * 2.3, m, dual=True)
    mb.box((1.2, 4.4, 0.8), (rx, 0, r), m["dark"])                                 # rear axle housing
    # front module: radiator, upper deck with handrails, cab, access stair
    mb.box((1.6, 3.2, 2.6), (fx + 2.6, 0, r + 1.0), yel)
    mb.box((0.08, 2.6, 1.8), (fx + 3.42, 0, r + 1.0), m["dark"])                    # grille
    for s in (-1, 1):
        mb.box((0.1, 0.5, 0.3), (fx + 3.45, s * 1.2, r + 2.1), P.emissive("truck_light", (1.0, 0.95, 0.8, 1), 3.0))
    deck_z = r + 2.35
    mb.box((3.6, 7.0, 0.2), (fx + 1.6, 0, deck_z), yel)
    mb.box((2.6, 7.4, 0.5), (fx + 2.6, 0, r + 0.2), yel)                           # bumper
    St.handrail(mb, (fx + 3.3, -3.4, deck_z + 0.1), (fx + 3.3, 3.4, deck_z + 0.1), m["safety"], None, h=1.0)
    for s in (-1, 1):
        St.handrail(mb, (fx - 0.1, s * 3.4, deck_z + 0.1), (fx + 3.3, s * 3.4, deck_z + 0.1), m["safety"], None,
                    h=1.0)
    cx, cy = fx + 1.0, 2.0
    mb.box((2.0, 2.0, 2.0), (cx, cy, deck_z + 1.1), yel)
    mb.box((2.04, 2.04, 0.9), (cx, cy, deck_z + 1.4), m["window"])
    mb.boxm(P.along((fx + 3.6, -2.6, 0.6), (fx + 2.0, -1.0, deck_z), 0.9, 0.08), m["galv"])   # diagonal stair
    mb.box((1.6, 1.4, 1.8), (fx + 0.8, -1.4, deck_z + 0.95), yel)                  # air filter housing
    # tray on its hinge, raised for dumping
    hinge = (T["hinge_x"], 0, T["hinge_z"])
    tilt = math.radians(T["dump_deg"]) if raised else 0.0
    with mb.at(hinge, (0, -tilt, 0)):
        _tray(mb, m, body)
    for s in (-1, 1):                                                              # hoist cylinders
        a = (rx + 1.6, s * 1.1, r + 0.3)
        hx = T["hinge_x"] + 3.2 * math.cos(tilt)
        hz = T["hinge_z"] + 0.3 + 3.2 * math.sin(tilt)
        mb.pipe(a, (hx, s * 1.1, hz), 0.18, m["galv"], n=10, caps=True)
    return mb


def build(scene):
    import bpy
    col = P.collection("HaulTrucks")
    meshes = {False: _truck(False).obj("tmpl_truck", col).data,
              True: _truck(True).obj("tmpl_truck_dump", col).data}
    for o in [o for o in col.objects if o.name.startswith("tmpl_truck")]:
        bpy.data.objects.remove(o)
    for i, (x, y, z, yaw, pitch, raised) in enumerate(config.TRUCKS):
        o = bpy.data.objects.new(f"HaulTruck{i + 1}", meshes[raised])
        col.objects.link(o)
        o.location = (x, y, z)
        o.rotation_euler = (0.0, pitch, yaw)
