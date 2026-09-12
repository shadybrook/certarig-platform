from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from certarig.edge.config import ConfigurationError, load_config
from certarig.edge.hardware.mock import MockHardware
from certarig.edge.models import CommissioningPlan, PlanState, PlanStep
from certarig.edge.safety import validate_plan

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "rig.example.json"
WAVE1_CONFIG = ROOT / "config" / "rig.wave1.json"


class ConfigAndSafetyTests(unittest.TestCase):
    def test_configuration_hash_is_stable(self) -> None:
        first = load_config(CONFIG)
        second = load_config(CONFIG)
        self.assertEqual(first.config_hash, second.config_hash)
        self.assertEqual(first.rig_id, "pressure-flow-rig-01")

    def test_wave1_configuration_matches_dry_bench_contract(self) -> None:
        config = load_config(WAVE1_CONFIG)
        self.assertEqual(config.hardware.mode, "raspberry_pi")
        self.assertTrue(config.hardware.emergency_stop_active_high)
        self.assertIsNone(config.hardware.relay_feedback_gpio)
        self.assertEqual([channel.adc_channel for channel in config.channels], [0, 1])
        self.assertEqual([channel.raw_max_v for channel in config.channels], [3.302, 3.3])

    def test_required_channel_without_calibration_is_rejected(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["channels"][0]["calibration_id"] = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_emergency_stop_active_high_requires_boolean(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["hardware"]["emergency_stop_active_high"] = "true"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-estop-polarity.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_config(path)

    def test_stale_configuration_hash_blocks_plan(self) -> None:
        config = load_config(CONFIG)
        hardware = MockHardware(config)
        plan = CommissioningPlan(
            plan_id="plan-test",
            rig_id=config.rig_id,
            config_hash="stale",
            purpose="test",
            pressure_limit_bar=4.2,
            steps=[PlanStep(action="sample", duration_ms=100)],
        )
        findings = validate_plan(config, hardware.snapshot(), plan)
        self.assertEqual(plan.state, PlanState.BLOCKED)
        self.assertTrue(any("stale" in finding for finding in findings))

    def test_valid_plan_reaches_validated_state(self) -> None:
        config = load_config(CONFIG)
        hardware = MockHardware(config)
        plan = CommissioningPlan(
            plan_id="plan-test",
            rig_id=config.rig_id,
            config_hash=config.config_hash,
            purpose="test",
            pressure_limit_bar=4.2,
            steps=[PlanStep(action="sample", duration_ms=100)],
        )
        findings = validate_plan(config, hardware.snapshot(), plan)
        self.assertEqual(findings, [])
        self.assertEqual(plan.state, PlanState.VALIDATED)


if __name__ == "__main__":
    unittest.main()
