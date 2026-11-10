"""Explicit branch-inertance/compliance transient, not CFD or a valve FEM."""

from __future__ import annotations

import csv
import gzip
import math


def scenarios():
    return [
        dict(name="nominal_closure", C=2e-10, closing=0.10, dt=1e-4, end=2.0, unsafe=False),
        dict(name="minimum_compliance_fast_valve", C=2e-10, closing=0.001, dt=1e-4, end=2.0, unsafe=False),
        dict(name="maximum_inertance_minimum_closing", C=2e-10, closing=0.05, dt=1e-4, end=2.0, unsafe=False),
        dict(name="arrestor_failed_slow_valve", C=3e-14, closing=0.05, dt=2e-6, end=0.8, unsafe=False),
        dict(
            name="negative_fast_valve_failed_arrestor",
            C=3e-14,
            closing=0.001,
            dt=2e-6,
            end=0.2032,
            unsafe=True,
        ),
        dict(name="minimum_compliance_refined", C=2e-10, closing=0.001, dt=2e-5, end=2.0, unsafe=False),
    ]


def solve(p, root=None):
    inertance = 7.1e7
    Rfeed = 2e12
    G = 1.5 / 60000 / math.sqrt(45000)
    source = 60000.0
    q = math.sqrt(source / (Rfeed + 1 / G**2))
    pressure = q * q / G**2
    dt = p["dt"]
    peak = pressure
    minimum = pressure
    saved = []
    stride = 1  # Preserve every integration state for offline extrema replay.

    def derivative(t, q, pressure):
        opening = max(0, 1 - max(0, t - 0.2) / p["closing"])
        out = G * opening * math.sqrt(max(0, pressure))
        return ((source - pressure - Rfeed * q * abs(q)) / inertance, (q - out) / p["C"])

    for step in range(round(p["end"] / dt) + 1):
        t = step * dt
        if step % stride == 0:
            saved.append([t, q, pressure, source])
        peak = max(peak, pressure)
        minimum = min(minimum, pressure)
        if not all(math.isfinite(x) for x in [q, pressure]):
            raise ValueError("Nonfinite hydraulic transient")
        a, b = derivative(t, q, pressure)
        c, d = derivative(t + dt / 2, q + a * dt / 2, pressure + b * dt / 2)
        e, f = derivative(t + dt / 2, q + c * dt / 2, pressure + d * dt / 2)
        g, h = derivative(t + dt, q + e * dt, pressure + f * dt)
        q += dt * (a + 2 * c + 2 * e + g) / 6
        pressure += dt * (b + 2 * d + 2 * f + h) / 6
    # Normal full-scale2bar is the stated observation target; all wet parts proof6.
    if minimum < -2000:
        raise ValueError("Left single-phase model domain; do not interpret cavitating trace")
    criterion = peak < 200000 and minimum >= -2000
    result = dict(
        parameters=p,
        peak_bar=peak / 1e5,
        min_bar=minimum / 1e5,
        observation_envelope_pass=criterion,
        experiment_ok=criterion != p["unsafe"],
        steps=round(p["end"] / dt) + 1,
        saved_samples=len(saved),
        model="RK4, source0.60bar upper envelope, I=7.1e7, feed R=2e12, valve Kv chosen at1.5Lmin/0.45bar, compliance as declared; negative window ends at203.2ms before first vacuum/cavitation; it proves initial overpressure only; no post-cavitation prediction",
    )
    if root:
        folder = root / "hydraulic" / p["name"]
        folder.mkdir(parents=True, exist_ok=True)
        with gzip.open(folder / "trace.csv.gz", "wt", newline="") as stream:
            w = csv.writer(stream)
            w.writerow(["time_s", "flow_m3s", "valve_pressure_Pa", "source_Pa"])
            w.writerows(saved)
    return result


def run(root):
    return [solve(p, root) for p in scenarios()]
