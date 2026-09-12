from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime

from .evidence import EvidenceStore
from .hardware.base import HardwareAdapter
from .models import (
    CommissioningPlan,
    EvidenceEvent,
    PlanState,
    RigSnapshot,
    RunOutcome,
    RunResult,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class DeterministicExecutor:
    def __init__(
        self,
        hardware: HardwareAdapter,
        store: EvidenceStore,
        sample_interval_ms: int,
        pressure_abort_bar: float,
        actuation_enabled: bool,
    ) -> None:
        self.hardware = hardware
        self.store = store
        self.sample_interval_ms = sample_interval_ms
        self.pressure_abort_bar = pressure_abort_bar
        self.actuation_enabled = actuation_enabled
        self._stop_requested = threading.Event()
        self._run_lock = threading.Lock()

    def request_stop(self) -> None:
        self._stop_requested.set()
        self.hardware.force_safe_state()

    @staticmethod
    def _pressure(snapshot: RigSnapshot) -> float:
        values = [sample.value for sample in snapshot.samples if sample.unit.lower() == "bar"]
        if not values:
            raise RuntimeError("snapshot contains no pressure channel")
        return float(max(values))

    def run(self, plan: CommissioningPlan) -> RunResult:
        if plan.state != PlanState.APPROVED:
            raise ValueError("plan must be approved before execution")
        if not self._run_lock.acquire(blocking=False):
            raise RuntimeError("another run is already active")

        run_id = f"run-{uuid.uuid4().hex[:12]}"
        started = utc_now()
        sequence = 0
        max_pressure = 0.0
        outcome = RunOutcome.COMPLETED
        reason = "all approved steps completed"
        plan.state = PlanState.RUNNING
        self._stop_requested.clear()

        def record(event_type: str, payload: dict) -> None:
            nonlocal sequence
            self.store.append_event(
                EvidenceEvent(
                    run_id=run_id,
                    sequence=sequence,
                    event_type=event_type,
                    payload=payload,
                    recorded_at=utc_now(),
                )
            )
            sequence += 1

        try:
            record("run_started", {"plan_id": plan.plan_id, "config_hash": plan.config_hash})
            for index, step in enumerate(plan.steps):
                if self._stop_requested.is_set():
                    outcome = RunOutcome.STOPPED
                    reason = "operator stop requested"
                    break
                record("step_started", {"index": index, "action": step.action})
                if step.action == "set_valve":
                    if step.valve_open and not self.actuation_enabled:
                        outcome = RunOutcome.BLOCKED
                        reason = "physical actuation is disabled"
                        record("run_blocked", {"reason": reason})
                        break
                    self.hardware.set_valve(bool(step.valve_open))
                    record("output_changed", {"valve_open": bool(step.valve_open)})

                sample_count = max(1, step.duration_ms // self.sample_interval_ms)
                if step.action in {"hold", "sample", "set_valve"}:
                    for _ in range(sample_count):
                        snapshot = self.hardware.snapshot()
                        pressure = self._pressure(snapshot)
                        max_pressure = max(max_pressure, pressure)
                        record("snapshot", snapshot.to_dict())
                        if snapshot.emergency_stop_active:
                            outcome = RunOutcome.SAFE_ABORT
                            reason = "emergency stop became active"
                            break
                        if any(sample.quality != "good" for sample in snapshot.samples):
                            outcome = RunOutcome.SAFE_ABORT
                            reason = "sensor quality became invalid"
                            break
                        if pressure > min(plan.pressure_limit_bar, self.pressure_abort_bar):
                            outcome = RunOutcome.SAFE_ABORT
                            reason = "pressure exceeded the approved limit"
                            break
                        if self._stop_requested.wait(self.sample_interval_ms / 1000.0):
                            outcome = RunOutcome.STOPPED
                            reason = "operator stop requested"
                            break
                if outcome != RunOutcome.COMPLETED:
                    record("run_interrupted", {"outcome": outcome.value, "reason": reason})
                    break
                record("step_completed", {"index": index})
        except Exception as exc:
            outcome = RunOutcome.SAFE_ABORT
            reason = f"executor error: {type(exc).__name__}"
            record("executor_error", {"error_type": type(exc).__name__, "message": str(exc)})
        finally:
            self.hardware.force_safe_state()
            record("safe_state", {"output_safe": self.hardware.output_is_safe()})
            self._run_lock.release()

        completed = utc_now()
        if outcome == RunOutcome.COMPLETED:
            plan.state = PlanState.COMPLETED
        elif outcome == RunOutcome.STOPPED:
            plan.state = PlanState.STOPPED
        else:
            plan.state = PlanState.ABORTED
        checksum = self.store.checksum(run_id)
        result = RunResult(
            run_id=run_id,
            plan_id=plan.plan_id,
            outcome=outcome,
            reason=reason,
            started_at=started,
            completed_at=completed,
            max_pressure_bar=round(max_pressure, 5),
            evidence_checksum=checksum,
        )
        self.store.save_plan(plan)
        self.store.save_run(result)
        return result
