"""Hydrocyclone classification model and particle paths for the explainer. Pure Python.

Classification: a Plitt-style partition curve. The share of particles of size d and
density rho reporting to the underflow is
    P(d) = Rf + (1 - Rf) * (1 - exp(-0.693 * (d / d50_rho) ** m))
where Rf is the fraction of feed water short-circuiting to the underflow (it carries
fines with it) and d50_rho is the cut size for that density. Heavier hematite separates
at a finer size than silica:  d50_rho = d50 * sqrt((2.65 - 1) / (rho - 1)).

Modes:
- NORMAL: stable air core, umbrella spray at the apex.
- ROPING: the apex cannot pass the underflow solids; the air core collapses, the
  underflow leaves as a rope and coarse particles are forced into the overflow.
- PULSING: unstable feed; the cut size and spray surge, slimes bypass to the underflow.
"""
from __future__ import annotations

import math

from demo import config

E = config.EXPLAINER
MODES = ("NORMAL", "ROPING", "PULSING")


# ------------------------------------------------------------------ settings -> state
def load_ratio(apex_mm, solids_pct):
    """Underflow solids load relative to what the apex can pass (1 = nominal)."""
    return (solids_pct / E["feed_solids_pct"]) * (E["apex_mm"] / apex_mm) ** 2


def auto_mode(apex_mm, solids_pct, pressure_kpa):
    if load_ratio(apex_mm, solids_pct) > E["rope_load"]:
        return "ROPING"
    if pressure_kpa < E["pulse_kpa"]:
        return "PULSING"
    return "NORMAL"


def surge(t):
    """0..1 surge level for pulsing (two-beat pulse)."""
    s = math.sin(2 * math.pi * t / E["pulse_period_s"])
    return max(0.0, s) ** 2


def d50(apex_mm, solids_pct, pressure_kpa, mode, t=0.0):
    """Silica-equivalent cut size, um (Plitt-style sensitivities)."""
    d = E["d50_um"]
    d *= (apex_mm / E["apex_mm"]) ** -0.71
    d *= (pressure_kpa / E["pressure_kpa"]) ** -0.25
    d *= math.exp(0.063 * 0.5 * (solids_pct - E["feed_solids_pct"]))
    if mode == "ROPING":
        d *= 1.8
    elif mode == "PULSING":
        d *= 1.0 + 0.6 * surge(t)
    return d


def bypass(mode, t=0.0):
    """Rf: fraction of feed water (and fines with it) short-circuiting to the underflow."""
    if mode == "ROPING":
        return 0.04
    if mode == "PULSING":
        return E["water_rf"] + 0.35 * surge(t)
    return E["water_rf"]


def d50_for(rho, d50_silica):
    return d50_silica * math.sqrt((E["rho_ref"] - E["rho_water"]) / (rho - E["rho_water"]))


def partition(d_um, rho, d50_silica, mode, t=0.0):
    """Probability that a particle of size d (um) and density rho reports to the underflow."""
    rf = bypass(mode, t)
    x = d_um / d50_for(rho, d50_silica)
    p = rf + (1.0 - rf) * (1.0 - math.exp(-math.log(2.0) * x ** E["sharpness_m"]))
    if mode == "ROPING" and x > 1.0:
        p *= 0.6                       # apex choked: coarse forced out the vortex finder
    return min(1.0, max(0.0, p))


# ------------------------------------------------------------------ particles
def _hash(i, k):
    v = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return v - math.floor(v)


def particles():
    """Static per-particle constants: [(class idx, d_um, rho, phase, lane, speed)]."""
    out = []
    i = 0
    for c, (_, _, rho, dmin, dmax, n, _, _) in enumerate(E["classes"]):
        for _ in range(n):
            u = _hash(i, 1)
            d = math.exp(math.log(dmin) + u * (math.log(dmax) - math.log(dmin)))
            out.append((c, d, rho, _hash(i, 2), _hash(i, 3), 0.85 + 0.3 * _hash(i, 4)))
            i += 1
    return out


def wall_r(z):
    """Inner wall radius at head-relative height z (0 = apex, top = cone_h + head_h)."""
    if z >= E["cone_h"]:
        return E["head_r"]
    if z <= 0:
        return E["apex_r"]
    return E["apex_r"] + (E["head_r"] - E["apex_r"]) * z / E["cone_h"]


