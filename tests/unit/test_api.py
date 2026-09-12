from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from certarig.edge.app import CertaRigApplication, make_server
from certarig.edge.client import CertaRigClient
from certarig.edge.config import load_config
from certarig.edge.evidence import EvidenceStore
from certarig.edge.hardware.mock import MockHardware

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "rig.example.json"
OPERATOR_KEY = "test-operator-key-12345"


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        config = load_config(CONFIG)
        self.hardware = MockHardware(config)
        self.store = EvidenceStore(Path(self.temp.name) / "evidence.sqlite3")
        self.app = CertaRigApplication(
            config=config,
            hardware=self.hardware,
            store=self.store,
            operator_key=OPERATOR_KEY,
            actuation_enabled=False,
        )
        self.server = make_server(self.app, "127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.app.close()
        self.temp.cleanup()

    @staticmethod
    def _proposal(snapshot: dict) -> dict:
        return {
            "rig_id": snapshot["rig_id"],
            "config_hash": snapshot["config_hash"],
            "purpose": "API integration test",
            "pressure_limit_bar": 4.2,
            "steps": [
                {"action": "sample", "duration_ms": 20},
                {"action": "set_valve", "duration_ms": 40, "valve_open": True},
                {"action": "set_valve", "duration_ms": 20, "valve_open": False},
            ],
        }

    def test_complete_http_workflow(self) -> None:
        public_client = CertaRigClient(self.url)
        health = public_client.health()
        self.assertEqual(health["status"], "ok")
        snapshot = public_client.snapshot()
        plan = public_client.create_plan(self._proposal(snapshot))
        self.assertEqual(plan["state"], "validated")
        with self.assertRaises(RuntimeError):
            public_client.approve_plan(plan["plan_id"], "unauthorized")

        operator_client = CertaRigClient(self.url, OPERATOR_KEY)
        approved = operator_client.approve_plan(plan["plan_id"], "test operator")
        self.assertEqual(approved["state"], "approved")
        result = operator_client.execute_plan(plan["plan_id"])
        self.assertEqual(result["outcome"], "completed")
        evidence = operator_client.evidence(result["run_id"])
        self.assertEqual(evidence["checksum"], result["evidence_checksum"])
        self.assertTrue(self.hardware.output_is_safe())


if __name__ == "__main__":
    unittest.main()
