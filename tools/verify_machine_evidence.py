#!/usr/bin/env python3
"""Verify a machine-lab result, the audit chain, source hashes and controller shutdown."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from certarig.machines.gateway import canonical


def verify(folder: Path) -> dict:
    result = json.loads((folder / "result.json").read_text())
    assert result["result"] == "passed" and result["physical_machine"] is False
    assert result["live_llm_inference"] is False
    assert len(result["checks"]) == 12 and all(c["passed"] for c in result["checks"])
    actions = [c for c in result["checks"] if c["check"] == "agent_tool_action"]
    assert [(c["action"], c["ok"]) for c in actions] == [
        ("start", False),
        ("start", True),
        ("pause", True),
        ("resume", False),
        ("resume", True),
        ("cancel", True),
    ]
    assert any(
        c["check"] == "virtual_job_completed" and c["completion_percent"] == 100 for c in result["checks"]
    )
    previous, count = "0" * 64, 0
    for raw in (folder / "gateway-audit.jsonl").read_text().splitlines():
        row = json.loads(raw)
        digest = row.pop("hash")
        assert row["previous"] == previous
        assert digest == hashlib.sha256(canonical(row)).hexdigest()
        previous, count = digest, count + 1
    assert previous == result["audit_final_hash"]
    cleanup = json.loads((folder / "cleanup.json").read_text())
    assert cleanup["server_stopped"] is True and cleanup["server_exit_code"] == 0
    root = Path(__file__).resolve().parents[1]
    sources = json.loads((folder / "source-manifest.json").read_text())["files"]
    for name, digest in sources.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    transcript = [json.loads(row) for row in (folder / "agent-transcript.jsonl").read_text().splitlines()]
    observed_actions = [r for r in transcript if r["kind"] == "tool_result"]
    assert len(observed_actions) == 6
    return {
        "verified": True,
        "controller": result["controller"]["server"],
        "integration_checks": 12,
        "audit_records": count,
        "source_files": len(sources),
        "agent_tool_results": len(observed_actions),
        "server_stopped": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    print(json.dumps(verify(parser.parse_args().folder), indent=2))
