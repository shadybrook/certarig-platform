"""Operator bench briefing. Typed context for evidence bundles, not a hardware map."""

from __future__ import annotations

from typing import Any

from .atomic import write_json_atomic
from .live import utc_now

FIELDS = ("p1_role", "p2_role", "estop", "relay", "diagram_notes")
NAME = "briefing.json"
_FIELD_MAX = 2000


def briefing_path(evidence_dir: Any) -> Any:
    from pathlib import Path

    return Path(evidence_dir) / NAME


def empty_briefing() -> dict[str, str]:
    return {field: "" for field in FIELDS}


def read_briefing(evidence_dir: Any) -> dict[str, Any]:
    path = briefing_path(evidence_dir)
    if not path.is_file():
        return {"present": False, "briefing": empty_briefing()}
    raw = path.read_text(encoding="utf-8")
    import json

    loaded = json.loads(raw)
    briefing = empty_briefing()
    if isinstance(loaded, dict):
        for field in FIELDS:
            briefing[field] = str(loaded.get(field) or "")[:_FIELD_MAX]
        updated = str(loaded.get("updated_at") or "")
    else:
        updated = ""
    return {"present": True, "briefing": briefing, "updated_at": updated}


def write_briefing(evidence_dir: Any, body: dict[str, Any]) -> dict[str, Any]:
    document = empty_briefing()
    for field in FIELDS:
        document[field] = str(body.get(field) or "").strip()[:_FIELD_MAX]
    document["updated_at"] = utc_now()
    write_json_atomic(briefing_path(evidence_dir), document)
    return {"present": True, "briefing": {k: document[k] for k in FIELDS}, "updated_at": document["updated_at"]}
