"""Where parcels come from. SimulatedSource is used for the demo.
A live source (Ignition/PI/Databricks) can implement the same interface later."""
from __future__ import annotations

import random

from demo import config
from demo.sim.parcel import Parcel, default_q, new_id


class ParcelSource:
    def parcels(self, minutes: float):
        """Yield crusher-discharge parcels in time order up to `minutes`."""
        raise NotImplementedError


class SimulatedSource(ParcelSource):
    def __init__(self, seed: int = config.SEED, cfg: dict = config.SOURCE):
        self.rng = random.Random(seed)
        self.cfg = cfg

    def _block_grades(self):
        c = self.cfg
        return {k: self.rng.gauss(c["grade_mean"][k], c["grade_sd"][k]) for k in config.ANALYTES}

    def parcels(self, minutes: float):
        c = self.cfg
        dt = c["parcel_t"] / c["rate_tph"] * 60.0
        t, block_left, block_n, grades = 0.0, 0.0, 0, {}
        while t < minutes:
            if block_left <= 0:
                block_n += 1
                block_left = c["block_t"]
                grades = self._block_grades()
            q = default_q(**{k: max(0.0, g + self.rng.gauss(0, 0.15 * config.SOURCE["grade_sd"][k]))
                             for k, g in grades.items()},
                          lump_frac=c["lump_frac"], p80_mm=c["p80_mm"], fault_frac=0.0)
            yield Parcel(new_id("C"), c["parcel_t"], c["moisture"], q, "crusher",
                         f"BLK{block_n:03d}", (), {"crusher": t})
            block_left -= c["parcel_t"]
            t += dt
