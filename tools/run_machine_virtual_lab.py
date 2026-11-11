#!/usr/bin/env python3
"""Verify CertaRig's agent tool loop against real OctoPrint + its bundled VIRTUAL printer.

Runs a temporary loopback server, never attaches a hardware serial port, exports
sanitized evidence, and terminates the server in finally. No paid model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import secrets
import socket
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from certarig.agent.orchestrator import AgentSession
from certarig.agent.providers.fake import FakeProvider, call, say, tool_call
from certarig.agent.transcript import Transcript
from certarig.machines.agent_tools import MachineTools
from certarig.machines.gateway import Audit, Gateway, Intent, OctoPrintVirtual


def upload(client: OctoPrintVirtual, filename: str, content: bytes) -> None:
    client.require_virtual()
    boundary = "certarig" + secrets.token_hex(12)
    data = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
    ).encode()
    data += content + f"\r\n--{boundary}--\r\n".encode()
    req = Request(
        client.base_url + "/api/files/local",
        data=data,
        method="POST",
        headers={"X-Api-Key": client._key, "Content-Type": "multipart/form-data; boundary=" + boundary},
    )
    with urlopen(req, timeout=10) as response:
        if response.status != 201:
            raise AssertionError("upload was not accepted")


def wait_state(client: OctoPrintVirtual, expected: str, checks: list, timeout: int = 30) -> dict:
    until = time.monotonic() + timeout
    last = None
    while time.monotonic() < until:
        try:
            last = client.status()
            if last["state"] == expected:
                checks.append(
                    {
                        "check": "controller_state",
                        "expected": expected,
                        "observed": last["state"],
                        "job": last["job"],
                        "passed": True,
                    }
                )
                print("Controller confirmed:", expected, flush=True)
                return last
        except (OSError, ValueError, KeyError, http.client.HTTPException):
            pass
        time.sleep(0.2)
    raise AssertionError(f"expected {expected}; last observation {last}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--octoprint-bin", default=".venv-controller/bin/octoprint")
    parser.add_argument("--out", default="evidence/machine-control/octoprint-virtual")
    args = parser.parse_args()
    output = Path(args.out)
    if output.exists():
        raise SystemExit("Output must be a new directory to preserve earlier evidence.")
    output.mkdir(parents=True)
    checks: list[dict] = []
    key = secrets.token_hex(24)
    issued_approvals: list[str] = []
    with tempfile.TemporaryDirectory(prefix="certarig-octoprint-") as tmp:
        basedir = Path(tmp)
        config = {
            "server": {
                "firstRun": False,
                "onlineCheck": {"enabled": False},
                "pluginBlacklist": {"enabled": False},
            },
            "api": {"enabled": True, "key": key},
            "accessControl": {"enabled": False},
            "serial": {"autoconnect": False, "log": False},
            "plugins": {
                "virtual_printer": {"enabled": True},
                "_disabled": ["discovery", "softwareupdate", "pluginmanager", "tracking"],
            },
        }
        config_path = basedir / "config.yaml"
        config_path.write_text(yaml.safe_dump(config))
        config_path.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        client = OctoPrintVirtual(f"http://127.0.0.1:{port}", key)
        with (basedir / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    str(Path(args.octoprint_bin).resolve()),
                    "--basedir",
                    tmp,
                    "serve",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                print("Starting real OctoPrint on loopback with temporary state", flush=True)
                until = time.monotonic() + 55
                while True:
                    if process.poll() is not None:
                        raise AssertionError("OctoPrint exited during startup")
                    try:
                        version = client.request("GET", "/api/version")
                        break
                    except (OSError, ValueError, http.client.HTTPException):
                        if time.monotonic() > until:
                            raise AssertionError("OctoPrint startup timed out") from None
                        time.sleep(0.5)
                print("OctoPrint version:", version, flush=True)
                client.request(
                    "POST",
                    "/api/connection",
                    {"command": "connect", "port": "VIRTUAL", "baudrate": 115200, "save": False},
                )
                wait_state(client, "Operational", checks)
                job = b"; CertaRig VIRTUAL-only integration job; no heat or spindle\nG21\nG90\n"
                job += b"G4 P500\n" * 80
                digest = hashlib.sha256(job).hexdigest()
                upload(client, "certarig-virtual.gcode", job)
                audit = Audit(output / "gateway-audit.jsonl")
                gateway = Gateway("octoprint-virtual-01", client, audit)
                tools = MachineTools(gateway)
                transcript_path = basedir / "agent-private.jsonl"
                transcript = Transcript(transcript_path)

                def agent_action(action: str, approve: bool, expected_ok: bool = True) -> None:
                    intent = Intent(gateway.machine_id, action, "certarig-virtual.gcode", digest)
                    arguments = asdict(intent)
                    if approve:
                        approval = gateway.approve(intent, actor="automated_test_harness")
                        issued_approvals.append(approval)
                        arguments["approval_id"] = approval
                    provider = FakeProvider(
                        script=[
                            call(tool_call("machine_command", arguments)),
                            say("Finished the controller request; inspect tool evidence."),
                        ]
                    )
                    session = AgentSession(
                        provider,
                        tools,
                        transcript,
                        system_prompt="Operate only through commissioned machine tools.",
                    )
                    turn = session.send(f"{action} the approved virtual job")
                    if len(turn.tool_results) != 1 or turn.tool_results[0].ok != expected_ok:
                        raise AssertionError(f"unexpected agent result for {action}: {turn.to_dict()}")
                    checks.append(
                        {
                            "check": "agent_tool_action",
                            "action": action,
                            "approved_by_test_harness": approve,
                            "ok": expected_ok,
                            "result": turn.tool_results[0].result,
                            "passed": True,
                        }
                    )
                    print(
                        "Agent tool verified:", action, "accepted" if expected_ok else "refused", flush=True
                    )

                agent_action("start", False, expected_ok=False)
                agent_action("start", True)
                wait_state(client, "Printing", checks)
                agent_action("pause", False)
                wait_state(client, "Paused", checks)
                agent_action("resume", False, expected_ok=False)
                agent_action("resume", True)
                wait_state(client, "Printing", checks)
                agent_action("cancel", False)
                wait_state(client, "Operational", checks)
                # Also prove completion of a short second job, rather than only accepted API writes.
                short = b"; CertaRig VIRTUAL-only completion check\nG21\nG90\nG4 P100\nM400\n"
                upload(client, "certarig-complete.gcode", short)
                finish = Intent(
                    gateway.machine_id, "start", "certarig-complete.gcode", hashlib.sha256(short).hexdigest()
                )
                gateway.execute(finish, gateway.approve(finish, actor="automated_test_harness"))
                until = time.monotonic() + 30
                complete = None
                while time.monotonic() < until:
                    complete = client.request("GET", "/api/job")
                    if (
                        complete.get("state") == "Operational"
                        and (complete.get("progress", {}).get("completion") or 0) >= 100
                    ):
                        break
                    time.sleep(0.2)
                else:
                    raise AssertionError(f"short job did not complete: {complete}")
                checks.append(
                    {
                        "check": "virtual_job_completed",
                        "state": complete["state"],
                        "completion_percent": complete["progress"]["completion"],
                        "passed": True,
                    }
                )
                public_transcript = transcript_path.read_text()
                for secret in [key, *issued_approvals]:
                    public_transcript = public_transcript.replace(secret, "[REDACTED_LAB_CREDENTIAL]")
                (output / "agent-transcript.jsonl").write_text(public_transcript)
                manifest = {
                    "result": "passed",
                    "controller": version,
                    "physical_machine": False,
                    "agent_provider": "fake-scripted",
                    "live_llm_inference": False,
                    "operator_approvals": "automated_test_harness_only",
                    "checks": checks,
                    "audit_final_hash": audit.previous,
                    "job_sha256": digest,
                    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                    "source_state": "uncommitted research additions; see source-manifest.json",
                }
                (output / "result.json").write_text(json.dumps(manifest, indent=2) + "\n")
                source_root = Path(__file__).resolve().parents[1]
                source_files = sorted((source_root / "certarig/machines").glob("*.py")) + [
                    Path(__file__).resolve(),
                    source_root / "tests/unit/test_machine_gateway.py",
                ]
                (output / "source-manifest.json").write_text(
                    json.dumps(
                        {
                            "files": {
                                str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in source_files
                            }
                        },
                        indent=2,
                    )
                    + "\n"
                )
                print("PASS:", len(checks), "checks; virtual job completed at 100%", flush=True)
            except Exception:
                tail = (basedir / "server.log").read_text()[-12000:].replace(key, "[REDACTED]")
                print(tail, flush=True)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                (output / "cleanup.json").write_text(
                    json.dumps(
                        {
                            "server_exit_code": process.returncode,
                            "server_stopped": process.poll() is not None,
                            "temporary_credentials_retained": False,
                        }
                    )
                    + "\n"
                )


if __name__ == "__main__":
    main()
