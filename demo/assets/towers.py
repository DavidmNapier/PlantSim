"""Transfer towers at the belt junctions (config.TRANSFER_TOWERS): braced steel frames
with grating floors, clad head houses and external stairs."""
from __future__ import annotations

from demo import config
from demo.assets import _prims as P
from demo.assets import _steel as St


def build(scene):
    col = P.collection("TransferTowers")
    mb = P.Mesh()
    for name, (x, y, top, w, d, clad, stair_side) in config.TRANSFER_TOWERS.items():
        St.transfer_tower(mb, x, y, top, w, d, clad=clad, stair_side=stair_side)
    mb.obj("TransferTowers", col)
