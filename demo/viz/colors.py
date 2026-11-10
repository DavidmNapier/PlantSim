"""Metric values and colours. Pure Python (no bpy) so it is testable."""
from __future__ import annotations

from demo import config


def parcel_interval_min() -> float:
    return config.SOURCE["parcel_t"] / config.SOURCE["rate_tph"] * 60.0


def metric_value(parcel, metric: str) -> float:
    if metric == "tonnes":
        return parcel.dry_t / parcel_interval_min() * 60.0      # t/h
    if metric == "moisture":
        return parcel.moisture
    if metric == "size":
        return parcel.q["p80_mm"]
    return parcel.q[metric]


def badness(metric: str, value: float) -> float:
    """0 = good end of the ramp, 1 = bad end."""
    _, _, lo, hi, higher_better = config.METRICS[metric]
    f = min(1.0, max(0.0, (value - lo) / (hi - lo)))
    return 1.0 - f if higher_better else f


def rgba(metric: str, value: float):
    b = badness(metric, value)
    g, m, r = config.RAMP
    a, c, f = (g, m, b * 2) if b < 0.5 else (m, r, b * 2 - 1)
    return (*(a[i] + (c[i] - a[i]) * f for i in range(3)), 1.0)


def to_linear(rgba_srgb):
    """Display (sRGB) colour -> linear, for Blender colour attributes and materials."""
    def f(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (*(f(c) for c in rgba_srgb[:3]), rgba_srgb[3])


def fmt(metric: str, value: float) -> str:
    label, unit, *_ = config.METRICS[metric]
    nd = 0 if metric == "tonnes" else 3 if metric == "P" else 2 if metric == "Al2O3" else 1
    return f"{label} {value:,.{nd}f} {unit}"
