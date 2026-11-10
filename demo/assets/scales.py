"""The three tracking points: belt scale + analyser frames over the crusher-discharge
belt (TP1) and the product belt (TP2), and the wagon weighbridge under the chute (TP3).
Each has an indicator light that flashes when a parcel (TP1/TP2) or wagon (TP3) is measured."""
from __future__ import annotations

from demo import config
from demo.assets import _prims as P

U = config.UPSTREAM


def _led(name):
    m = P.material(name, (0.1, 1.0, 0.4, 1), roughness=0.3)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (0.1, 1.0, 0.4, 1)
    b.inputs["Emission Strength"].default_value = 0.0
    return m


def _belt_z(cfg, x):
    (x0, _, z0), (x1, _, z1) = cfg["start"], cfg["end"]
    return z0 + (z1 - z0) * (x - x0) / (x1 - x0)


def _frame(name, x, y, z, width, col, led):
    safety = P.material("safety")
    for s in (-1, 1):
        P.beam(f"{name}_Post{s}", (x, y + s * (width / 2 + 0.5), 0), (x, y + s * (width / 2 + 0.5), z + 1.6),
               0.12, safety, col, square=True)
    P.box(f"{name}_Beam", (0.4, width + 1.4, 0.3), (x, y, z + 1.6), safety, col)
    P.box(f"{name}_Analyser", (1.2, 1.0, 0.8), (x, y, z + 2.15), P.material("analyser", (0.9, 0.9, 0.92, 1)), col)
    P.box(f"{name}_Idlers", (1.0, width, 0.12), (x, y, z + 0.05), P.material("steel_dark"), col)
    P.cylinder(f"{name}_Led", 0.18, 0.25, (x + 0.65, y, z + 2.3), led, col, rot=(0, 1.5708, 0), verts=10)


def build(scene):
    from demo.assets import crusher
    col = P.collection("TrackingPoints")
    tp1, tp2, tp3 = _led("led_tp1"), _led("led_tp2"), _led("led_tp3")
    cb = crusher.CRUSHER_BELT
    _frame("TP1", U["tp1_x"], 0.0, _belt_z(cb, U["tp1_x"]), cb["width"], col, tp1)
    _frame("TP2", U["tp2_x"], 0.0, _belt_z(config.BELT, U["tp2_x"]), config.BELT["width"], col, tp2)
    LG = config.LOADOUT_GEOM
    conc = P.material("concrete", (0.62, 0.60, 0.56, 1), roughness=0.9)
    P.box("TP3_Weighbridge", (14.0, 4.5, 0.12), (U["tp3_x"], LG["track_y"], 0.06), conc, col)
    P.box("TP3_Hut", (3.0, 2.5, 2.6), (U["tp3_x"] - 9.0, LG["track_y"] - 5.0, 1.3),
          P.material("analyser", (0.9, 0.9, 0.92, 1)), col)
    P.cylinder("TP3_Led", 0.25, 0.3, (U["tp3_x"] - 9.0, LG["track_y"] - 6.3, 2.2), tp3, col,
               rot=(1.5708, 0, 0), verts=10)


def _pulse(phase):
    """Bright for the first 20% of each cycle."""
    return 8.0 if phase % 1.0 < 0.2 else 0.0


def update(scene, minute: float, wagon_phase: float):
    import bpy
    dt = config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60.0
    stacking = minute < config.SIM_MINUTES
    for name, on in (("led_tp1", stacking), ("led_tp2", stacking)):
        m = bpy.data.materials[name]
        m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = \
            _pulse(minute / dt) if on else 0.0
    m = bpy.data.materials["led_tp3"]
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = \
        _pulse(wagon_phase) if wagon_phase >= 0 else 0.0
