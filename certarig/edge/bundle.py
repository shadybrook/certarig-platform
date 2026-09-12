"""Per-run evidence bundle: manifest, SHA256SUMS, report.md, events JSONL."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from certarig import __version__
from certarig.edge.ops import sha256_file, write_sums
from certarig.edge.schemas import validate_against_schema

MANIFEST_NAME = "manifest.json"
SUMS_NAME = "SHA256SUMS.txt"
REPORT_NAME = "report.md"
EVENTS_NAME = "events.jsonl"

REPORT_TEMPLATE = """# {title}

- Procedure `{procedure_id}` hash `{procedure_hash}`
- Run `{run_id}` · **{status}** · {outcome_reason}
- Rig `{rig_id}` ({hardware_mode}) config `{config_hash}`
- Contract `{contract_hash}`
- CertaRig {certarig_version}

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
{step_rows}

## Checks

{check_rows}

## Kernel events

{kernel_rows}

## Recording

{recording}

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

{narrative}

## Recovery

{recovery}
"""


def _step_rows(run: dict[str, Any]) -> str:
    lines = []
    for step in run.get("steps", []):
        detail = step.get("reason") or step.get("instruction") or ""
        lines.append(
            f"| {step.get('step_id')} | {step.get('type')} | {step.get('status')} | {str(detail).replace('|', '/')} |"
        )
    return "\n".join(lines) or "| — | — | — | — |"


def _check_rows(run: dict[str, Any]) -> str:
    checks = run.get("checks") or []
    if not checks:
        return "_No evaluate checks._"
    return "\n".join(f"- {'PASS' if c.get('passed') else 'FAIL'}: {c.get('check')}" for c in checks)


def render_report(run: dict[str, Any], context: dict[str, Any], narrative: str = "") -> str:
    recording = run.get("recording") or {}
    rec = (
        f"`{recording.get('filename')}` · {recording.get('samples')} samples · sha256 `{recording.get('sha256')}`"
        if recording
        else "_No CSV recording._"
    )
    events = run.get("kernel_events") or []
    kernel = "\n".join(f"- `{e.get('event', e) if isinstance(e, dict) else e}`" for e in events) or "_None._"
    return REPORT_TEMPLATE.format(
        title=context.get("title") or run.get("procedure_id") or "Procedure run",
        procedure_id=run.get("procedure_id"),
        procedure_hash=run.get("procedure_hash"),
        run_id=run.get("run_id"),
        status=run.get("status"),
        outcome_reason=run.get("outcome_reason") or "",
        rig_id=context.get("rig_id"),
        hardware_mode=context.get("hardware_mode"),
        config_hash=str(context.get("config_hash", ""))[:16],
        contract_hash=str(context.get("contract_hash", ""))[:16],
        certarig_version=__version__,
        step_rows=_step_rows(run),
        check_rows=_check_rows(run),
        kernel_rows=kernel,
        recording=rec,
        narrative=narrative or "_No agent narrative was attached._",
        recovery=(run.get("recovery") or "_None._").strip(),
    )


def write_run_bundle(
    target: Path,
    run: dict[str, Any],
    context: dict[str, Any],
    narrative: str = "",
) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    events = run.get("events") or run.get("kernel_events") or []
    (target / EVENTS_NAME).write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in events), encoding="utf-8"
    )
    (target / REPORT_NAME).write_text(render_report(run, context, narrative), encoding="utf-8")
    listed = [
        path
        for path in sorted(target.iterdir())
        if path.is_file() and path.name not in {MANIFEST_NAME, SUMS_NAME}
    ]
    files = [{"path": p.name, "sha256": sha256_file(p), "size": p.stat().st_size} for p in listed]
    manifest = {
        "kind": "certarig_run_bundle",
        "certarig_version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "run_id": run.get("run_id"),
        "procedure_id": run.get("procedure_id"),
        "procedure_hash": run.get("procedure_hash"),
        "status": run.get("status"),
        "outcome_reason": run.get("outcome_reason"),
        "seed": context.get("seed"),
        "files": files,
        "rig_id": context.get("rig_id") or run.get("rig_id") or "unknown",
        "hardware_mode": context.get("hardware_mode") or run.get("hardware_mode") or "unknown",
        "config_hash": context.get("config_hash") or "unspecified",
        "manifest_hash": context.get("manifest_hash") or "unspecified",
        "contract_hash": context.get("contract_hash") or "unspecified",
    }
    validate_against_schema(manifest, "evidence_manifest.schema.json", ValueError)
    (target / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (target / SUMS_NAME).write_text(
        write_sums([(str(f["path"]), str(f["sha256"])) for f in files]), encoding="utf-8"
    )
    return manifest


def canonicalize(document: Any) -> Any:
    """Drop timestamps and run ids so two seeded runs can be compared."""
    skip = {
        "run_id",
        "started_at",
        "ended_at",
        "at",
        "created_at",
        "captured_at",
        "last_event_at",
        "evidence_dir",
        "filename",
        "sha256",
        "elapsed_ms",
        "requested_by",
        "label",
    }
    if isinstance(document, list):
        return [canonicalize(item) for item in document]
    if not isinstance(document, dict):
        return document
    return {k: canonicalize(v) for k, v in document.items() if k not in skip}
