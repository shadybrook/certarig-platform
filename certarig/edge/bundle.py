"""Per-run evidence bundle: manifest, SHA256SUMS, report.md, events JSONL."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from certarig import __version__
from certarig.edge.atomic import write_json_atomic, write_text_atomic
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
- Hardware `{hardware_identity}`
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

## Bench briefing

{briefing}

## Commissioning interview

{interview}

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


def _skill_extra(run: dict[str, Any], context: dict[str, Any]) -> str:
    procedure_id = str(run.get("procedure_id") or "")
    root = Path(context["skills_root"]) if context.get("skills_root") else Path(__file__).resolve().parents[2] / "skills"
    if not procedure_id or not root.is_dir():
        return ""
    for path in root.rglob("report.md"):
        if path.parent.name == procedure_id:
            text = path.read_text(encoding="utf-8")
            try:
                return "\n" + text.format_map(_SafeMap(context))
            except Exception:
                return "\n" + text
    return ""


class _SafeMap(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def _briefing_block(target: Path, context: dict[str, Any]) -> str:
    source = context.get("briefing")
    if not isinstance(source, dict):
        candidates = []
        root = context.get("evidence_root")
        if root:
            candidates.append(Path(root) / "briefing.json")
        candidates.append(target.parent.parent / "briefing.json")
        for path in candidates:
            if path.is_file():
                source = json.loads(path.read_text(encoding="utf-8"))
                break
        else:
            source = None
    if not source:
        return "_No bench briefing was saved._"
    write_json_atomic(target / "briefing.json", source)
    lines = []
    for key in ("p1_role", "p2_role", "estop", "relay", "diagram_notes"):
        value = str(source.get(key) or "").strip() or "_empty_"
        lines.append(f"- **{key}**: {value.replace('|', '/')}")
    if source.get("updated_at"):
        lines.append(f"- updated_at: `{source['updated_at']}`")
    return "\n".join(lines)


def _interview_block(target: Path, context: dict[str, Any]) -> str:
    source = context.get("interview")
    if not isinstance(source, dict):
        candidates = []
        root = context.get("evidence_root")
        if root:
            candidates.append(Path(root) / "interview.json")
        candidates.append(target.parent.parent / "interview.json")
        for path in candidates:
            if path.is_file():
                source = json.loads(path.read_text(encoding="utf-8"))
                break
        else:
            source = None
    if not source:
        return "_No commissioning interview was saved._"
    write_json_atomic(target / "interview.json", source)
    answers = source.get("answers") if isinstance(source.get("answers"), dict) else {}
    lines = [f"- **status**: {source.get('status') or 'unknown'}"]
    for key in ("modules", "signals", "observe_only", "diagram"):
        value = str(answers.get(key) or "").strip() or "_empty_"
        lines.append(f"- **{key}**: {value.replace('|', '/')}")
    for row in source.get("signals") or []:
        if isinstance(row, dict):
            lines.append(
                f"- {row.get('customer_name') or row.get('concept')} "
                f"{row.get('concept')} {row.get('trip')} {row.get('unit')}"
            )
    if source.get("updated_at"):
        lines.append(f"- updated_at: `{source['updated_at']}`")
    return "\n".join(lines)


def render_report(
    run: dict[str, Any],
    context: dict[str, Any],
    narrative: str = "",
    briefing: str = "",
    interview: str = "",
) -> str:
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
        briefing=briefing or "_No bench briefing was saved._",
        interview=interview or "_No commissioning interview was saved._",
        narrative=narrative or "_No agent narrative was attached._",
        recovery=(run.get("recovery") or "_None._").strip(),
        hardware_identity=context.get("hardware_identity") or context.get("hardware_mode") or "unknown",
    ) + _skill_extra(run, context)


def write_run_bundle(
    target: Path,
    run: dict[str, Any],
    context: dict[str, Any],
    narrative: str = "",
) -> dict[str, Any]:
    target.mkdir(parents=True, exist_ok=True)
    events = run.get("events") or run.get("kernel_events") or []
    write_text_atomic(target / EVENTS_NAME, "".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
    briefing = _briefing_block(target, context)
    interview = _interview_block(target, context)
    write_text_atomic(
        target / REPORT_NAME,
        render_report(run, context, narrative, briefing=briefing, interview=interview),
    )
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
        "hardware_identity": context.get("hardware_identity") or context.get("hardware_mode"),
    }
    validate_against_schema(manifest, "evidence_manifest.schema.json", ValueError)
    write_json_atomic(target / MANIFEST_NAME, manifest)
    write_text_atomic(target / SUMS_NAME, write_sums([(str(f["path"]), str(f["sha256"])) for f in files]))
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
