"""Operator attestations backed by immutable, hash-checked local qualification files."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .server import HttpError

OBSERVATION_CHECKS = {"mapping", "unpowered_wiring", "electrical_limits", "calibration"}
TRIAL_CHECKS = OBSERVATION_CHECKS | {"independent_cutoff", "feedback_response"}
ACCEPTANCE_CHECKS = TRIAL_CHECKS | {"estop_recovery", "controlled_trial"}


def checked_file(root: Path, reference: dict[str, Any]) -> bytes:
    name = reference.get("path")
    if not isinstance(name, str):
        raise ValueError("Evidence path required")
    relative = Path(name)
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or any(part.is_symlink() for part in [path, *path.parents])
        or not path.is_file()
        or path.stat().st_size > 2_000_000
    ):
        raise ValueError("Evidence must be a bounded regular file inside this evidence root")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != reference.get("sha256"):
        raise ValueError("Qualification evidence checksum mismatch")
    return data


def inspect_evidence(
    root: Path, checks: Any, config_hash: str, wiring_revision: str, stage: str
) -> list[dict[str, Any]]:
    required = {"observation": OBSERVATION_CHECKS, "trial": TRIAL_CHECKS, "accepted": ACCEPTANCE_CHECKS}[
        stage
    ]
    if not isinstance(checks, dict) or not required.issubset(checks):
        raise ValueError("Missing physical checks: " + ", ".join(sorted(required)))
    files: dict[str, dict[str, Any]] = {}
    for key in sorted(required):
        reference = checks[key]
        data = checked_file(root, reference)
        record = json.loads(data)
        if (
            record.get("check") != key
            or record.get("passed") is not True
            or record.get("evidence_kind") != "physical"
            or record.get("config_hash") != config_hash
            or record.get("wiring_revision") != wiring_revision
        ):
            raise ValueError(f"Physical check {key} has wrong identity, status or evidence kind")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"Physical check {key} requires raw supporting artifacts")
        for ref in [reference, *artifacts]:
            payload = checked_file(root, ref)
            files[ref["path"]] = {**ref, "data_base64": base64.b64encode(payload).decode()}
            if len(files) > 32 or sum(len(f["data_base64"]) for f in files.values()) > 16_000_000:
                raise ValueError("Qualification evidence exceeds portable review limits")
    return list(files.values())


def review_physical(service: Any, ctx: Any) -> tuple[int, dict[str, Any]]:
    node = service.node
    node._require_operator(ctx)
    config = node.config
    stage = ctx.body.get("stage")
    if config.hardware.mode != "raspberry_pi" or stage not in {"observation", "trial", "accepted"}:
        raise HttpError(400, "Physical review requires a Pi profile and observation/trial/accepted stage")
    if (
        not config.commissioning_required
        or ctx.body.get("expected_config_hash") != config.config_hash
        or not config.wiring_revision
        or ctx.body.get("wiring_revision") != config.wiring_revision
    ):
        raise HttpError(409, "Physical review requires the exact commissioning profile and wiring revision")
    if ctx.body.get("attest_reviewed") is not True:
        raise HttpError(400, "Explicit human review attestation required")
    ids = ctx.body.get("procedure_ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(pid, str) for pid in ids):
        raise HttpError(400, "procedure_ids must be a nonempty list")
    with service._lock:
        try:
            evidence = inspect_evidence(
                node.runtime.evidence_dir,
                ctx.body.get("checks"),
                config.config_hash,
                config.wiring_revision,
                stage,
            )
            procedures = {}
            for pid in ids:
                proc = node.extensions["procedures"].library.get(pid)
                readiness = service.readiness(pid, reviewed=False)
                problems = [
                    b for b in readiness["blockers"] if b != "Physical commissioning has not been accepted"
                ]
                if proc is None or problems:
                    raise ValueError("Physical observations/procedure are not ready: " + "; ".join(problems))
                if stage == "observation" and proc.requires_output:
                    raise ValueError("Observation review cannot qualify output procedures")
                if stage != "observation":
                    from .twin_gate import check_gate

                    if (
                        not config.hardware.feedback_required
                        or node.runtime.state().get("outputs", {}).get("feedback_source") != "electrical_gpio"
                    ):
                        raise ValueError("Measured electrical feedback must be required and observed")
                    refusal = check_gate(
                        node.runtime.evidence_dir, proc.procedure_hash, "raspberry_pi", config=config
                    )
                    if refusal:
                        raise ValueError(str(refusal["error"]))
                procedures[pid] = proc.procedure_hash
            if stage == "accepted":
                previous = service.current()
                if (
                    not previous
                    or previous.get("stage") != "trial"
                    or previous.get("session_id") != service.session_id
                    or previous.get("expires_at_unix", 0) < time.time()
                ):
                    raise ValueError("Current attended trial review required before acceptance")
                runner = node.extensions["procedures"].runner
                passed = {
                    r["procedure_id"]
                    for r in runner.list()
                    if r.get("status") == "passed"
                    and runner.get(r["run_id"]).config_hash == config.config_hash
                    and r.get("hardware_mode") == "raspberry_pi"
                }
                if not set(ids).issubset(passed):
                    raise ValueError("Each accepted procedure needs a passing physical trial")
            record = {
                "schema_version": 1,
                "rig_id": config.rig_id,
                "config_hash": config.config_hash,
                "adapter_identity": service.identity(),
                "reviewed_by": ctx.principal_name,
                "reviewed_at": datetime.now(UTC).isoformat(),
                "evidence_kind": "physical_review_attestation",
                "physical_commissioned": stage == "accepted",
                "procedures": procedures,
                "stage": stage,
                "wiring_revision": config.wiring_revision,
                "session_id": service.session_id,
                "expires_at_unix": time.time() + 1800 if stage == "trial" else None,
                "checks": ctx.body["checks"],
                "qualification_evidence": evidence,
            }
            from .atomic import write_json_atomic
            from .schemas import validate_against_schema

            validate_against_schema(record, "commissioning.schema.json")
            write_json_atomic(
                service.root / "history" / f"{config.config_hash}-{time.time_ns()}.json", record
            )
            write_json_atomic(service.root / f"{config.config_hash}.json", record)
        except (ValueError, KeyError, TypeError) as exc:
            raise HttpError(409, str(exc)) from exc
    return 201, service.readiness(ids[0])
