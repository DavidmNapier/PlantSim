"""Parcel record plus the two primitive operations: split and blend.

Every equipment step is built from these, so mass and analyte balance
holds everywhere by construction.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from demo import config

_ids = itertools.count(1)


def new_id(prefix: str = "P") -> str:
    return f"{prefix}{next(_ids):05d}"


def reset_ids() -> None:
    global _ids
    _ids = itertools.count(1)


@dataclass
class Parcel:
    id: str
    dry_t: float
    moisture: float                       # % of wet mass
    q: dict                               # BLEND_FIELDS -> value
    location: str = "source"
    source: str = ""                      # blast block id
    parents: tuple = ()                   # parcel ids this came from
    stamps: dict = field(default_factory=dict)  # stage -> sim minute
    tags: frozenset = frozenset()         # e.g. "fault:C3:PULSING"
    contrib: dict = field(default_factory=dict)  # product minute -> dry t (traceability ledger)

    @property
    def wet_t(self) -> float:
        return self.dry_t / (1.0 - self.moisture / 100.0)

    @property
    def water_t(self) -> float:
        return self.wet_t - self.dry_t

    def moved(self, location: str, minute: float) -> "Parcel":
        """Same material, new location and timestamp (conveyor, crusher, scrubber)."""
        stamps = dict(self.stamps)
        stamps[location] = minute
        return Parcel(self.id, self.dry_t, self.moisture, dict(self.q), location,
                      self.source, self.parents, stamps, self.tags, dict(self.contrib))


def split(p: Parcel, mass_frac: float, q_a: dict, moisture_a: float, moisture_b: float,
          loc_a: str, loc_b: str, minute: float, tags_a=frozenset(), tags_b=frozenset()):
    """Split p into (a, b). a gets mass_frac of the dry tonnes and the qualities q_a for
    the fields given. b gets the remainder so that every field balances exactly."""
    if not 0.0 < mass_frac < 1.0:
        raise ValueError("mass_frac must be in (0, 1)")
    ma = p.dry_t * mass_frac
    mb = p.dry_t - ma
    qa, qb = {}, {}
    for k, g in p.q.items():
        ga = q_a.get(k, g)
        gb = (p.dry_t * g - ma * ga) / mb
        if gb < -1e-9:
            raise ValueError(f"infeasible split for {k}: remainder grade {gb:.4f}")
        qa[k], qb[k] = ga, max(gb, 0.0)
    stamps = dict(p.stamps)
    a = Parcel(new_id(), ma, moisture_a, qa, loc_a, p.source, (p.id,),
               {**stamps, loc_a: minute}, p.tags | tags_a,
               {k: v * mass_frac for k, v in p.contrib.items()})
    b = Parcel(new_id(), mb, moisture_b, qb, loc_b, p.source, (p.id,),
               {**stamps, loc_b: minute}, p.tags | tags_b,
               {k: v * (1.0 - mass_frac) for k, v in p.contrib.items()})
    return a, b


def divide(p: Parcel, fracs, locs, minute: float):
    """Same-quality pieces of p with the given mass fractions (summing to 1)."""
    out, rest, left = [], p, 1.0
    for f, loc in zip(fracs[:-1], locs[:-1]):
        piece, rest = split(rest, f / left, dict(rest.q), rest.moisture, rest.moisture,
                            loc, locs[-1], minute)
        out.append(piece)
        left -= f
    out.append(rest if out else rest.moved(locs[-1], minute))
    return out


def blend(parcels, location: str, minute: float) -> Parcel:
    """Blend parcels: qualities weighted by dry tonnes, moisture by wet tonnes."""
    parcels = list(parcels)
    if not parcels:
        raise ValueError("nothing to blend")
    dry = sum(p.dry_t for p in parcels)
    wet = sum(p.wet_t for p in parcels)
    keys = parcels[0].q.keys()
    q = {k: sum(p.dry_t * p.q[k] for p in parcels) / dry for k in keys}
    moisture = 100.0 * (wet - dry) / wet
    sources = sorted({p.source for p in parcels})
    tags = frozenset().union(*(p.tags for p in parcels))
    contrib = {}
    for p in parcels:
        for k, v in p.contrib.items():
            contrib[k] = contrib.get(k, 0.0) + v
    return Parcel(new_id("B"), dry, moisture, q, location, "+".join(sources),
                  tuple(p.id for p in parcels), {location: minute}, tags, contrib)


def blend_value(parcels, key: str) -> float:
    """Dry-weighted value of one field (moisture uses wet weighting)."""
    parcels = list(parcels)
    if key == "moisture":
        wet = sum(p.wet_t for p in parcels)
        return 100.0 * sum(p.water_t for p in parcels) / wet
    dry = sum(p.dry_t for p in parcels)
    return sum(p.dry_t * p.q[key] for p in parcels) / dry


def default_q(**overrides) -> dict:
    q = {k: 0.0 for k in config.BLEND_FIELDS}
    q.update(overrides)
    return q
