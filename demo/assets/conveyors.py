"""Conveyors and pipes that link the plant areas:
screen fines -> slurry pipe -> cyclone feed riser; screen lump -> lump belt -> lump pile
(untracked); product belt -> transfer belt -> stacker yard belt; BWR -> reclaim belt ->
load-out belt."""
from __future__ import annotations

from demo import config
from demo.assets import _prims as P
from demo.assets import belt

B = config.BELT
LINKS = {
    "LumpBelt": {**B, "start": (-45.5, -3.5, 2.2), "end": (-45.5, -31.0, 8.5), "n_lumps": 120,
                 "width": 1.0, "lump_r": 0.11},
    # lands on the yard belt tail, clear of the stacker's tripper car
    "TransferBelt": {**B, "start": (32.5, 0.6, 2.4),
                     "end": (config.YARD_GEOM["x0"] - config.YARD_GEOM["tail_back"] + 1.0, -29.0, 2.4)},
    "ReclaimBelt": {**B, "start": (12.0, 33.5, 1.6), "end": (126.0, 33.5, 1.6), "n_lumps": 300,
                    "idler_pitch": 3.0},
}
LUMP_PILE = {"xy": (-45.5, -40.0), "r": 11.0, "h": 8.0}


def build(scene):
    col = P.collection("Links")
    pipe = P.material("pipe", metallic=0.3, roughness=0.4)
    steel = P.material("steel", metallic=0.6, roughness=0.45)
    for name, cfg in LINKS.items():
        belt.build(scene, name, cfg)
    # glass slurry pipes (segments drawn inside by demo/viz/segments.py)
    glass = P.material("glass_pipe", (0.75, 0.85, 0.95, 0.15), roughness=0.1)
    water = P.material("filtrate", (0.35, 0.55, 0.85, 0.6), roughness=0.1)
    for name, pp in config.PIPES.items():
        for i, (a, b) in enumerate(zip(pp["pts"], pp["pts"][1:])):
            P.beam(f"{name}Pipe{i}", a, b, pp["r"], glass, col, verts=16)
            if pp.get("water"):
                P.beam(f"{name}Water{i}", a, b, pp["r"] * 0.7, water, col, verts=12)
    P.box("SlurryPump", (2.2, 1.6, 1.6), (-43.0, -4.5, 0.8), P.material("steel_dark"), col)
    P.box("UnderflowPump", (1.4, 1.2, 1.2), (3.6, 0.0, 1.8), P.material("steel_dark"), col)
    # transfer chutes
    P.box("Chute_ProductToTransfer", (1.6, 1.6, 1.6), (32.2, 0.0, 3.6), steel, col)
    tx = LINKS["TransferBelt"]["end"][0]
    P.box("Chute_TransferToYard", (1.6, 1.6, 1.0), (tx, -29.8, 2.2), steel, col)
    P.box("Chute_ReclaimToLoad", (1.6, 1.6, 1.2), (127.0, 33.8, 1.8), steel, col)
    x, y = LUMP_PILE["xy"]
    P.cone("LumpPile", 0.4, LUMP_PILE["r"], LUMP_PILE["h"], (x, y, LUMP_PILE["h"] / 2),
           P.material("lump_ore", (0.36, 0.17, 0.10, 1), roughness=0.95), col, verts=24)


def update(scene, frame, product_colour, reclaim_colour, ore):
    belt.update(scene, frame, "LumpBelt", LINKS["LumpBelt"], colour_fn=lambda f: ore)
    belt.update(scene, frame, "TransferBelt", LINKS["TransferBelt"], colour_fn=product_colour)
    belt.update(scene, frame, "ReclaimBelt", LINKS["ReclaimBelt"], colour_fn=reclaim_colour)
