from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from certarig.edge.config import load_config
from certarig.edge.hardware.mock import MockHardware
from certarig.edge.live import LiveBenchRuntime, make_live_server

ROOT = Path(__file__).resolve().parents[2]
KEY = "test-live-operator-key"


class LiveApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        config = load_config(ROOT / "config" / "rig.example.json")
        self.runtime = LiveBenchRuntime(
            config,
            MockHardware(config),
            self.temp.name,
            allow_output=True,
        )
        self.runtime.sample_once()
        self.server = make_live_server(self.runtime, KEY, ROOT / "studio", "127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.runtime.close()
        self.temp.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None, key: str | None = KEY):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["X-CertaRig-Operator-Key"] = key
        request = Request(self.url + path, data=body, headers=headers, method=method)
        with urlopen(request, timeout=5) as response:
            return response.headers, response.read()

    def test_static_console_commands_and_csv_workflow(self) -> None:
        _, page = self.request("GET", "/", key=None)
        self.assertIn(b"Live control and evidence console", page)
        _, raw_state = self.request("GET", "/v1/live/state", key=None)
        state = json.loads(raw_state)
        self.assertTrue(state["guardrail"]["process_healthy"])

        with self.assertRaises(HTTPError) as unauthorized:
            self.request("POST", "/v1/live/commands/safe", {}, key=None)
        self.assertEqual(unauthorized.exception.code, 401)
        unauthorized.exception.close()

        self.request("POST", "/v1/live/recordings/start", {"label": "api-test"})
        _, raw_reset = self.request("POST", "/v1/live/commands/reset", {})
        self.assertEqual(json.loads(raw_reset)["guardrail"]["event"], "trip_reset_output_safe")
        _, raw_permit = self.request("POST", "/v1/live/commands/permit", {})
        self.assertTrue(json.loads(raw_permit)["outputs"]["relay_energized_expected"])
        self.request("POST", "/v1/live/commands/safe", {})
        _, raw_stop = self.request("POST", "/v1/live/recordings/stop", {})
        completed = json.loads(raw_stop)["completed_recording"]
        self.assertEqual(len(completed["sha256"]), 64)
        headers, csv_body = self.request("GET", "/v1/live/recordings/latest.csv")
        self.assertIn("text/csv", headers["Content-Type"])
        self.assertIn(b"pressure_bar", csv_body)


if __name__ == "__main__":
    unittest.main()
