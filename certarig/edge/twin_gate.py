"""Digital-twin gate: a bench procedure may run only if the same hash passed in sim recently."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

WINDOW_S = 24 * 3600


def _path(evidence_dir: Path, procedure_hash: str) -> Path:
    return evidence_dir / "twin_gate" / f"{procedure_hash}.json"


def record_sim_pass(evidence_dir: Path, procedure_id: str, procedure_hash: str, run_id: str) -> Path:
    target = _path(evidence_dir, procedure_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "procedure_id": procedure_id,
        "procedure_hash": procedure_hash,
        "run_id": run_id,
        "passed_at": datetime.now(UTC).isoformat(),
        "passed_at_unix": time.time(),
    }
    target.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return target


def check_gate(
    evidence_dir: Path,
    procedure_hash: str,
    hardware_mode: str,
    window_s: int = WINDOW_S,
    now: float | None = None,
) -> dict[str, Any] | None:
    """Return None if the run may start; otherwise a refusal payload."""
    if hardware_mode != "raspberry_pi":
        return None
    path = _path(evidence_dir, procedure_hash)
    if not path.is_file():
        return {
            "error": "digital-twin gate: this procedure hash has not passed on the simulator",
            "code": "twin_gate",
            "procedure_hash": procedure_hash,
        }
    document = json.loads(path.read_text(encoding="utf-8"))
    age = (now if now is not None else time.time()) - float(document.get("passed_at_unix") or 0)
    if age > window_s:
        return {
            "error": f"digital-twin gate: last simulator pass is {age / 3600:.1f} h old (limit {window_s / 3600:.0f} h)",
            "code": "twin_gate_stale",
            "procedure_hash": procedure_hash,
            "last_pass": document,
        }
    return None
