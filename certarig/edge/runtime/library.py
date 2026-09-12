"""Procedure loading, validation against the schema and against a rig, and the library."""

from __future__ import annotations

import builtins
import json
import threading
from pathlib import Path
from typing import Any

import yaml

from ..models import RigConfig
from ..schemas import schema_errors
from .facts import concept_index
from .model import Procedure
from .predicates import referenced_signals


class ProcedureValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def _semantic_errors(raw: dict[str, Any], config: RigConfig | None) -> list[str]:
    errors: list[str] = []
    steps = raw.get("steps", [])
    ids = [str(step.get("id")) for step in steps]
    duplicates = sorted({step_id for step_id in ids if ids.count(step_id) > 1})
    if duplicates:
        errors.append(f"duplicate step ids: {', '.join(duplicates)}")
    known_steps = set(ids)
    for check in raw.get("evaluate", []):
        target = check.get("step_passed") or check.get("step")
        if target and target not in known_steps:
            errors.append(f"evaluate references unknown step {target!r}")
    record_open = False
    for step in steps:
        if step.get("type") == "record":
            if step["action"] == "start":
                if record_open:
                    errors.append(f"step {step['id']}: recording already started")
                record_open = True
            elif step["action"] == "stop":
                if not record_open:
                    errors.append(f"step {step['id']}: no recording to stop")
                record_open = False
    if raw.get("record", True) and any(step.get("type") == "record" for step in steps):
        errors.append("record: true (whole-run recording) cannot be combined with record steps")

    if config is not None:
        index = concept_index(config)
        names: set[str] = set()
        for predicate in raw.get("preconditions", []):
            names |= referenced_signals(predicate)
        for step in steps:
            for key in ("predicate", "expect", "confirm"):
                if key in step:
                    names |= referenced_signals(step[key])
        for check in raw.get("evaluate", []):
            if "signal" in check:
                names.add(str(check["signal"]))
        unknown = sorted(name for name in names if name not in index)
        if unknown:
            errors.append(f"unknown signals for rig {config.rig_id}: {', '.join(unknown)}")
        applies = raw.get("applies_to", {})
        concepts = {channel.concept for channel in config.channels} | {"emergency_stop"}
        missing = sorted(set(applies.get("concepts", [])) - concepts)
        if missing:
            errors.append(f"rig lacks required concepts: {', '.join(missing)}")
        actuators = {"permit_relay"}
        missing_actuators = sorted(set(applies.get("actuators", [])) - actuators)
        if missing_actuators:
            errors.append(f"rig lacks required actuators: {', '.join(missing_actuators)}")
        modes = applies.get("hardware_modes")
        if modes and config.hardware.mode not in modes:
            errors.append(f"procedure does not apply to hardware mode {config.hardware.mode}")
    return errors


def validate_procedure(raw: Any, config: RigConfig | None = None) -> list[str]:
    """Return all schema and semantic errors (empty list means valid)."""
    if not isinstance(raw, dict):
        return ["procedure must be a mapping"]
    errors = schema_errors(raw, "procedure.schema.json")
    if errors:
        return errors
    return _semantic_errors(raw, config)


def load_procedure_file(
    path: str | Path, config: RigConfig | None = None, approved: bool = True
) -> Procedure:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    raw = yaml.safe_load(text) if source.suffix in {".yaml", ".yml"} else json.loads(text)
    errors = validate_procedure(raw, config)
    if errors:
        raise ProcedureValidationError([f"{source.name}: {error}" for error in errors])
    return Procedure.from_dict(raw, source=str(source), approved=approved)


class ProcedureLibrary:
    """Approved procedures plus unapproved drafts, keyed by id."""

    def __init__(self, config: RigConfig, drafts_dir: Path | None = None) -> None:
        self.config = config
        self.drafts_dir = drafts_dir
        self._lock = threading.Lock()
        self._approved: dict[str, Procedure] = {}
        self._drafts: dict[str, Procedure] = {}
        self.skipped: list[dict[str, str]] = []
        self._reload_drafts()

    def load_directory(self, root: str | Path) -> list[Procedure]:
        loaded: list[Procedure] = []
        for path in sorted(Path(root).rglob("procedure.y*ml")):
            try:
                procedure = load_procedure_file(path, self.config)
            except ProcedureValidationError as exc:
                self.skipped.append({"path": str(path), "errors": str(exc)})
                continue
            self.add(procedure)
            loaded.append(procedure)
        return loaded

    def add(self, procedure: Procedure) -> None:
        with self._lock:
            existing = self._approved.get(procedure.id)
            if existing is None or existing.version <= procedure.version:
                self._approved[procedure.id] = procedure

    def _reload_drafts(self) -> None:
        if self.drafts_dir is None or not self.drafts_dir.is_dir():
            return
        for path in sorted(self.drafts_dir.glob("*.y*ml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            try:
                draft = Procedure.from_dict(raw, source=f"disk:{path.name}", approved=False)
            except Exception:
                continue
            self._drafts.setdefault(draft.procedure_hash, draft)

    def get(self, procedure_id: str) -> Procedure | None:
        with self._lock:
            return self._approved.get(procedure_id)

    def list(self) -> builtins.list[dict[str, Any]]:
        with self._lock:
            return [item.summary() for item in sorted(self._approved.values(), key=lambda p: p.id)]

    # ------------------------------------------------------------- drafts
    def add_draft(self, raw: dict[str, Any], author: str) -> Procedure:
        errors = validate_procedure(raw, self.config)
        if errors:
            raise ProcedureValidationError(errors)
        draft = Procedure.from_dict(raw, source=f"draft:{author}", approved=False)
        with self._lock:
            self._drafts[draft.procedure_hash] = draft
        if self.drafts_dir is not None:
            self.drafts_dir.mkdir(parents=True, exist_ok=True)
            (self.drafts_dir / f"{draft.id}-{draft.procedure_hash[:12]}.yaml").write_text(
                yaml.safe_dump(raw, sort_keys=False), encoding="utf-8"
            )
        return draft

    def drafts(self) -> builtins.list[dict[str, Any]]:
        with self._lock:
            return [item.summary() for item in self._drafts.values()]

    def draft(self, procedure_hash: str) -> Procedure | None:
        with self._lock:
            return self._drafts.get(procedure_hash)

    def approve_draft(self, procedure_hash: str, approver: str) -> Procedure:
        with self._lock:
            draft = self._drafts.pop(procedure_hash, None)
        if draft is None:
            raise KeyError(procedure_hash)
        approved = Procedure.from_dict(draft.raw, source=f"approved:{approver}", approved=True)
        self.add(approved)
        return approved

    def reject_draft(self, procedure_hash: str) -> None:
        with self._lock:
            if procedure_hash not in self._drafts:
                raise KeyError(procedure_hash)
            del self._drafts[procedure_hash]
