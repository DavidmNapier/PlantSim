"""Screens and desliming cyclones, as split/blend operations on parcels."""
from __future__ import annotations

import math
from dataclasses import dataclass

from demo import config
from demo.sim.parcel import Parcel, blend, split


def screen(p: Parcel, minute: float, cfg: dict = config.SCREEN):
    """Split into (lump, fines) by the parcel's lump fraction."""
    lf = p.q["lump_frac"]
    # choose lump p80 so the fines remainder lands on the configured fines p80
    lump_p80 = (p.q["p80_mm"] - (1 - lf) * cfg["fines_p80_mm"]) / lf
    slurry = 100.0 - config.CYCLONE["feed_solids_pct"]      # wet screening: fines leave as slurry
    return split(p, lf, {"lump_frac": 1.0, "p80_mm": lump_p80},
                 p.moisture, slurry, "lump", "fines", minute)


@dataclass
class CycloneSettings:
    condition: str = "NORMAL"
    apex_mm: float = config.CYCLONE["apex_mm"]
    feed_solids_pct: float = config.CYCLONE["feed_solids_pct"]
    pressure_kpa: float = config.CYCLONE["pressure_kpa"]


def cyclone_yield(s: CycloneSettings, minute: float, cfg: dict = config.CYCLONE) -> float:
    c = cfg["conditions"][s.condition]
    y = c["yield"]
    if c["yield_amp"]:
        y += c["yield_amp"] * math.sin(2 * math.pi * minute / cfg["pulse_period_min"])
    y += cfg["dY_apex_per_mm"] * (s.apex_mm - cfg["apex_mm"])
    y += cfg["dY_solids_per_pct"] * (s.feed_solids_pct - cfg["feed_solids_pct"])
    y += cfg["dY_pressure_per_kpa"] * (s.pressure_kpa - cfg["pressure_kpa"])
    return min(0.97, max(0.55, y))


def cyclone(p: Parcel, s: CycloneSettings, name: str, minute: float, cfg: dict = config.CYCLONE):
    """Split fines into (product underflow, slimes overflow).

    Each analyte's share to product is d = min(1, ratio * yield), so product grade is
    feed * d / yield and the slimes carry the rest. Balance holds by construction."""
    c = cfg["conditions"][s.condition]
    y = cyclone_yield(s, minute, cfg)
    q_prod = {}
    for k in config.ANALYTES:
        d = min(1.0, c["ratio"][k] * y)
        q_prod[k] = p.q[k] * d / y
    faulty = s.condition != "NORMAL"
    if faulty:  # label the material passing a faulty cyclone (a label, not a conserved quantity)
        p = p.moved(p.location, minute)
        p.q["fault_frac"] = 1.0
    tags = frozenset({f"fault:{name}:{s.condition}"}) if faulty else frozenset()
    moist = cfg["uf_moisture"] + 4.0 * c["moist_delta"]
    return split(p, y, q_prod, moist, cfg["slimes_moisture"],
                 f"{name}.uf", f"{name}.of", minute, tags_a=tags, tags_b=tags)


def belt_filter(p: Parcel, minute: float, cfg: dict = config.FILTER) -> Parcel:
    """Dewater underflow slurry to filter cake. Dry tonnes and grades unchanged; wetter
    underflow (e.g. slimes from a pulsing cyclone) gives a wetter cake."""
    cake = p.moved("filter", minute)
    cake.moisture = cfg["cake_moisture"] + cfg["k"] * (p.moisture - cfg["uf_ref"])
    return cake


def cyclone_cluster(p: Parcel, settings: list, minute: float, cfg: dict = config.CYCLONE):
    """Feed split equally across cyclones. Returns (product, slimes, per_cyclone) where
    per_cyclone is a list of (name, yield, product_parcel)."""
    n = len(settings)
    parts, rest = [], p
    for i in range(n - 1):     # carve equal shares without changing quality
        share, rest = split(rest, 1.0 / (n - i), dict(rest.q), rest.moisture, rest.moisture,
                            "manifold", "manifold", minute)
        parts.append(share)
    parts.append(rest)
    prods, slimes, per = [], [], []
    for i, (part, s) in enumerate(zip(parts, settings)):
        name = f"C{i + 1}"
        uf, of = cyclone(part, s, name, minute, cfg)
        prods.append(uf)
        slimes.append(of)
        per.append((name, uf.dry_t / part.dry_t, uf))
    return blend(prods, "product", minute), blend(slimes, "tailings", minute), per
