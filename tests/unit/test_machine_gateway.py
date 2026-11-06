from __future__ import annotations

import hashlib
import json
import tempfile
import time
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from certarig.machines.agent_tools import MachineTools
from certarig.machines.gateway import Audit, Gateway, Intent, NoRedirect, OctoPrintVirtual, Refused, canonical
from certarig.machines.protocols import grbl_realtime, moonraker_request, sdcp_request

HASH = hashlib.sha256(b"approved job").hexdigest()


class FakeController:
    def __init__(self) -> None:
        self.state = "Operational"
        self.sent = []
        self.age = 0
        self.fail = False

    def status(self):
        return {"state": self.state, "observed_monotonic": time.monotonic() - self.age}

    def send(self, intent):
        self.sent.append(intent)
        if self.fail:
            raise TimeoutError("ambiguous controller acknowledgement")
        return {"dispatched": True, "physical_result": "not_measured"}


class MachineGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.audit = Audit(Path(self.tmp.name) / "audit.jsonl")
        self.adapter = FakeController()
        self.gateway = Gateway("virtual-01", self.adapter, self.audit)
        self.start = Intent("virtual-01", "start", "square.gcode", HASH)

    def test_start_without_approval_never_reaches_transport(self):
        with self.assertRaisesRegex(Refused, "approval_required"):
            self.gateway.execute(self.start)
        self.assertEqual(self.adapter.sent, [])

    def test_approval_is_bound_to_exact_action_and_hash(self):
        approval = self.gateway.approve(self.start)
        with self.assertRaisesRegex(Refused, "approval_required"):
            self.gateway.execute(replace(self.start, sha256="0" * 64), approval)
        self.assertEqual(self.adapter.sent, [])

    def test_one_approval_cannot_be_replayed(self):
        approval = self.gateway.approve(self.start)
        self.gateway.execute(self.start, approval)
        with self.assertRaisesRegex(Refused, "approval_required"):
            self.gateway.execute(self.start, approval)
        self.assertEqual(len(self.adapter.sent), 1)

    def test_expired_approval_is_denied(self):
        approval = self.gateway.approve(self.start)
        self.gateway.clock = lambda: time.monotonic() + 1000
        self.adapter.status = lambda: {"state": "Operational", "observed_monotonic": self.gateway.clock()}
        with self.assertRaisesRegex(Refused, "approval_required"):
            self.gateway.execute(self.start, approval)

    def test_unknown_state_and_stale_observation_are_denied(self):
        self.adapter.state = "Unknown"
        with self.assertRaisesRegex(Refused, "invalid_machine_state"):
            self.gateway.execute(self.start)
        self.adapter.state, self.adapter.age = "Operational", 10
        with self.assertRaisesRegex(Refused, "stale_or_invalid"):
            self.gateway.execute(self.start)

    def test_wrong_machine_and_future_timestamp_are_denied(self):
        with self.assertRaisesRegex(Refused, "machine_mismatch"):
            self.gateway.execute(replace(self.start, machine_id="other"))
        self.adapter.age = -20
        with self.assertRaisesRegex(Refused, "stale_or_invalid"):
            self.gateway.execute(self.start)

    def test_timeout_consumes_approval_and_latches_uncertainty(self):
        approval = self.gateway.approve(self.start)
        self.adapter.fail = True
        with self.assertRaises(TimeoutError):
            self.gateway.execute(self.start, approval)
        self.assertTrue(self.gateway.uncertain)
        with self.assertRaisesRegex(Refused, "reconciliation"):
            self.gateway.execute(self.start, approval)

    def test_pause_remains_available_after_uncertainty(self):
        self.gateway.uncertain = True
        self.adapter.state = "Printing"
        self.gateway.execute(replace(self.start, action="pause"))
        self.assertEqual(len(self.adapter.sent), 1)

    def test_resume_needs_new_approval(self):
        self.adapter.state = "Paused"
        resume = replace(self.start, action="resume")
        with self.assertRaisesRegex(Refused, "approval_required"):
            self.gateway.execute(resume)
        self.gateway.execute(resume, self.gateway.approve(resume))

    def test_path_and_action_injection_are_rejected(self):
        for job in (
            "../bad.gcode",
            "/tmp/bad.gcode",
            "a//b.gcode",
            "a%2fb.gcode",
            "a.gcode\nM112",
            "a\\b.gcode",
            "firmware.bin",
        ):
            with self.subTest(job=job), self.assertRaises(Refused):
                replace(self.start, job=job)
        with self.assertRaises(Refused):
            replace(self.start, action="raw_gcode")

    def test_agent_cannot_mint_approvals_or_add_raw_commands(self):
        tools = MachineTools(self.gateway)
        self.assertEqual({s.name for s in tools.specs()}, {"machine_status", "machine_command"})
        self.assertFalse(tools.execute("approve", {}).ok)
        self.assertFalse(tools.execute("machine_command", {**asdict(self.start), "gcode": "M3"}).ok)
        self.assertFalse(tools.execute("machine_command", {**asdict(self.start), "action": "raw"}).ok)
        self.assertFalse(tools.execute("machine_command", asdict(self.start)).ok)
        self.assertEqual(self.adapter.sent, [])

    def test_adapter_rejects_non_loopback_urls(self):
        for url in (
            "http://printer.local",
            "http://example.com",
            "http://127.0.0.1/path",
            "http://user:pass@127.0.0.1",
            "http://127.0.0.1?x=1",
        ):
            with self.subTest(url=url), self.assertRaises(Refused):
                OctoPrintVirtual(url, "test-key")

    def test_redirects_cannot_forward_api_credentials(self):
        with self.assertRaisesRegex(Refused, "redirect_refused"):
            NoRedirect().redirect_request(None, None, 302, "Found", {}, "http://other.invalid")

    def test_non_finite_telemetry_cannot_authorize_start(self):
        self.adapter.age = float("nan")
        with self.assertRaisesRegex(Refused, "stale_or_invalid"):
            self.gateway.execute(self.start)

    def test_invalid_approval_lifetime_is_denied(self):
        for ttl in (0, -1, 301, float("nan"), float("inf")):
            with self.subTest(ttl=ttl), self.assertRaisesRegex(Refused, "invalid_approval"):
                self.gateway.approve(self.start, ttl)

    def test_physical_serial_port_is_rejected_even_on_loopback(self):
        adapter = OctoPrintVirtual("http://127.0.0.1:12345", "test-key")
        adapter.request = lambda *args: {"current": {"port": "/dev/ttyUSB0"}}
        with self.assertRaisesRegex(Refused, "physical_serial"):
            adapter.require_virtual()

    def test_modified_remote_artifact_is_rejected(self):
        adapter = OctoPrintVirtual("http://127.0.0.1:12345", "test-key")
        adapter.require_virtual = lambda: None
        adapter.file_hash = lambda job: "0" * 64
        with self.assertRaisesRegex(Refused, "artifact_hash_mismatch"):
            adapter.send(self.start)

    def test_audit_hash_chain_verifies(self):
        with self.assertRaises(Refused):
            self.gateway.execute(self.start)
        self.gateway.execute(self.start, self.gateway.approve(self.start))
        previous = "0" * 64
        for raw in self.audit.path.read_text().splitlines():
            row = json.loads(raw)
            recorded = row.pop("hash")
            self.assertEqual(row["previous"], previous)
            self.assertEqual(recorded, hashlib.sha256(canonical(row)).hexdigest())
            previous = recorded

    def test_moonraker_uses_dedicated_stop_and_filename_encoding(self):
        self.assertEqual(moonraker_request("emergency_stop"), ("POST", "/printer/emergency_stop"))
        self.assertEqual(
            moonraker_request("start", "two words.gcode"),
            ("POST", "/printer/print/start?filename=two+words.gcode"),
        )
        with self.assertRaises(Refused):
            moonraker_request("raw_gcode")

    def test_grbl_realtime_commands_are_unterminated_bytes(self):
        self.assertEqual(grbl_realtime("status"), b"?")
        self.assertEqual(grbl_realtime("feed_hold"), b"!")
        self.assertEqual(grbl_realtime("resume"), b"~")
        with self.assertRaises(Refused):
            grbl_realtime("emergency_stop")

    def test_resin_protocol_preserves_device_identity_and_command_semantics(self):
        for action, code in (("start", 128), ("pause", 129), ("cancel", 130), ("resume", 131)):
            msg = sdcp_request(
                action,
                brand_id="brand",
                board_id="board01",
                request_id="req01",
                timestamp=1794000000,
                filename="cube.ctb",
            )
            self.assertEqual(msg["Data"]["Cmd"], code)
            self.assertEqual(msg["Topic"], "sdcp/request/board01")
            self.assertEqual(msg["Data"]["MainboardID"], "board01")
        with self.assertRaises(Refused):
            sdcp_request(
                "start", brand_id="b", board_id="board", request_id="req", timestamp=1, filename="../cube.ctb"
            )


if __name__ == "__main__":
    unittest.main()
