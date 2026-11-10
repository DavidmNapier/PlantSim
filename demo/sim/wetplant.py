"""Phase-1 pipeline: crusher -> screen -> cyclone cluster -> product belt.
Precomputed once per settings change. The Blender side only reads the records."""
from __future__ import annotations

from dataclasses import dataclass, field

from demo import config
from demo.sim.equipment import CycloneSettings, belt_filter, cyclone_cluster, screen
from demo.sim.parcel import reset_ids
from demo.sim.source import SimulatedSource


@dataclass
class StepRecord:
    minute: float
    feed: object
    lump: object
    product: object
    slimes: object
    per_cyclone: list
    conditions: list = field(default_factory=list)
    alerts: list = field(default_factory=list)
    fines: object = None        # cyclone feed slurry
    underflow: object = None    # underflow slurry to the belt filter (product = filter cake)


def settings_at(minute: float, base: list, schedule) -> list:
    out = [CycloneSettings(**vars(s)) for s in base]
    for start, end, idx, cond in schedule:
        if start <= minute < end:
            out[idx].condition = cond
    return out


def alerts_for(rec: StepRecord) -> list:
    a = []
    p = rec.product
    if p.q["Al2O3"] > config.TARGETS["Al2O3"] + config.ALERT_TOL["Al2O3"]:
        a.append(f"Product Al2O3 {p.q['Al2O3']:.2f}% above target")
    if p.q["SiO2"] > config.TARGETS["SiO2"] + config.ALERT_TOL["SiO2"]:
        a.append(f"Product SiO2 {p.q['SiO2']:.2f}% above target")
    nominal = config.CYCLONE["conditions"]["NORMAL"]["yield"]
    al_lim = config.TARGETS["Al2O3"] + config.ALERT_TOL["Al2O3"]
    for name, y, uf in rec.per_cyclone:
        if y < nominal - config.ALERT_TOL["yield"]:
            a.append(f"{name} yield {y:.0%}: possible roping")
        if uf.q["Al2O3"] > al_lim:
            a.append(f"{name} underflow Al2O3 {uf.q['Al2O3']:.2f}%: slimes bypass (pulsing)")
    return a


def run(minutes: float = config.SIM_MINUTES, seed: int = config.SEED,
        base_settings: list | None = None, schedule=config.FAULT_SCHEDULE, source=None,
        settings_fn=None):
    """settings_fn(minute) -> list[CycloneSettings] overrides base_settings/schedule
    (used for live presenter changes)."""
    reset_ids()
    base = base_settings or [CycloneSettings() for _ in range(config.CYCLONE["count"])]
    src = source or SimulatedSource(seed)
    records = []
    for feed in src.parcels(minutes):
        t = feed.stamps["crusher"]
        lump, fines = screen(feed, t)
        settings = settings_fn(t) if settings_fn else settings_at(t, base, schedule)
        prod, slimes, per = cyclone_cluster(fines, settings, t)
        cake = belt_filter(prod, t)
        rec = StepRecord(t, feed, lump, cake, slimes, per, [s.condition for s in settings],
                         fines=fines, underflow=prod)
        rec.alerts = alerts_for(rec)
        records.append(rec)
    return records
