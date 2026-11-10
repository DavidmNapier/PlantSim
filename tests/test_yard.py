import math

import pytest

from demo import config
from demo.sim.parcel import Parcel, default_q, divide
from demo.sim.stockyard import _coverage, build_pile, run_yard, stacker_pos
from demo.sim.wetplant import run


@pytest.fixture(scope="module")
def recs():
    return run(minutes=config.SIM_MINUTES)


@pytest.fixture(scope="module")
def yard(recs):
    return run_yard(recs)


def _sum(ps, key=None):
    return sum(p.dry_t * (p.q[key] if key else 1.0) for p in ps)


def test_divide_balances_and_keeps_quality():
    p = Parcel("X", 90.0, 8.0, default_q(Fe=61.0, Al2O3=2.3), contrib={4.0: 90.0})
    parts = divide(p, [0.2, 0.5, 0.3], ["a", "b", "c"], 0.0)
    assert math.isclose(_sum(parts), 90.0)
    assert all(math.isclose(x.q["Fe"], 61.0) for x in parts)
    assert math.isclose(sum(sum(x.contrib.values()) for x in parts), 90.0)


def test_stacker_shuttles():
    P = config.STOCKPILE["pass_min"]
    assert stacker_pos(0)[0] == 0.0 and math.isclose(stacker_pos(P * 0.999)[0], 1.0, abs_tol=1e-2)
    assert stacker_pos(P)[1] == 1 and math.isclose(stacker_pos(P)[0], 1.0)
    cov = _coverage(P - 1, P + 1)                 # straddles the turn at the pile end
    assert math.isclose(sum(f for *_, f in cov), 1.0)
    assert {k for k, *_ in cov} == {0, 1}


def test_pile_mass_balance(recs):
    pile = build_pile(recs)
    stacked = [r.product for r in recs]
    assert math.isclose(pile.tonnes(), _sum(stacked), rel_tol=1e-9)
    cells = [p for ps in pile.cells.values() for p in ps]
    for k in config.ANALYTES:
        assert math.isclose(_sum(cells, k), _sum(stacked, k), rel_tol=1e-9)
    assert pile.layers == math.ceil(config.SIM_MINUTES / config.STOCKPILE["pass_min"])


def test_reclaim_and_train_balance(recs, yard):
    stacked = [r.product for r in recs]
    rec = [p for *_, p in yard.reclaimed]
    out = [w.parcel for w in yard.wagons] + yard.leftover
    for ps in (rec, out):
        assert math.isclose(_sum(ps), _sum(stacked), rel_tol=1e-9)
        for k in config.ANALYTES:
            assert math.isclose(_sum(ps, k), _sum(stacked, k), rel_tol=1e-9)
    assert all(math.isclose(w.parcel.dry_t, config.TRAIN["payload_t"]) for w in yard.wagons)
    assert len(yard.wagons) == config.TRAIN["wagons"]


def test_contrib_ledger_traces_every_tonne(yard):
    for w in yard.wagons:
        assert math.isclose(sum(w.parcel.contrib.values()), w.parcel.dry_t, rel_tol=1e-9)


def test_reclaimer_blends_out_variability(recs, yard):
    v = yard.variability(recs, "Al2O3")
    assert v["wagons"] < v["stacked"] * 0.6


def test_fault_is_localised_to_some_wagons(recs, yard):
    flagged = [w for w in yard.wagons if w.flagged]
    assert 0 < len(flagged) < len(yard.wagons)
    p0, p1 = config.FAULT_SCHEDULE[1][:2]
    for w in flagged:
        tr = w.trace(recs)
        assert tr and all(t > 0 for _, t, _ in tr)
        assert any(p0 <= m < p1 and "C3:PULSING" in bad for m, _, bad in tr)
    for w in yard.wagons:
        if not w.flagged:
            assert w.fault_t / w.parcel.dry_t <= config.TRAIN["flag_fault_frac"]
    # faulty tonnes over all wagons + leftover cannot exceed C3 pulsing product
    pulsing_t = sum(uf.dry_t for r in recs if p0 <= r.minute < p1
                    for (_, _, uf), c in zip(r.per_cyclone, r.conditions) if c == "PULSING")
    assert sum(w.fault_t for w in yard.wagons) <= pulsing_t + 1e-6


def test_heatmap_grid_shape(yard):
    g = yard.pile.grid("Al2O3")
    assert len(g) == yard.pile.layers and all(len(r) == config.STOCKPILE["slices"] for r in g)


def test_bench_area_weights_cover_the_section():
    """Bench areas of a 3-layer triangle add up to the whole triangle, top bench smallest."""
    import math as _m
    tan = _m.tan(_m.radians(config.YARD_GEOM["repose_deg"]))

    def tri(H, a, b):
        a, b = min(max(a, 0), H), min(max(b, 0), H)
        return 2 * (H / tan) * ((b - a) - (b * b - a * a) / (2 * H)) if b > a else 0.0
    H = 9.0
    benches = [tri(H, H * (2 - b) / 3, H * (3 - b) / 3) for b in range(3)]
    assert abs(sum(benches) - H * H / tan) < 1e-9
    assert benches[0] < benches[1] < benches[2]
