from __future__ import annotations

import pytest

from certarig.edge.config import load_config
from certarig.edge.hardware.base import HardwareError
from certarig.sim import invariants
from certarig.sim.plant import SimSettings, SimulatedRig
from certarig.sim.scenario import ScenarioError, load_scenario
from tests.support import CONFIG_DIR

CONFIG = load_config(CONFIG_DIR / "rig.sim.json")


def values(rig: SimulatedRig, n: int) -> list[tuple[float, ...]]:
    out = []
    for _ in range(n):
        snap = rig.snapshot()
        out.append(tuple(sample.value for sample in snap.samples))
    return out


def test_deterministic_under_seed() -> None:
    a = SimulatedRig(CONFIG, SimSettings(seed=5, fixed_dt_s=0.02, noise={"pressure": 0.01, "flow": 0.05}))
    b = SimulatedRig(CONFIG, SimSettings(seed=5, fixed_dt_s=0.02, noise={"pressure": 0.01, "flow": 0.05}))
    for rig in (a, b):
        rig.ramp("pressure", 4.0, 0.5)
    assert values(a, 50) == values(b, 50)
    c = SimulatedRig(CONFIG, SimSettings(seed=6, fixed_dt_s=0.02, noise={"pressure": 0.01, "flow": 0.05}))
    c.ramp("pressure", 4.0, 0.5)
    assert values(c, 50) != values(a, 50)


def test_ramp_and_lag_reach_target_and_raw_scaling() -> None:
    rig = SimulatedRig(CONFIG, SimSettings(seed=1, fixed_dt_s=0.02, lag_s=0.1))
    rig.ramp("pressure", 5.0, 0.4)
    values(rig, 60)  # 1.2 simulated seconds
    snap = rig.snapshot()
    pressure = next(s for s in snap.samples if s.channel_id == "pressure_emulator")
    assert abs(pressure.value - 5.0) < 0.02
    assert pressure.raw_value is not None and abs(pressure.raw_value - 3.302 * 0.5) < 0.02
    assert rig.describe()["channels"]["pressure_emulator"]["target"] == 5.0
    with pytest.raises(KeyError):
        rig.set_target("chamber", 1.0)


def test_faults() -> None:
    rig = SimulatedRig(CONFIG, SimSettings(seed=1, fixed_dt_s=0.02, lag_s=0.0))
    rig.inject("dropout", "flow")
    assert [s.channel_id for s in rig.snapshot().samples] == ["pressure_emulator"]
    rig.clear("dropout", "flow")
    rig.inject("bad_quality", "flow")
    assert next(s for s in rig.snapshot().samples if s.channel_id == "flow_emulator").quality == "bad"
    rig.clear(channel="flow")
    rig.inject("saturate", "pressure")
    sat = next(s for s in rig.snapshot().samples if s.channel_id == "pressure_emulator")
    assert sat.value > 10.0 and sat.quality == "bad"
    rig.clear()
    rig.set_target("pressure", 2.0)
    rig.snapshot()
    rig.inject("stuck", "pressure")
    rig.set_target("pressure", 8.0)
    stuck = [values(rig, 1)[0][0] for _ in range(5)]
    assert max(stuck) - min(stuck) < 1e-6
    rig.clear("stuck")
    rig.inject("drift", "pressure", rate=1.0)
    before = values(rig, 1)[0][0]
    after = values(rig, 50)[-1][0]
    assert after > before + 0.5
    rig.clear()
    rig.inject("snapshot_failure", count=2)
    with pytest.raises(HardwareError):
        rig.snapshot()
    with pytest.raises(HardwareError):
        rig.snapshot()
    rig.snapshot()
    rig.inject("driver_failure")
    with pytest.raises(HardwareError):
        rig.set_valve(True)
    rig.clear("driver_failure")
    with pytest.raises(ValueError, match="needs a channel"):
        rig.inject("stuck")
    assert rig.faults() == {"global": {}, "channels": {}}


def test_estop_and_nc2_behaviour() -> None:
    rig = SimulatedRig(CONFIG, SimSettings(seed=1, fixed_dt_s=0.02))
    rig.set_valve(True)
    assert rig.output is True and rig.output_is_safe() is False
    rig.press_estop()
    with pytest.raises(HardwareError):
        rig.set_valve(True)
    snap = rig.snapshot()
    assert snap.emergency_stop_active is True and rig.output is False  # NC2 dropped it
    assert any(entry["what"] == "nc2_dropped_output" for entry in rig.log)
    rig.release_estop()
    assert rig.snapshot().emergency_stop_active is False
    rig.inject("estop_wire_break")
    assert rig.snapshot().emergency_stop_active is True
    rig.clear("estop_wire_break")
    rig.set_valve(True)
    rig.force_safe_state()
    assert rig.output is False
    rig.close()
    assert rig.closed


def test_settings_from_config() -> None:
    settings = SimSettings.from_config(CONFIG, CONFIG.hardware.simulator)
    assert settings.seed == 7 and settings.noise["pressure"] == 0.005 and settings.fixed_dt_s == 0.02


# ---------------------------------------------------------------- invariants
def row(**kw: object) -> dict[str, str]:
    base = {
        "sample_index": "0",
        "elapsed_s": "0.0",
        "event": "",
        "gpio23_command_high": "false",
        "estop_active": "false",
        "pressure_state": "safe",
        "flow_state": "safe",
        "process_healthy": "true",
        "record_kind": "sample",
    }
    base.update({k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in kw.items()})
    return base


def test_invariant_checks() -> None:
    good = [row(sample_index=i, elapsed_s=i * 0.1) for i in range(5)]
    report = invariants.check_all(
        good, ["permit_accepted", "pressure_high_forced_safe", "trip_reset_output_safe", "permit_accepted"]
    )
    assert all(item["passed"] for item in report.values()), report
    bad = [
        row(sample_index=0, gpio23_command_high=True, estop_active=True),
        row(
            sample_index=2,
            gpio23_command_high=True,
            pressure_state="high",
            process_healthy=False,
            elapsed_s=-1,
        ),
    ]
    report = invariants.check_all(bad, ["permit_accepted", "estop_open_forced_safe", "permit_accepted"])
    assert not report["output_off_when_estop"]["passed"]
    assert report["output_off_when_process_unsafe"]["problem_count"] == 2
    assert not report["no_restart_without_reset"]["passed"]
    assert not report["csv_rows_contiguous"]["passed"]
    assert not report["ends_safe"]["passed"]
    assert invariants.ends_safe([]) == ["no rows"]
    assert invariants.no_restart_without_reset(["operator_safe", "permit_accepted"])
    assert invariants.events_from_rows([row(event="x"), row()]) == ["x"]


def test_scenario_loader_validates(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "s.yaml"
    path.write_text("name: bad\nevents: []\nexpect: {}\nunknown: 1\n")
    with pytest.raises(ScenarioError):
        load_scenario(path)
    path.write_text("name: two clocks\nevents:\n  - {at_s: 1, at_step: x, action: note}\nexpect: {}\n")
    with pytest.raises(ScenarioError, match="exactly one"):
        load_scenario(path)
