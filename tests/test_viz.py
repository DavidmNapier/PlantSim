from demo import config
from demo.sim.equipment import CycloneSettings
from demo.sim.wetplant import run
from demo.viz import colors


def test_ramp_direction():
    assert colors.badness("Al2O3", 2.15) == 0.0 and colors.badness("Al2O3", 2.45) == 1.0
    assert colors.badness("Fe", 61.2) == 0.0 and colors.badness("Fe", 60.4) == 1.0
    assert colors.rgba("Al2O3", 1.0)[:3] == config.RAMP[0]
    assert all(abs(a - b) < 1e-9 for a, b in zip(colors.rgba("Al2O3", 9.0), config.RAMP[2]))


def test_all_metrics_have_values():
    rec = run(minutes=10)[0]
    for m in config.METRICS:
        v = colors.metric_value(rec.product, m)
        assert v > 0 and len(colors.rgba(m, v)) == 4 and colors.fmt(m, v)


def test_live_settings_fn_applies_from_minute():
    def fn(minute):
        s = [CycloneSettings() for _ in range(5)]
        if minute >= 20:
            s[2].condition = "PULSING"
        return s
    recs = run(minutes=40, settings_fn=fn)
    assert all(r.conditions[2] == ("PULSING" if r.minute >= 20 else "NORMAL") for r in recs)
    assert any(r.alerts for r in recs if r.minute >= 20)
    assert not any(r.alerts for r in recs if r.minute < 20)
