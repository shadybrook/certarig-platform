"""Clean-shutdown flag. Missing file means the last process did not close."""

from __future__ import annotations

from pathlib import Path

from .atomic import write_json_atomic
from .live import utc_now


def clean_path(evidence_dir: str | Path) -> Path:
    return Path(evidence_dir) / "boot" / "clean.json"


def detect_unclean(evidence_dir: str | Path) -> bool:
    """True only if a previous process started and did not close."""
    boot = Path(evidence_dir) / "boot"
    if not boot.exists():
        return False
    return not clean_path(evidence_dir).is_file()


def mark_running(evidence_dir: str | Path) -> bool:
    """Consume the clean flag. Returns whether the previous shutdown was unclean."""
    dirty = detect_unclean(evidence_dir)
    path = clean_path(evidence_dir)
    if path.is_file():
        path.unlink()
    return dirty


def mark_clean(evidence_dir: str | Path) -> Path:
    return write_json_atomic(clean_path(evidence_dir), {"clean": True, "at": utc_now()})


def unclean(evidence_dir: str | Path) -> bool:
    return detect_unclean(evidence_dir)
