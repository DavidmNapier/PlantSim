"""Chevron stockpile, bucket wheel reclaimer and train load-out.

Stacking: the stacker shuttles along the pile, one chevron layer per pass. Each
product parcel is spread over the pile slices the stacker crossed while it arrived.
Reclaiming: the BWR takes one full cross-section slice per cut, blending every layer.
Load-out: reclaimed parcels queue through the bin, and each wagon takes `payload_t` off
the front. Every step uses split/blend, so tonnes and analytes balance, and the
contrib ledger (product minute -> t) traces each wagon to the minutes it came from.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

from demo import config
from demo.sim.parcel import Parcel, blend, divide, split

S = config.STOCKPILE
T = config.TRAIN


# ------------------------------------------------------------------ stacker
def stacker_pos(minute: float, cfg: dict = S):
    """(position 0..1 along the pile, pass index). Even passes go 0->1, odd 1->0."""
    k = int(minute // cfg["pass_min"])
    f = (minute - k * cfg["pass_min"]) / cfg["pass_min"]
    return (f if k % 2 == 0 else 1.0 - f), k


def laid_time(layer: int, j: int, cfg: dict = S) -> float:
    """Minute the stacker passes over the centre of slice j during pass `layer`."""
    f = (j + 0.5) / cfg["slices"]
    return (layer + (f if layer % 2 == 0 else 1.0 - f)) * cfg["pass_min"]


def _coverage(t0: float, t1: float, cfg: dict = S):
    """[(layer, slice, fraction of the interval)] for stacker travel over [t0, t1)."""
    n, out = cfg["slices"], {}
    total = t1 - t0
    t = t0
    while t < t1 - 1e-12:
        k = int(t // cfg["pass_min"])
        te = min(t1, (k + 1) * cfg["pass_min"])
        x0, _ = stacker_pos(t, cfg)
        x1 = x0 + (te - t) / cfg["pass_min"] * (1 if k % 2 == 0 else -1)
        lo, hi = sorted((x0, x1))
        for j in range(max(0, int(lo * n)), min(n, math.ceil(hi * n))):
            ov = min(hi, (j + 1) / n) - max(lo, j / n)
            if ov > 1e-12:
                key = (k, j)
                out[key] = out.get(key, 0.0) + ov / (hi - lo) * (te - t) / total
        t = te
    return [(k, j, f) for (k, j), f in sorted(out.items())]


@dataclass
class Pile:
    slices: int = S["slices"]
    cells: dict = field(default_factory=dict)       # (layer, slice) -> [Parcel]

    def stack(self, p: Parcel, t0: float, t1: float):
        cov = _coverage(t0, t1)
        locs = [f"pile:L{k}:S{j}" for k, j, _ in cov]
        for (k, j, _), piece in zip(cov, divide(p, [f for *_, f in cov], locs, t0)):
            piece.stamps["laid"] = min(t1, max(t0, laid_time(k, j)))
            self.cells.setdefault((k, j), []).append(piece)

    @property
    def layers(self) -> int:
        return 1 + max((k for k, _ in self.cells), default=-1)

    def cell(self, layer: int, j: int):
        ps = self.cells.get((layer, j))
        return blend(ps, f"pile:L{layer}:S{j}", 0.0) if ps else None

    def slice_parcels(self, j: int):
        return [p for (k, jj), ps in sorted(self.cells.items()) if jj == j for p in ps]

    def tonnes(self) -> float:
        return sum(p.dry_t for ps in self.cells.values() for p in ps)

    def grid(self, metric: str):
        """layers x slices of metric value (None where empty), used by the heatmap."""
        from demo.viz.colors import metric_value   # pure python, no bpy
        out = []
        for k in range(self.layers):
            row = []
            for j in range(self.slices):
                c = self.cell(k, j)
                row.append(metric_value(c, metric) if c else None)
            out.append(row)
        return out


def build_pile(records) -> Pile:
    pile = Pile()
    dt = config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60.0
    for r in records:
        p = r.product.moved("stacker", r.minute)
        p.contrib = {r.minute: p.dry_t}
        pile.stack(p, r.minute, r.minute + dt)
    return pile


# ------------------------------------------------------------------ reclaimer
def reclaim(pile: Pile, start: float = S["reclaim_start_min"], cfg: dict = S):
    """One blended parcel per slice, slice 0 first. Returns [(minute, slice, parcel)]."""
    out, t = [], start
    for j in range(pile.slices):
        ps = pile.slice_parcels(j)
        if not ps:
            continue
        p = blend(ps, "bwr", t)
        p.stamps["bwr"] = t
        out.append((t, j, p))
        t += p.dry_t / cfg["reclaim_tph"] * 60.0
    return out


# ------------------------------------------------------------------ load-out
@dataclass
class Wagon:
    index: int
    minute: float
    parcel: Parcel
    flagged: bool
    slices: list        # pile slices that fed this wagon

    fault_t: float = 0.0  # tonnes that passed a cyclone in a FLAG_CONDITIONS state

    def trace(self, records):
        """[(product minute, faulty tonnes in this wagon, ["C3:PULSING", ...])]."""
        by_min = {r.minute: r for r in records}
        out = []
        for m, t in sorted(self.parcel.contrib.items()):
            r = by_min.get(m)
            if r is None:
                continue
            bad, share = [], 0.0
            for (name, _, uf), c in zip(r.per_cyclone, r.conditions):
                if c != "NORMAL":
                    bad.append(f"{name}:{c}")
                    share += uf.dry_t / r.product.dry_t
            if bad:
                out.append((m, t * share, bad))
        return out


def load_train(reclaimed, cfg: dict = T):
    """FIFO through the bin. Returns (wagons, leftover parcels still in the bin/pile)."""
    queue = [(m, j, p) for m, j, p in reclaimed]
    wagons = []
    for i in range(cfg["wagons"]):
        need, take, srcs, minute = cfg["payload_t"], [], [], None
        while need > 1e-9 and queue:
            m, j, p = queue.pop(0)
            minute = m if minute is None else minute
            if p.dry_t <= need + 1e-9:
                take.append(p)
                need -= p.dry_t
            else:
                a, b = split(p, need / p.dry_t, dict(p.q), p.moisture, p.moisture,
                             f"wagon{i + 1}", "bin", m)
                take.append(a)
                queue.insert(0, (m, j, b))
                need = 0.0
            srcs.append(j)
        if not take or need > 1e-6:       # not enough left for a full wagon
            queue[:0] = [(minute, s, p) for s, p in zip(srcs, take)]
            break
        w = blend(take, f"wagon{i + 1}", minute)
        wagons.append(Wagon(i + 1, minute, w, False, sorted(set(srcs))))
    return wagons, [p for *_, p in queue]


# ------------------------------------------------------------------ whole yard
@dataclass
class YardResult:
    pile: Pile
    reclaimed: list
    wagons: list
    leftover: list

    def variability(self, records, metric="Al2O3"):
        """Std dev of the metric: stacked product parcels vs reclaimed cuts vs wagons."""
        from demo.viz.colors import metric_value

        def sd(ps):
            v = [metric_value(p, metric) for p in ps]
            return statistics.pstdev(v) if len(v) > 1 else 0.0
        return {"stacked": sd(r.product for r in records),
                "reclaimed": sd(p for *_, p in self.reclaimed),
                "wagons": sd(w.parcel for w in self.wagons)}


def run_yard(records) -> YardResult:
    pile = build_pile(records)
    rec = reclaim(pile)
    wagons, left = load_train(rec)
    flag = config.TRAIN["flag_conditions"]
    for w in wagons:
        w.fault_t = sum(t for _, t, bad in w.trace(records)
                        if any(b.split(":")[1] in flag for b in bad))
        w.flagged = w.fault_t / w.parcel.dry_t > config.TRAIN["flag_fault_frac"]
    return YardResult(pile, rec, wagons, left)
