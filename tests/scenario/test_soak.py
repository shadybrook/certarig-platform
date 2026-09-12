"""Accelerated soak: hours of simulated bench time in seconds of wall time.

The runtime loop is driven directly (no sleeping) so the simulator's fixed physics step
advances simulated time by 20 ms per sample. 180 000 samples = 1 simulated hour.
"""

from __future__ import annotations

import resource
import sys
import tempfile
from pathlib import Path

import pytest

from certarig.edge.config import load_config
from certarig.edge.live import LiveBenchRuntime
from certarig.sim.invariants import check_all, events_from_rows, read_rows
from certarig.sim.plant import SimSettings, SimulatedRig
from tests.support import CONFIG_DIR

CONFIG = load_config(CONFIG_DIR / "rig.sim.json")


def soak(samples: int, seed: int) -> tuple[dict[str, object], int, int]:
    rig = SimulatedRig(
        CONFIG, SimSettings(seed=seed, fixed_dt_s=0.02, noise={"pressure": 0.01, "flow": 0.05})
    )
    with tempfile.TemporaryDirectory() as temp:
        runtime = LiveBenchRuntime(CONFIG, rig, Path(temp), allow_output=True)
        runtime.start_recording("soak")
        runtime.sample_once()
        runtime.command("reset")
        runtime.command("permit")
        baseline = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_growth = 0
        trips = 0
        for index in range(samples):
            # every ~4 simulated minutes, an operator disturbance
            if index % 12_000 == 6_000:
                rig.ramp("pressure", 6.0, 0.5)
            if index % 12_000 == 6_100:
                rig.ramp("pressure", 2.0, 0.5)
            if index % 12_000 == 6_300:
                runtime.command("reset")
                runtime.command("permit")
            if index % 30_000 == 15_000:
                rig.press_estop(True)
            if index % 30_000 == 15_050:
                rig.press_estop(False)
            if index % 30_000 == 15_200:
                runtime.command("reset")
                runtime.command("permit")
            state = runtime.sample_once()
            if state["guardrail"].get("event", "").endswith("_forced_safe"):
                trips += 1
            assert rig.output == state["outputs"]["gpio23_command_high"]
            if index % 20_000 == 0:
                current = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                peak_growth = max(peak_growth, current - baseline)
                assert len(runtime._history) <= 300
        runtime.command("safe")
        stopped = runtime.stop_recording()
        rows = read_rows(runtime.latest_recording())  # type: ignore[arg-type]
        report = check_all(rows, events_from_rows(rows))
        runtime.close()
        assert stopped["completed_recording"]["samples"] == len(rows)
        return report, trips, peak_growth


@pytest.mark.slow
def test_one_simulated_hour_holds_all_invariants() -> None:
    report, trips, growth = soak(180_000, seed=101)
    assert all(item["passed"] for item in report.values()), report
    assert trips >= 20  # 15 pressure excursions + 6 e-stops
    # bounded memory: peak RSS may grow by allocator noise but not by an hour of samples (~200 MB if leaked)
    limit = 64 * 1024 * 1024
    if sys.platform != "darwin":
        limit //= 1024  # ru_maxrss is in kilobytes on Linux
    assert growth < limit, f"peak RSS grew by {growth} (platform units)"


def test_short_soak_smoke() -> None:
    report, trips, _ = soak(13_000, seed=102)
    assert all(item["passed"] for item in report.values()), report
    assert trips >= 1
