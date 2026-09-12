from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from certarig.edge.commissioning import ProcessGuardrail
from certarig.edge.config import load_config
from certarig.edge.hardware.base import HardwareAdapter
from certarig.edge.live import LiveBenchRuntime
from certarig.edge.models import RigSnapshot, Sample

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT / "config" / "rig.wave1.json")


def snapshot(
    pressure: float = 2.0,
    flow: float = 8.0,
    *,
    estop: bool = False,
    pressure_quality: str = "good",
    include_flow: bool = True,
) -> RigSnapshot:
    captured = datetime.now(UTC).isoformat()
    samples = [
        Sample("pressure_emulator", pressure, "bar", pressure * 3.302 / 10, pressure_quality, captured)
    ]
    if include_flow:
        samples.append(Sample("flow_emulator", flow, "L/min", flow * 3.3 / 20, "good", captured))
    return RigSnapshot(
        rig_id=CONFIG.rig_id,
        config_hash=CONFIG.config_hash,
        emergency_stop_active=estop,
        output_safe=True,
        samples=tuple(samples),
        captured_at=captured,
    )


class ProcessGuardrailTests(unittest.TestCase):
    def armed(self) -> ProcessGuardrail:
        guardrail = ProcessGuardrail(CONFIG, allow_output=True)
        guardrail.observe(snapshot())
        guardrail.command("reset")
        self.assertTrue(guardrail.command("permit").drive_high)
        return guardrail

    def test_startup_is_safe_and_requires_reset(self) -> None:
        guardrail = ProcessGuardrail(CONFIG, allow_output=True)
        result = guardrail.observe(snapshot())
        self.assertTrue(result.process_healthy)
        self.assertTrue(result.trip_latched)
        self.assertFalse(result.drive_high)
        self.assertEqual(guardrail.command("permit").event, "permit_rejected_reset_required")
        limits = guardrail.observe(snapshot(pressure=4.2, flow=15.0))
        self.assertTrue(limits.process_healthy)

    def test_pressure_high_forces_safe_and_never_auto_restarts(self) -> None:
        guardrail = self.armed()
        result = guardrail.observe(snapshot(pressure=4.3))
        self.assertEqual(result.event, "pressure_high_forced_safe")
        self.assertFalse(result.drive_high)
        self.assertTrue(result.trip_latched)
        recovered = guardrail.observe(snapshot(pressure=2.0))
        self.assertEqual(recovered.event, "process_safe_reset_required")
        self.assertFalse(recovered.drive_high)
        self.assertEqual(guardrail.command("permit").event, "permit_rejected_reset_required")

    def test_flow_high_forces_safe(self) -> None:
        result = self.armed().observe(snapshot(flow=15.1))
        self.assertEqual(result.event, "flow_high_forced_safe")
        self.assertFalse(result.drive_high)

    def test_small_adc_undershoot_below_zero_stays_healthy(self) -> None:
        guardrail = self.armed()
        result = guardrail.observe(snapshot(pressure=-0.04, flow=-0.03))
        self.assertTrue(result.process_healthy)
        self.assertEqual(result.reason, "permit_active")
        invalid = guardrail.observe(snapshot(pressure=-0.5))
        self.assertEqual(invalid.event, "sensor_invalid_forced_safe")

    def test_missing_or_bad_sensor_forces_safe(self) -> None:
        guardrail = self.armed()
        missing = guardrail.observe(snapshot(include_flow=False))
        self.assertEqual(missing.event, "sensor_invalid_forced_safe")
        self.assertFalse(missing.process_healthy)
        guardrail.observe(snapshot())
        guardrail.command("reset")
        guardrail.command("permit")
        bad = guardrail.observe(snapshot(pressure_quality="out_of_range"))
        self.assertEqual(bad.event, "sensor_invalid_forced_safe")
        self.assertFalse(bad.drive_high)

    def test_estop_dominates_and_release_requires_reset(self) -> None:
        guardrail = self.armed()
        tripped = guardrail.observe(snapshot(estop=True))
        self.assertEqual(tripped.event, "estop_open_forced_safe")
        self.assertFalse(tripped.drive_high)
        released = guardrail.observe(snapshot(estop=False))
        self.assertEqual(released.event, "estop_closed_reset_required")
        self.assertTrue(released.trip_latched)

    def test_reset_is_rejected_while_process_is_unsafe(self) -> None:
        guardrail = ProcessGuardrail(CONFIG, allow_output=True)
        guardrail.observe(snapshot(pressure=5.0))
        result = guardrail.command("reset")
        self.assertEqual(result.event, "reset_rejected_process_unsafe")
        self.assertTrue(result.trip_latched)

    def test_monitor_only_mode_cannot_permit(self) -> None:
        guardrail = ProcessGuardrail(CONFIG, allow_output=False)
        guardrail.observe(snapshot())
        guardrail.command("reset")
        result = guardrail.command("permit")
        self.assertEqual(result.event, "permit_rejected_monitor_only")
        self.assertFalse(result.drive_high)

    def test_operator_safe_latches_reset_requirement(self) -> None:
        guardrail = self.armed()
        result = guardrail.command("safe")
        self.assertEqual(result.event, "operator_safe")
        self.assertTrue(result.trip_latched)
        self.assertFalse(result.drive_high)
        self.assertEqual(guardrail.command("permit").event, "permit_rejected_reset_required")


class ControllableHardware(HardwareAdapter):
    def __init__(self) -> None:
        self.pressure = 2.0
        self.flow = 8.0
        self.estop = False
        self.output = False
        self.closed = False

    def snapshot(self) -> RigSnapshot:
        value = snapshot(self.pressure, self.flow, estop=self.estop)
        return RigSnapshot(
            rig_id=value.rig_id,
            config_hash=value.config_hash,
            emergency_stop_active=value.emergency_stop_active,
            output_safe=not self.output,
            samples=value.samples,
            captured_at=value.captured_at,
        )

    def set_valve(self, open_state: bool) -> None:
        if open_state and self.estop:
            raise RuntimeError("emergency stop is active")
        self.output = bool(open_state)

    def force_safe_state(self) -> None:
        self.output = False

    def output_is_safe(self) -> bool:
        return not self.output

    def close(self) -> None:
        self.output = False
        self.closed = True


class LiveBenchRuntimeTests(unittest.TestCase):
    def test_runtime_controls_output_and_records_complete_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            hardware = ControllableHardware()
            runtime = LiveBenchRuntime(CONFIG, hardware, temp, allow_output=True)
            runtime.sample_once()
            runtime.command("reset")
            state = runtime.command("permit")
            self.assertTrue(state["outputs"]["relay_energized_expected"])
            self.assertTrue(hardware.output)

            runtime.start_recording("Randomized test #1")
            runtime.sample_once()
            hardware.flow = 16.0
            tripped = runtime.sample_once()
            self.assertEqual(tripped["guardrail"]["event"], "flow_high_forced_safe")
            self.assertFalse(hardware.output)
            completed = runtime.stop_recording()["completed_recording"]
            path = Path(temp) / completed["filename"]
            self.assertTrue(path.is_file())
            self.assertEqual(len(completed["sha256"]), 64)
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreaterEqual(len(rows), 2)
            self.assertEqual(rows[-1]["flow_state"], "high")
            self.assertEqual(rows[-1]["gpio23_command_high"], "false")
            self.assertEqual(rows[-1]["trip_latched"], "true")
            runtime.close()


if __name__ == "__main__":
    unittest.main()
