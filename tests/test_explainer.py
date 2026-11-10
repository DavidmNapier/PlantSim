from demo import config
from demo.explainer import model as M

E = config.EXPLAINER


def test_partition_is_a_rising_curve_between_bypass_and_one():
    d50 = M.d50(E["apex_mm"], E["feed_solids_pct"], E["pressure_kpa"], "NORMAL")
    ps = [M.partition(d, 2.65, d50, "NORMAL") for d in (1, 10, 30, 45, 100, 300, 1000)]
    assert ps == sorted(ps)
    assert abs(ps[0] - E["water_rf"]) < 0.01 and ps[-1] > 0.99
    assert abs(M.partition(d50, 2.65, d50, "NORMAL") - (E["water_rf"] + (1 - E["water_rf"]) * 0.5)) < 1e-6


def test_hematite_separates_finer_than_silica():
    d50 = 45.0
    assert M.d50_for(5.0, d50) < 0.7 * d50
    assert M.partition(30, 5.0, d50, "NORMAL") > M.partition(30, 2.65, d50, "NORMAL") + 0.2


def test_roping_sends_coarse_to_overflow_and_pulsing_bypasses_slimes():
    n = M.d50(90, 35, 120, "NORMAL")
    r = M.d50(90, 35, 120, "ROPING")
    assert M.partition(300, 5.0, r, "ROPING") < 0.7 < M.partition(300, 5.0, n, "NORMAL")
    peak = E["pulse_period_s"] / 4                     # surge maximum
    assert M.partition(5, 2.6, n, "PULSING", peak) > M.partition(5, 2.6, n, "NORMAL") + 0.2


def test_auto_mode_from_settings():
    assert M.auto_mode(90, 35, 120) == "NORMAL"
    assert M.auto_mode(70, 45, 120) == "ROPING"
    assert M.auto_mode(90, 35, 50) == "PULSING"


def test_particles_route_to_their_outlets():
    parts = M.particles()
    assert len(parts) == sum(c[5] for c in E["classes"])
    d50 = lambda t: 45.0  # noqa: E731
    T = E["cycle_s"]
    for i, part in enumerate(parts[::37]):
        for t in (0.0, 0.7 * T, 1.3 * T):
            x, y, z, uf = M.position(i, part, t, "NORMAL", d50)
            assert -2.0 < z - E["z0"] < M.TOP + E["vf_top"] + 0.5
    # end of trip: underflow particles below the apex, overflow ones up at the outlet
    for i, part in enumerate(parts[::23]):
        c, d, rho, phase, lane, speed = part
        t_end = (0.99 - phase) * T / speed + T / speed * 2
        x, y, z, uf = M.position(i, part, t_end, "NORMAL", d50)
        assert (z < E["z0"]) if uf else (z > E["z0"] + M.TOP)
