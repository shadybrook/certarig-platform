"""Broker-owned, fixed agent-trace verification; no submitted code or live model credentials."""

from __future__ import annotations

import json
import secrets
import threading
from typing import Any

from certarig.edge.atomic import write_bytes_atomic, write_json_atomic
from certarig.platform.contracts import encoded, fingerprint, verify_trace

from .contracts import digest, identifier, safe_name
from .engine import policy_hash


def call(broker: Any, method: str, owner: str, body: dict[str, Any]) -> dict[str, Any]:
    if method == "agent_evaluation_validate":
        receipt = body["receipt"]
        identifier(receipt["job_id"], "job")
        record = broker.root / "agent-evaluations" / (receipt["job_id"] + ".json")
        if not record.is_file() or record.is_symlink():
            raise ValueError("Missing trusted evaluation record")
        value = json.loads(record.read_text())
        if (
            value["owner"] != owner
            or value["receipt"] != receipt
            or receipt["runner_image"] != broker.engine.current_image
            or receipt["policy_hash"] != policy_hash()
            or value["status"] != "completed"
        ):
            raise ValueError("Evaluation binding or verifier policy changed")
        for name, expected in receipt["artifact_hashes"].items():
            if not safe_name(name) or "/" in name:
                raise ValueError("Unsafe evaluation artifact")
            raw = record.parent / receipt["job_id"] / name
            if raw.is_symlink() or not raw.is_file() or digest(raw.read_bytes()) != expected:
                raise ValueError("Missing or corrupt required evaluation artifact")
        trace = json.loads(record.with_suffix(".trace").read_bytes())
        if verify_trace(trace) != receipt["verification"]:
            raise ValueError("Evaluation trace changed")
        return dict(receipt)
    if not broker.engine.preflight()["ready"]:
        raise ValueError("Qualified Sandbox unavailable; no host verification fallback")
    trace = body["trace"]
    payload = encoded(trace)
    if len(payload) > 2 * 1024**2:
        raise ValueError("Evaluation trace exceeds quota")
    job_id = "job_" + secrets.token_hex(8)
    path = broker.root / "agent-evaluations" / (job_id + ".json")
    broker._admit(len(payload) + 1024**2)
    write_bytes_atomic(path.with_suffix(".trace"), payload)
    write_json_atomic(path, {"owner": owner, "job_id": job_id, "status": "running"})
    cancel = broker.events[job_id] = threading.Event()
    try:
        if not broker.slot.acquire(blocking=False):
            raise ValueError("Sandbox worker busy")
        try:
            outcome = broker.engine.run(job_id, "agent_evaluation", {"trace.json": payload}, 120, cancel)
        finally:
            broker.slot.release()
        if outcome["status"] != "completed" or cancel.is_set():
            raise ValueError("Sandbox verification interrupted")
        verification = verify_trace(trace)
        reported = json.loads(outcome["files"]["evaluation.json"])
        if reported != verification or broker.engine.current_image != broker.engine.image:
            raise ValueError("Worker verification or runner identity mismatch")
        receipt = {
            "job_id": job_id,
            "runner_image": broker.engine.image,
            "policy_hash": policy_hash(),
            "verification": verification,
            "trace_hash": fingerprint(trace),
            "at": broker.clock(),
            "resource": outcome["resource"],
            "artifact_hashes": {name: digest(raw) for name, raw in outcome["files"].items()},
            "worker_report": reported,
        }
        for name, raw in outcome["files"].items():
            if not safe_name(name) or "/" in name:
                raise ValueError("Unsafe evaluation artifact")
            write_bytes_atomic(path.parent / job_id / name, raw)
        write_json_atomic(
            path,
            {
                "owner": owner,
                "job_id": job_id,
                "status": "completed",
                "receipt": receipt,
                "resource": outcome["resource"],
            },
        )
        return receipt
    except Exception:
        write_json_atomic(path, {"owner": owner, "job_id": job_id, "status": "failed"})
        raise
    finally:
        broker.events.pop(job_id, None)
