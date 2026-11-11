"""Versioned sandbox contracts shared by broker, worker and offline verifier."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path, PurePosixPath
from typing import Any

from certarig.edge.config import canonical_hash, load_config_dict
from certarig.edge.revalidation import model_revision, profile_hash
from certarig.edge.runtime import validate_procedure

CONTEXT = "colima-certarig-sandbox"
PROFILE = "certarig-sandbox"
SUITE = "commissioning-sandbox-v1"
VERIFIER = "sandbox-verifier-v1-" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
REQUIRED_CASES = ("candidate_procedure", "stale_source", "dropout", "overrange")
LIMITS = {
    "cpus": 1,
    "memory_bytes": 512 * 1024**2,
    "pids": 64,
    "analysis_s": 120,
    "rehearsal_s": 300,
    "lease_s": 900,
    "jobs": 10,
    "input_bytes": 64 * 1024**2,
    "output_bytes": 128 * 1024**2,
    "scratch_bytes": 256 * 1024**2,
    "workspace_bytes": 256 * 1024**2,
    "disk_free_bytes": 8 * 1024**3,
}
TERMINAL = {"completed", "failed", "cancelled", "timed_out", "interrupted"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def identifier(value: str, prefix: str) -> str:
    if not re.fullmatch(prefix + r"_[a-f0-9]{16}", value):
        raise ValueError("invalid sandbox identifier")
    return value


def safe_name(name: str) -> bool:
    p = PurePosixPath(name)
    return (
        bool(name)
        and not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in name
        and ":" not in name
        and str(p) == name
        and not any(ord(c) < 32 for c in name)
    )


def snapshot(
    document: dict[str, Any],
    procedure: dict[str, Any],
    base_hash: str,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Whitelist public model/control fields. Never copy transport configuration or credentials.
    document = json.loads(encoded(document))
    document.pop("config_hash", None)
    if document.get("pressure_abort_bar") == 0 and "pressure" not in document.get("abort_limits", {}):
        document.pop("pressure_abort_bar")
    try:
        config = load_config_dict(document)
        public = config.public_dict()
    except ValueError:
        # Drafts are inert analysis inputs; qualification separately checks the full schema.
        public = document
    if not isinstance(public.get("hardware"), dict) or not isinstance(public.get("channels"), list):
        raise ValueError("draft must contain hardware and channels objects")
    public.pop("config_hash", None)
    if public.get("pressure_abort_bar") == 0:
        public.pop("pressure_abort_bar")
    hw = public["hardware"]
    public["hardware"] = {k: v for k, v in hw.items() if k not in {"mqtt", "modbus"}}
    for channel in public["channels"]:
        source = channel.get("source") or {}
        channel["source"] = {k: v for k, v in source.items() if k in {"kind", "address", "topic", "index"}}
        if any(isinstance(v, str) and ("://" in v or "@" in v) for v in channel["source"].values()):
            raise ValueError("source contains an endpoint or credential; provide a public mapping identity")
    value = {
        "schema_version": 1,
        "document": public,
        "procedure": procedure,
        "base_config_hash": base_hash,
        "provenance": provenance or {},
        "evidence_kind": "simulated_experiment_not_physical_commissioning",
    }
    if len(encoded(value)) > LIMITS["input_bytes"]:
        raise ValueError("snapshot exceeds input quota")
    return value


def blockers(value: dict[str, Any]) -> list[str]:
    try:
        config = load_config_dict(value["document"])
        errors = list(validate_procedure(value["procedure"], config))
        concepts = {c.concept for c in config.channels if c.required}
        if not concepts or not concepts <= {"pressure", "flow", "temperature"}:
            errors.append("Only mapped pressure/flow and thermal profiles are qualified")
        plant = (config.hardware.simulator or {}).get("plant", "generic")
        if plant not in {"generic", "thermal_rc"}:
            errors.append("Unsupported simulator model")
        expected = {"temperature": "degc", "pressure": "bar", "flow": "l/min"}
        for c in config.channels:
            if not c.required:
                continue
            if c.unit.lower() != expected.get(c.concept):
                errors.append(f"Incompatible units: {c.channel_id}")
            if not c.calibration_id:
                errors.append(f"Missing calibration identity: {c.channel_id}")
            if not c.source or not (c.source.get("address") or c.source.get("topic")):
                errors.append(f"Missing source identity: {c.channel_id}")
        errors.extend(value.get("provenance", {}).get("blockers", []))
        return errors
    except (ValueError, KeyError, TypeError) as exc:
        return [str(exc)]


def binding(value: dict[str, Any], image: str, seed: int) -> dict[str, Any]:
    config = load_config_dict(value["document"])
    return {
        "snapshot_hash": canonical_hash(value),
        "profile_hash": profile_hash(config),
        "procedure_hash": canonical_hash(value["procedure"]),
        "model_revision": model_revision(config),
        "suite_revision": SUITE,
        "seed": seed,
        "runner_image": image,
        "verifier_revision": VERIFIER,
    }


def verify_rehearsal(value: dict[str, Any], files: dict[str, bytes]) -> dict[str, Any]:
    """Re-evaluate fixed-scenario reports AND their raw recordings, outside submitted code."""
    import csv
    import io

    from certarig.sim.invariants import check_all, events_from_rows

    problems = blockers(value)
    try:
        report = json.loads(files["rehearsal.json"])
        if report["suite_revision"] != SUITE or set(report["cases"]) != set(REQUIRED_CASES):
            raise ValueError("mandatory scenario suite is missing or changed")
        for name in REQUIRED_CASES:
            case = report["cases"][name]
            rows = list(csv.DictReader(io.StringIO(files[case["recording"]].decode())))
            if len(rows) < 2 or any(
                not all(math.isfinite(float(r[k])) for k in ("sample_index",)) for r in rows
            ):
                raise ValueError("missing/nonfinite rehearsal samples")
            checks = check_all(
                rows,
                events_from_rows(rows),
                [
                    "csv_rows_contiguous",
                    "ends_safe",
                    "no_restart_without_reset",
                    "output_off_when_process_unsafe",
                ],
            )
            if any(not r["passed"] for r in checks.values()):
                problems.append(f"Raw invariants failed: {name}")
            if name == "candidate_procedure":
                if case["run"]["status"] != "passed" or not case["passed"]:
                    problems.append("Candidate procedure did not pass")
            else:
                events = events_from_rows(rows)
                if (
                    "permit_accepted" not in events
                    or not any("forced_safe" in e for e in events)
                    or "permit_rejected_reset_required" not in events
                ):
                    problems.append(f"Fault was not excited/contained: {name}")
            if not case["passed"]:
                problems.append(f"Scenario failed: {name}")
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        problems.append(f"Incomplete rehearsal evidence: {exc}")
    return {
        "passed": not problems,
        "blockers": problems,
        "suite_revision": SUITE,
        "evidence_kind": "trusted_simulated_rehearsal_not_physical_acceptance",
    }
