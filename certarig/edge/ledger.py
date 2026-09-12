"""Local outcome ledger. Not GBrain — a file the authoring wizard and Agent can read."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import write_text_atomic


def ledger_path(evidence_dir: str | Path) -> Path:
    return Path(evidence_dir) / "ledger" / "outcomes.jsonl"


def append_outcome(evidence_dir: str | Path, row: dict[str, Any]) -> Path:
    path = ledger_path(evidence_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    write_text_atomic(path, existing + json.dumps(row, sort_keys=True) + "\n")
    return path


def read_outcomes(evidence_dir: str | Path, procedure_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    path = ledger_path(evidence_dir)
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if procedure_id and item.get("procedure_id") != procedure_id:
            continue
        rows.append(item)
    return rows[-limit:]
