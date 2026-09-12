from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from certarig.edge.config import load_config
from certarig.edge.evidence import EvidenceStore
from certarig.edge.executor import DeterministicExecutor
from certarig.edge.hardware.mock import MockHardware
from certarig.edge.models import CommissioningPlan, PlanState, PlanStep, RunOutcome

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "rig.example.json"


class ExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.config = load_config(CONFIG)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _executor(self, hardware: MockHardware) -> DeterministicExecutor:
        self.store = EvidenceStore(Path(self.temp.name) / "evidence.sqlite3")
        return DeterministicExecutor(
            hardware=hardware,
            store=self.store,
            sample_interval_ms=20,
            pressure_abort_bar=self.config.pressure_abort_bar,
            actuation_enabled=True,
        )

    def _plan(self) -> CommissioningPlan:
        return CommissioningPlan(
            plan_id="plan-approved",
            rig_id=self.config.rig_id,
            config_hash=self.config.config_hash,
            purpose="bounded response test",
            pressure_limit_bar=4.2,
            steps=[
                PlanStep(action="set_valve", duration_ms=80, valve_open=True),
                PlanStep(action="hold", duration_ms=80),
                PlanStep(action="set_valve", duration_ms=20, valve_open=False),
            ],
            state=PlanState.APPROVED,
        )

    def test_normal_run_completes_and_returns_safe_state(self) -> None:
        hardware = MockHardware(self.config)
        executor = self._executor(hardware)
        result = executor.run(self._plan())
        self.assertEqual(result.outcome, RunOutcome.COMPLETED)
        self.assertTrue(hardware.output_is_safe())
        bundle = self.store.evidence_bundle(result.run_id)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle["checksum"], result.evidence_checksum)
        self.store.close()

    def test_pressure_breach_aborts_and_closes_output(self) -> None:
        hardware = MockHardware(
            self.config,
            pressure_profile=lambda index, valve_open: 6.04 if valve_open else 0.1,
        )
        executor = self._executor(hardware)
        result = executor.run(self._plan())
        self.assertEqual(result.outcome, RunOutcome.SAFE_ABORT)
        self.assertIn("pressure", result.reason)
        self.assertTrue(hardware.output_is_safe())
        self.store.close()

    def test_unapproved_plan_cannot_execute(self) -> None:
        hardware = MockHardware(self.config)
        executor = self._executor(hardware)
        plan = self._plan()
        plan.state = PlanState.VALIDATED
        with self.assertRaises(ValueError):
            executor.run(plan)
        self.store.close()


if __name__ == "__main__":
    unittest.main()