TOP = E["cone_h"] + E["head_h"]


def position(i, part, t, mode, d50_fn):
    """World (x, y, z, to_underflow) of particle i at time t (seconds).
    d50_fn(t) gives the silica cut size at time t (settings + mode)."""
    c, d, rho, phase, lane, speed = part
    T = E["cycle_s"]
    age = t / T * speed + phase
    k = math.floor(age)
    p = age - k
    t0 = (k - phase) * T / speed                       # start of this trip
    to_uf = _hash(i, 100 + k) < partition(d, rho, d50_fn(t0), mode, t0)
    z0 = E["z0"]
    ii = E["inlet"]
    # 1) feed duct: tangential entry at y = inlet y, travelling -x (counter-clockwise flow)
    if p < 0.12:
        f = p / 0.12
        x = ii["len"] * (1 - f) + 0.05
        y = ii["y"] + (lane - 0.5) * ii["w"] * 0.7
        z = E["cone_h"] + ii["z"] + (_hash(i, 5) - 0.5) * ii["h"] * 0.7
        return x, y, z0 + z, to_uf
    q = (p - 0.12) / 0.88
    ang0 = math.pi / 2                                 # entry point at +y
    zin = E["cone_h"] + ii["z"]
    if to_uf:
        if q < 0.75:                                   # outer vortex: spiral down the wall
            f = q / 0.75
            if mode == "ROPING":
                f = f ** 0.55                          # crowding at the choked apex
            z = zin * (1 - f)
            r = wall_r(z) * (0.88 - 0.12 * lane)
            ang = ang0 + 2 * math.pi * E["turns_down"] * f ** 0.8
        else:                                          # discharge
            f = (q - 0.75) / 0.25
            z = -E["spigot_h"] - f * 1.3
            if mode == "ROPING":
                spread = 0.03
                z = -E["spigot_h"] - f * 1.0
            elif mode == "PULSING":
                spread = 0.12 + 0.5 * surge(t)
            else:
                spread = 0.55
            r = E["apex_r"] * 0.6 + spread * f * (0.4 + 0.6 * lane)
            ang = ang0 + 2 * math.pi * E["turns_down"] + 2.0 * f + lane * 6.28
        x, y = r * math.cos(ang), r * math.sin(ang)
        return x, y, z0 + z, True
    # overflow: down the wall until the particle's turn height, then into the inner vortex
    # finer particles leave the outer vortex higher up
    rel = min(1.0, (d / d50_for(rho, E["d50_um"])) ** 0.5)
    z_turn = min(zin - 0.3, zin * (0.25 + 0.5 * (1.0 - rel) + 0.15 * lane))
    if q < 0.3:
        f = q / 0.3
        z = zin - f * (zin - z_turn)
        r = wall_r(z) * (0.85 - 0.1 * lane)
        ang = ang0 + 2 * math.pi * 1.6 * f
    elif q < 0.42:                                     # migrate inward
        f = (q - 0.3) / 0.12
        z = z_turn
        r_wall = wall_r(z) * (0.85 - 0.1 * lane)
        r_in = E["vf_r"] * (0.45 + 0.35 * lane)
        r = r_wall + (r_in - r_wall) * f
        ang = ang0 + 2 * math.pi * (1.6 + 0.8 * f)
    elif q < 0.85:                                     # inner vortex: spiral up, out the vortex finder
        f = (q - 0.42) / 0.43
        z = z_turn + f * (TOP + E["vf_top"] - z_turn)
        r = E["vf_r"] * (0.45 + 0.35 * lane)
        if mode == "PULSING":
            r *= 1.0 + 0.3 * math.sin(t * 8 + lane * 20)
        ang = ang0 + 2 * math.pi * (2.4 + E["turns_up"] * f)
    else:                                              # overflow pipe, out toward -x
        f = (q - 0.85) / 0.15
        z = TOP + E["vf_top"]
        r = 0.0
        ang = 0.0
        x = -f * 2.6
        y = (lane - 0.5) * E["vf_r"]
        return x, y, z0 + z + (_hash(i, 6) - 0.5) * E["vf_r"], False
    return r * math.cos(ang), r * math.sin(ang), z0 + z, False
