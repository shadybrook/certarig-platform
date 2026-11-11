"""Deterministic fixture-agent demo. Requires a qualified real sandbox runtime."""

from __future__ import annotations

import argparse
import copy
import json
import os
import time
from pathlib import Path

from certarig.agent.tools import ToolRegistry
from certarig.edge.client import EdgeClient
from certarig.sandbox.evidence import verify


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18083")
    parser.add_argument("--output", type=Path, default=Path("outputs/sandbox-demo"))
    args = parser.parse_args()
    client = EdgeClient(
        args.url,
        agent_key=os.environ.get("CERTARIG_AGENT_KEY"),
        principal_name="deterministic-sandbox-fixture",
    )
    check = client.sandbox_preflight()
    if not check["ready"]:
        print(
            json.dumps(
                {"demo_started": False, "runtime_qualified": False, "blockers": check["blockers"]}, indent=2
            )
        )
        raise SystemExit(2)
    tools = ToolRegistry(client)
    created = tools.execute("sandbox_experiment", {"action": "create", "source": "thermal"})
    if not created.ok:
        raise SystemExit(json.dumps(created.result))
    sid = created.result["sandbox_id"]
    w = client.sandbox(sid)
    correct = w["snapshot"]["document"]
    bad = copy.deepcopy(correct)
    bad["channels"][0]["unit"] = "bar"
    client.revise_sandbox(sid, 0, bad)
    refused = tools.execute("sandbox_experiment", {"action": "run", "sandbox_id": sid, "kind": "rehearsal"})
    if refused.ok:
        raise AssertionError("Invalid units were accepted")
    client.revise_sandbox(sid, 1, correct)

    def run(kind: str, source: str = "") -> dict:
        result = tools.execute(
            "sandbox_experiment", {"action": "run", "sandbox_id": sid, "kind": kind, "source": source}
        )
        if not result.ok:
            raise RuntimeError(result.result)
        jid = result.result["job_id"]
        deadline = time.monotonic() + 310
        while time.monotonic() < deadline:
            job = client.sandbox_job(sid, jid)
            if job["status"] not in {"queued", "running"}:
                if job["status"] != "completed":
                    raise RuntimeError(job)
                return job
            time.sleep(0.25)
        raise TimeoutError("Sandbox job did not finish")

    examples = Path(__file__).resolve().parents[1] / "docs/sandbox/examples"
    analysis = run("python", (examples / "thermal_analysis.py").read_text())
    spice = run("spice", (examples / "flyback_protection.cir").read_text())
    if not {"analysis.json", "analysis.png"} <= set(analysis["artifacts"]):
        raise AssertionError("Thermal experiment did not produce its report and plot")
    if "protection-trace.txt" not in spice["artifacts"]:
        raise AssertionError("SPICE completion did not produce the required protection trace")
    job = run("rehearsal")
    if not job["qualification"]:
        raise AssertionError(job["receipt"]["verification"])
    proposal = client.propose_sandbox(sid, job["job_id"])
    args.output.mkdir(parents=True, exist_ok=True)
    bundle = args.output / (sid + ".zip")
    bundle.write_bytes(client.export_sandbox(sid))
    checked = verify(bundle)
    if not checked["ok"]:
        raise AssertionError(checked)
    print(
        json.dumps(
            {
                "agent_kind": "deterministic_fixture_not_live_model_qualification",
                "sandbox_id": sid,
                "bad_mapping_refused": True,
                "trusted_rehearsal_passed": True,
                "proposal_id": proposal["proposal_id"],
                "configuration_applied": False,
                "physical_authority": "none",
                "bundle": str(bundle),
                "verification": checked,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
