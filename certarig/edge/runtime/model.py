"""Procedure and run data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from ..config import canonical_hash


class RunStatus(StrEnum):
    PENDING = "pending"
    PREFLIGHT = "preflight"
    RUNNING = "running"
    AWAITING_OPERATOR = "awaiting_operator"
    PASSED = "passed"
    FAILED = "failed"
    ABORTED = "aborted"

    @property
    def terminal(self) -> bool:
        return self in {RunStatus.PASSED, RunStatus.FAILED, RunStatus.ABORTED}


@dataclass(frozen=True)
class Step:
    id: str
    type: str
    raw: dict[str, Any]

    @property
    def title(self) -> str:
        return str(self.raw.get("title") or self.id)

    @property
    def allow_estop(self) -> bool:
        return bool(self.raw.get("allow_estop", False))


@dataclass(frozen=True)
class Procedure:
    id: str
    version: int
    title: str
    raw: dict[str, Any]
    procedure_hash: str
    source: str
    approved: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source: str = "inline", approved: bool = True) -> Procedure:
        return cls(
            id=str(raw["id"]),
            version=int(raw["version"]),
            title=str(raw["title"]),
            raw=raw,
            procedure_hash=canonical_hash(raw),
            source=source,
            approved=approved,
        )

    @property
    def steps(self) -> list[Step]:
        return [Step(id=str(step["id"]), type=str(step["type"]), raw=step) for step in self.raw["steps"]]

    @property
    def preconditions(self) -> list[dict[str, Any]]:
        value: list[dict[str, Any]] = list(self.raw.get("preconditions", []))
        return value

    @property
    def checks(self) -> list[dict[str, Any]]:
        value: list[dict[str, Any]] = list(self.raw.get("evaluate", []))
        return value

    @property
    def timeout_s(self) -> float:
        return float(self.raw.get("timeout_s", 600))

    @property
    def record(self) -> bool:
        return bool(self.raw.get("record", True))

    @property
    def requires_output(self) -> bool:
        return bool(self.raw.get("requires_output", False))

    @property
    def applies_to(self) -> dict[str, list[str]]:
        value = self.raw.get("applies_to", {})
        return {
            "concepts": list(value.get("concepts", [])),
            "actuators": list(value.get("actuators", [])),
            "hardware_modes": list(value.get("hardware_modes", [])),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "title": self.title,
            "summary": self.raw.get("summary", ""),
            "domain": self.raw.get("domain"),
            "tags": list(self.raw.get("tags", [])),
            "procedure_hash": self.procedure_hash,
            "source": self.source,
            "approved": self.approved,
            "applies_to": self.applies_to,
            "requires_output": self.requires_output,
            "steps": len(self.raw["steps"]),
            "operator_steps": sum(1 for step in self.raw["steps"] if step["type"] == "await_operator"),
        }


@dataclass
class StepResult:
    step_id: str
    type: str
    title: str
    status: str = "pending"  # pending | running | awaiting | passed | failed | skipped
    started_at: str | None = None
    ended_at: str | None = None
    elapsed_ms: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    instruction: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProcedureRun:
    run_id: str
    procedure_id: str
    procedure_hash: str
    procedure_title: str
    rig_id: str
    config_hash: str
    contract_hash: str
    label: str
    requested_by: str
    created_at: str
    status: RunStatus = RunStatus.PENDING
    started_at: str | None = None
    ended_at: str | None = None
    current_step: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    outcome_reason: str = ""
    kernel_events: list[dict[str, Any]] = field(default_factory=list)
    peaks: dict[str, float] = field(default_factory=dict)
    recording: dict[str, Any] | None = None
    evidence_dir: str | None = None
    hardware_mode: str = ""
    recovery: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["terminal"] = self.status.terminal
        return value
