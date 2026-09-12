"""Generic abort_limits, temperature-only rigs, stuck-good, and dynamic CSV."""

from __future__ import annotations

import copy
import csv
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from certarig.edge.commissioning import ProcessGuardrail
from certarig.edge.config import load_config, load_config_dict
from certarig.edge.hardware.mock import MockHardware
from certarig.edge.live import LiveBenchRuntime, csv_fields_for
from certarig.edge.models import RigSnapshot, Sample
from tests.support import CONFIG_DIR

WAVE1 = json.loads((CONFIG_DIR / "rig.wave1.json").read_text())


def _snap(config, values: dict[str, float], *, quality: str = "good", estop: bool = False) -> RigSnapshot:
    captured = datetime.now(UTC).isoformat()
    samples = tuple(
        Sample(channel_id, value, config.channel(channel_id).unit if config.channel(channel_id) else "", value, quality, captured)
        for channel_id, value in values.items()
    )
    return RigSnapshot(
        rig_id=config.rig_id,
        config_hash=config.config_hash,
        emergency_stop_active=estop,
        output_safe=True,
        samples=samples,
        captured_at=captured,
    )


def test_pressure_abort_bar_alias_still_loads() -> None:
    config = load_config(CONFIG_DIR / "rig.wave1.json")
    assert config.abort_limits["pressure"] == 4.2
    assert config.pressure_abort_bar == 4.2


def test_temperature_only_rig_loads() -> None:
    config = load_config(CONFIG_DIR / "rig.thermal.sim.json")
    assert "pressure" not in config.abort_limits
    assert config.abort_limits["temperature"] == 85.0
    jacket = config.channel("jacket_c")
    assert jacket is not None and jacket.concept == "temperature"
    assert jacket.stuck_samples == 50
    fields = csv_fields_for(config)
    assert "jacket_c_value" in fields
    assert "pressure_bar" not in fields


def test_abort_limits_cap_trip_for_any_concept() -> None:
    raw = copy.deepcopy(WAVE1)
    raw.pop("pressure_abort_bar")
    raw["abort_limits"] = {"pressure": 3.5, "flow": 12.0}
    config = load_config_dict(raw)
    signals = {row["channel_id"]: row for row in config.signals()}
    assert signals["pressure_emulator"]["limits"]["trip"] == [0.0, 3.5]
    assert signals["flow_emulator"]["limits"]["trip"] == [0.0, 12.0]


def test_stuck_channel_forces_output_low() -> None:
    raw = copy.deepcopy(WAVE1)
    raw["channels"][0]["stuck_samples"] = 3
    raw["channels"][0]["stuck_epsilon"] = 0.001
    config = load_config_dict(raw)
    guardrail = ProcessGuardrail(config, allow_output=True)
    for _ in range(2):
        result = guardrail.observe(_snap(config, {"pressure_emulator": 2.0, "flow_emulator": 8.0}))
        assert result.process_healthy
    guardrail.command("reset")
    assert guardrail.command("permit").drive_high
    assert guardrail.observe(_snap(config, {"pressure_emulator": 2.0, "flow_emulator": 8.0})).drive_high
    stuck = guardrail.observe(_snap(config, {"pressure_emulator": 2.0, "flow_emulator": 8.0}))
    assert stuck.channels[0]["quality"] == "stuck"
    assert not stuck.process_healthy
    assert not stuck.drive_high
    assert "forced_safe" in stuck.event


def test_thermal_csv_has_jacket_columns() -> None:
    config = load_config(CONFIG_DIR / "rig.thermal.sim.json")
    with tempfile.TemporaryDirectory() as temp:
        runtime = LiveBenchRuntime(config, MockHardware(config), temp, allow_output=True)
        runtime.start_recording("thermal")
        runtime.sample_once()
        completed = runtime.stop_recording()["completed_recording"]
        path = Path(temp) / completed["filename"]
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        runtime.close()
    assert rows
    assert "jacket_c_value" in rows[0]
    assert "jacket_c_state" in rows[0]
    assert "jacket_c_quality" in rows[0]
    assert "pressure_bar" not in rows[0]


def test_wave1_csv_keeps_legacy_aliases() -> None:
    config = load_config(CONFIG_DIR / "rig.wave1.json")
    fields = csv_fields_for(config)
    assert "pressure_emulator_value" in fields
    assert "pressure_bar" in fields
    assert "flow_l_min" in fields
