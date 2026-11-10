import math

import pytest

from demo import config
from demo.sim.equipment import CycloneSettings, cyclone, cyclone_cluster, cyclone_yield, screen
from demo.sim.parcel import Parcel, blend, blend_value, default_q, split
from demo.sim.wetplant import run

CONSERVED = config.ANALYTES + ("lump_frac", "p80_mm")


def feed(dry=250.0, **q):
    base = dict(Fe=59.5, SiO2=5.6, Al2O3=3.2, P=0.085, LOI=5.4, lump_frac=0.35,
                p80_mm=10.0, fault_frac=0.0)
    base.update(q)
    return Parcel("T1", dry, 6.0, default_q(**base), source="BLK001")


def assert_balance(inp, outs, keys=CONSERVED):
    assert math.isclose(sum(o.dry_t for o in outs), inp.dry_t, rel_tol=1e-12)
    for k in keys:
        got = sum(o.dry_t * o.q[k] for o in outs)
        assert math.isclose(got, inp.dry_t * inp.q[k], rel_tol=1e-9, abs_tol=1e-9), k


def test_split_balances():
    p = feed()
    a, b = split(p, 0.3, {"Fe": 62.0}, 6.0, 6.0, "a", "b", 0.0)
    assert_balance(p, [a, b])
    assert a.parents == (p.id,) and b.parents == (p.id,)


def test_split_rejects_infeasible():
    with pytest.raises(ValueError):
        split(feed(), 0.9, {"Al2O3": 10.0}, 6, 6, "a", "b", 0)


def test_blend_weighting():
    a = feed(100.0, Fe=60.0)
    b = feed(300.0, Fe=64.0)
    b.moisture = 10.0
    m = blend([a, b], "pile", 0.0)
    assert m.dry_t == 400.0
    assert math.isclose(m.q["Fe"], 63.0)
    assert math.isclose(m.moisture, blend_value([a, b], "moisture"))
    assert math.isclose(m.water_t, a.water_t + b.water_t)


def test_split_then_blend_roundtrip():
    p = feed()
    a, b = split(p, 0.42, {"SiO2": 4.0, "Al2O3": 2.0}, 6.0, 6.0, "a", "b", 0.0)
    m = blend([a, b], "x", 0.0)
    for k in CONSERVED:
        assert math.isclose(m.q[k], p.q[k], rel_tol=1e-9)


def test_screen():
    lump, fines = screen(feed(), 0.0)
    assert_balance(feed(), [lump, fines])
    assert lump.q["lump_frac"] == 1.0 and abs(fines.q["lump_frac"]) < 1e-9
    assert math.isclose(fines.q["p80_mm"], config.SCREEN["fines_p80_mm"])


@pytest.mark.parametrize("cond", ["NORMAL", "ROPING", "PULSING"])
def test_cyclone_balance(cond):
    _, fines = screen(feed(), 0.0)
    for minute in (0.0, 1.5, 3.0, 4.5):
        uf, of = cyclone(fines, CycloneSettings(cond), "C1", minute)
        assert_balance(fines, [uf, of])
        assert all(v >= 0 for v in of.q.values())


def test_cyclone_conditions_match_table():
    _, fines = screen(feed(), 0.0)
    n_uf, _ = cyclone(fines, CycloneSettings("NORMAL"), "C1", 0.0)
    r_uf, _ = cyclone(fines, CycloneSettings("ROPING"), "C1", 0.0)
    p_uf, _ = cyclone(fines, CycloneSettings("PULSING"), "C1", 0.0)
    assert abs(n_uf.dry_t / fines.dry_t - 0.88) < 0.005
    assert abs(r_uf.dry_t / fines.dry_t - 0.78) < 0.005
    assert 2.0 < n_uf.q["Al2O3"] < 2.4 and p_uf.q["Al2O3"] > 2.8
    assert p_uf.moisture > n_uf.moisture > r_uf.moisture
    assert p_uf.q["fault_frac"] == 1.0 and n_uf.q["fault_frac"] == 0.0
    assert any(t.startswith("fault:C1:PULSING") for t in p_uf.tags)


def test_pulsing_swings():
    ys = [cyclone_yield(CycloneSettings("PULSING"), m) for m in range(12)]
    assert max(ys) - min(ys) > 0.05


def test_settings_shift_yield():
    lo = cyclone_yield(CycloneSettings(apex_mm=70.0), 0)
    hi = cyclone_yield(CycloneSettings(apex_mm=110.0), 0)
    assert hi > lo


def test_cluster_balance():
    _, fines = screen(feed(), 0.0)
    s = [CycloneSettings() for _ in range(5)]
    s[2].condition = "PULSING"
    prod, slimes, per = cyclone_cluster(fines, s, 0.0)
    assert_balance(fines, [prod, slimes], config.ANALYTES)
    assert len(per) == 5 and 0.15 < prod.q["fault_frac"] < 0.25


def test_run_end_to_end():
    recs = run(minutes=240.0)
    (r0, r1, _, _), (p0, p1, _, _) = config.FAULT_SCHEDULE
    dt = config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60
    assert abs(len(recs) - 240 / dt) <= 1
    for r in recs:
        assert_balance(r.feed, [r.lump, r.product, r.slimes], config.ANALYTES)
    normal = [r for r in recs if r.minute < r0]
    pulsing = [r for r in recs if p0 <= r.minute < p1]
    roping = [r for r in recs if r0 <= r.minute < r1]
    assert not any(r.alerts for r in normal)
    assert all(any("pulsing" in a for a in r.alerts) for r in pulsing)
    assert all(any("roping" in a for a in r.alerts) for r in roping)
    # tracing: fault material carries its tag downstream
    assert all(any("C3:PULSING" in t for t in r.product.tags) for r in pulsing)


def test_run_is_deterministic():
    a, b = run(minutes=30), run(minutes=30)
    assert [r.product.q["Fe"] for r in a] == [r.product.q["Fe"] for r in b]


def test_belt_filter_dewaters_without_changing_solids():
    r = run(minutes=120.0)
    for x in r:
        assert x.fines.moisture == 100.0 - config.CYCLONE["feed_solids_pct"]
        assert x.underflow.dry_t == x.product.dry_t and x.underflow.q == x.product.q
        assert x.underflow.moisture > 25.0 and 7.0 < x.product.moisture < 10.0
    normal = [x.product.moisture for x in r if x.conditions[2] == "NORMAL"]
    pulsing = [x.product.moisture for x in r if x.conditions[2] == "PULSING"]
    assert min(pulsing) > max(normal)
