"""The deterministic procedure runner.

State machine::

    pending -> preflight -> running(step n) <-> awaiting_operator -> passed | failed | aborted

Every transition appends an event to the run record. The runner only ever talks to
the kernel through :class:`LiveBenchRuntime` commands; it cannot bypass the guardrail.
Any run, however it ends, leaves the kernel in the safe state.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..live import LiveBenchRuntime
from ..models import RigConfig
from .facts import Facts, build_facts
from .model import Procedure, ProcedureRun, RunStatus, Step, StepResult
from .predicates import describe, evaluate, observed


class RunnerError(RuntimeError):
    pass


class _Abort(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Fail(Exception):
    def __init__(self, reason: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ProcedureRunner:
    def __init__(
        self,
        runtime: LiveBenchRuntime,
        config: RigConfig,
        evidence_dir: str | Path,
        contract_hash: Callable[[], str],
        poll_s: float | None = None,
        on_finish: Callable[[ProcedureRun], None] | None = None,
        bundle_context: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.runtime = runtime
        self.config = config
        self.evidence_dir = Path(evidence_dir)
        self._contract_hash = contract_hash
        self.poll_s = poll_s if poll_s is not None else max(0.01, config.sample_interval_ms / 2000.0)
        self.on_finish = on_finish
        self.bundle_context = bundle_context or (lambda: {})
        self._lock = threading.RLock()
        self._runs: dict[str, ProcedureRun] = {}
        self._procedures: dict[str, Procedure] = {}
        self._active: str | None = None
        self._thread: threading.Thread | None = None
        self._abort_reason: str | None = None
        self._ack_event = threading.Event()
        self._ack_step: str | None = None
        self._ack_by: str | None = None
        self._closing = threading.Event()
        self._last_event_key: tuple[str, str] | None = None

    # ------------------------------------------------------------------ queries
    def get(self, run_id: str) -> ProcedureRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            runs = sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)[:limit]
            return [
                {
                    "run_id": run.run_id,
                    "procedure_id": run.procedure_id,
                    "procedure_hash": run.procedure_hash,
                    "title": run.procedure_title,
                    "status": run.status.value,
                    "label": run.label,
                    "created_at": run.created_at,
                    "ended_at": run.ended_at,
                    "outcome_reason": run.outcome_reason,
                    "current_step": run.current_step,
                    "hardware_mode": run.hardware_mode,
                }
                for run in runs
            ]

    @property
    def active(self) -> ProcedureRun | None:
        with self._lock:
            return self._runs.get(self._active) if self._active else None

    # ------------------------------------------------------------------ control
    def start(self, procedure: Procedure, label: str, requested_by: str) -> ProcedureRun:
        with self._lock:
            if self._active is not None:
                raise RunnerError(f"a procedure run is already active: {self._active}")
            if not procedure.approved:
                raise RunnerError("procedure is not approved")
            if procedure.requires_output and not self.runtime.allow_output:
                raise RunnerError("procedure requires output actuation but this node is monitor-only")
            modes = procedure.applies_to["hardware_modes"]
            if modes and self.config.hardware.mode not in modes:
                raise RunnerError(f"procedure does not apply to hardware mode {self.config.hardware.mode}")
            run = ProcedureRun(
                run_id=f"run_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}",
                procedure_id=procedure.id,
                procedure_hash=procedure.procedure_hash,
                procedure_title=procedure.title,
                rig_id=self.config.rig_id,
                config_hash=self.config.config_hash,
                contract_hash=self._contract_hash(),
                label=label,
                requested_by=requested_by,
                created_at=utc_now(),
                hardware_mode=self.config.hardware.mode,
                recovery=procedure.raw.get("recovery"),
                steps=[StepResult(step.id, step.type, step.title) for step in procedure.steps],
            )
            self._runs[run.run_id] = run
            self._procedures[run.run_id] = procedure
            self._active = run.run_id
            self._abort_reason = None
            self._ack_event.clear()
            self._ack_step = None
            self._thread = threading.Thread(
                target=self._execute, args=(run, procedure), name=f"certarig-proc-{run.run_id}", daemon=True
            )
            self._thread.start()
            return run

    def ack(self, run_id: str, step_id: str, by: str) -> ProcedureRun:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            if run.status is not RunStatus.AWAITING_OPERATOR or run.current_step != step_id:
                raise RunnerError(f"run is not awaiting acknowledgement of step {step_id}")
            self._ack_step = step_id
            self._ack_by = by
            self._ack_event.set()
            return run

    def abort(self, run_id: str, reason: str, by: str) -> ProcedureRun:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            if run.status.terminal:
                raise RunnerError(f"run already ended with status {run.status.value}")
            self._abort_reason = f"{reason} (by {by})"
            self._ack_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=5.0)
        return run

    def close(self) -> None:
        self._closing.set()
        with self._lock:
            active = self._active
            thread = self._thread
        if active is not None:
            self._abort_reason = "runner closing"
            self._ack_event.set()
        if thread is not None:
            thread.join(timeout=5.0)

    # ------------------------------------------------------------------ helpers
    def _event(self, run: ProcedureRun, kind: str, **payload: Any) -> None:
        run.events.append({"at": utc_now(), "kind": kind, **payload})

    def _observe(self, run: ProcedureRun) -> Facts:
        state = self.runtime.state()
        facts = build_facts(self.config, state)
        key = (str(state.get("last_event", "")), str(state.get("last_event_at", "")))
        if key != self._last_event_key and key[0]:
            self._last_event_key = key
            run.kernel_events.append({"at": key[1], "event": key[0], "reason": facts.states.get("reason")})
        for name, value in facts.signals.items():
            if value is not None and value > run.peaks.get(name, float("-inf")):
                run.peaks[name] = value
        return facts

    def _guard(self, run: ProcedureRun, step: Step | None, facts: Facts, deadline: float) -> None:
        if self._abort_reason is not None:
            raise _Abort(self._abort_reason)
        if self._closing.is_set():
            raise _Abort("runner closing")
        if time.monotonic() > deadline:
            raise _Fail("procedure timeout exceeded")
        if facts.states.get("status") == "error":
            raise _Abort(f"runtime error: {facts.states.get('last_event')}")
        if step is not None and facts.states.get("estop_active") and not step.allow_estop:
            raise _Abort("emergency stop became active during a step that does not allow it")
        if step is not None and not step.allow_invalid_sensor:
            invalid = sorted(name for name, state in facts.signal_states.items() if state == "invalid")
            if invalid:
                raise _Fail(
                    f"sensor invalid during step: {', '.join(invalid)}",
                    {"invalid_signals": invalid, "qualities": dict(facts.qualities)},
                )

    def _wait_for(
        self,
        run: ProcedureRun,
        step: Step,
        predicate: dict[str, Any],
        timeout_s: float,
        deadline: float,
    ) -> tuple[Facts, float]:
        started = time.monotonic()
        while True:
            facts = self._observe(run)
            self._guard(run, step, facts, deadline)
            if evaluate(predicate, facts):
                return facts, (time.monotonic() - started) * 1000.0
            if time.monotonic() - started > timeout_s:
                raise _Fail(
                    f"{describe(predicate)} not satisfied within {timeout_s:.3f}s",
                    {"predicate": describe(predicate), "observed": observed(predicate, facts)},
                )
            time.sleep(self.poll_s)

    def _hold(
        self, run: ProcedureRun, step: Step, predicate: dict[str, Any], hold_ms: int, deadline: float
    ) -> None:
        end = time.monotonic() + hold_ms / 1000.0
        while time.monotonic() < end:
            facts = self._observe(run)
            self._guard(run, step, facts, deadline)
            if not evaluate(predicate, facts):
                raise _Fail(
                    f"{describe(predicate)} did not hold for {hold_ms} ms",
                    {"predicate": describe(predicate), "observed": observed(predicate, facts)},
                )
            time.sleep(self.poll_s)

    # ------------------------------------------------------------------ steps
    def _run_step(self, run: ProcedureRun, step: Step, result: StepResult, deadline: float) -> None:
        raw = step.raw
        if step.type == "command":
            state = self.runtime.command(str(raw["command"]))
            result.detail["kernel_event"] = state["guardrail"].get("event")
            result.detail["kernel_reason"] = state["guardrail"].get("reason")
            self._event(
                run,
                "command",
                step=step.id,
                command=raw["command"],
                kernel_event=state["guardrail"].get("event"),
            )
            if "expect" in raw:
                facts, elapsed = self._wait_for(
                    run, step, raw["expect"], int(raw.get("within_ms", 1000)) / 1000.0, deadline
                )
                result.detail["expect"] = describe(raw["expect"])
                result.detail["observed"] = observed(raw["expect"], facts)
                result.detail["satisfied_after_ms"] = round(elapsed, 3)
            return
        if step.type == "expect":
            facts, elapsed = self._wait_for(
                run, step, raw["predicate"], int(raw.get("within_ms", 1000)) / 1000.0, deadline
            )
            result.detail["predicate"] = describe(raw["predicate"])
            result.detail["observed"] = observed(raw["predicate"], facts)
            result.detail["satisfied_after_ms"] = round(elapsed, 3)
            hold_ms = int(raw.get("hold_ms", 0))
            if hold_ms:
                self._hold(run, step, raw["predicate"], hold_ms, deadline)
                result.detail["held_ms"] = hold_ms
            return
        if step.type == "trigger":
            if raw.get("instruction"):
                result.instruction = str(raw["instruction"])
                self._event(run, "instruction", step=step.id, instruction=result.instruction)
            facts, elapsed = self._wait_for(
                run, step, raw["predicate"], float(raw.get("timeout_s", 300)), deadline
            )
            result.detail["predicate"] = describe(raw["predicate"])
            result.detail["observed"] = observed(raw["predicate"], facts)
            result.detail["triggered_after_ms"] = round(elapsed, 3)
            return
        if step.type == "await_operator":
            result.instruction = str(raw["instruction"])
            result.status = "awaiting"
            with self._lock:
                run.status = RunStatus.AWAITING_OPERATOR
                self._ack_event.clear()
                self._ack_step = None
            self._event(run, "awaiting_operator", step=step.id, instruction=result.instruction)
            timeout = float(raw.get("timeout_s", 600))
            started = time.monotonic()
            while True:
                if self._ack_event.wait(timeout=self.poll_s):
                    facts = self._observe(run)
                    self._guard(run, step, facts, deadline)
                    acknowledged: str | None = self._ack_step
                    if acknowledged == step.id:
                        break
                    self._ack_event.clear()
                facts = self._observe(run)
                self._guard(run, step, facts, deadline)
                if time.monotonic() - started > timeout:
                    raise _Fail(f"operator did not acknowledge within {timeout:.0f}s")
            with self._lock:
                run.status = RunStatus.RUNNING
            result.detail["acknowledged_by"] = self._ack_by
            self._event(run, "operator_ack", step=step.id, by=self._ack_by)
            if "confirm" in raw:
                facts = self._observe(run)
                result.detail["confirm"] = describe(raw["confirm"])
                result.detail["observed"] = observed(raw["confirm"], facts)
                if not evaluate(raw["confirm"], facts):
                    raise _Fail(f"confirmation predicate failed: {describe(raw['confirm'])}", result.detail)
            return
        if step.type == "wait":
            end = time.monotonic() + int(raw["duration_ms"]) / 1000.0
            while time.monotonic() < end:
                facts = self._observe(run)
                self._guard(run, step, facts, deadline)
                time.sleep(min(self.poll_s, max(0.0, end - time.monotonic())))
            return
        if step.type == "record":
            action = raw["action"]
            if action == "start":
                state = self.runtime.start_recording(str(raw.get("label", run.label)))
                result.detail["filename"] = state["recording"]["filename"]
            elif action == "stop":
                state = self.runtime.stop_recording()
                result.detail["completed_recording"] = state.get("completed_recording")
                run.recording = state.get("completed_recording")
            else:
                self._event(run, "mark", step=step.id, label=raw.get("label", step.id))
            return
        raise _Fail(f"unsupported step type {step.type}")

    # ------------------------------------------------------------------ checks
    def _evaluate_checks(self, run: ProcedureRun, procedure: Procedure) -> bool:
        observed_events = {row["event"] for row in run.kernel_events}
        by_step = {result.step_id: result for result in run.steps}
        all_ok = True
        for check in procedure.checks:
            ok = True
            detail: dict[str, Any] = {}
            if "event_observed" in check:
                ok = check["event_observed"] in observed_events
                detail = {"observed_events": sorted(observed_events)}
            elif "event_not_observed" in check:
                ok = check["event_not_observed"] not in observed_events
                detail = {"observed_events": sorted(observed_events)}
            elif "step_passed" in check:
                ok = by_step[check["step_passed"]].status == "passed"
            elif "max_elapsed_ms" in check:
                result = by_step[check["step"]]
                measured = result.detail.get("satisfied_after_ms", result.detail.get("triggered_after_ms"))
                ok = measured is not None and float(measured) <= float(check["max_elapsed_ms"])
                detail = {"measured_ms": measured}
            elif "peak_below" in check:
                peak = run.peaks.get(str(check["signal"]))
                ok = peak is not None and peak < float(check["peak_below"])
                detail = {"peak": peak}
            run.checks.append({"check": check, "passed": ok, **detail})
            all_ok = all_ok and ok
        return all_ok

    # ------------------------------------------------------------------ execute
    def _execute(self, run: ProcedureRun, procedure: Procedure) -> None:
        deadline = time.monotonic() + procedure.timeout_s
        final_status = RunStatus.FAILED
        reason = ""
        try:
            with self._lock:
                run.status = RunStatus.PREFLIGHT
                run.started_at = utc_now()
            self._event(run, "preflight")
            facts = self._observe(run)
            self._guard(run, None, facts, deadline)
            failed = [describe(p) for p in procedure.preconditions if not evaluate(p, facts)]
            if failed:
                raise _Fail(
                    "preconditions not met: " + "; ".join(failed),
                    {"failed_preconditions": failed, "signals": facts.signals, "states": facts.states},
                )
            if procedure.record:
                state = self.runtime.start_recording(run.label)
                self._event(run, "recording_started", filename=state["recording"]["filename"])
            with self._lock:
                run.status = RunStatus.RUNNING
            for step, result in zip(procedure.steps, run.steps, strict=True):
                with self._lock:
                    run.current_step = step.id
                result.status = "running"
                result.started_at = utc_now()
                started = time.monotonic()
                self._event(run, "step_started", step=step.id, type=step.type)
                try:
                    self._run_step(run, step, result, deadline)
                except _Fail as exc:
                    result.status = "failed"
                    result.detail.update(exc.detail)
                    result.detail["reason"] = exc.reason
                    result.ended_at = utc_now()
                    result.elapsed_ms = round((time.monotonic() - started) * 1000, 3)
                    self._event(run, "step_failed", step=step.id, reason=exc.reason)
                    raise _Fail(f"step {step.id} failed: {exc.reason}") from exc
                result.status = "passed"
                result.ended_at = utc_now()
                result.elapsed_ms = round((time.monotonic() - started) * 1000, 3)
                self._event(run, "step_passed", step=step.id, elapsed_ms=result.elapsed_ms)
            checks_ok = self._evaluate_checks(run, procedure)
            if checks_ok:
                final_status = RunStatus.PASSED
                reason = "all steps and checks passed"
            else:
                final_status = RunStatus.FAILED
                failed_checks = [row["check"] for row in run.checks if not row["passed"]]
                reason = f"{len(failed_checks)} evaluation check(s) failed"
        except _Fail as exc:
            final_status = RunStatus.FAILED
            reason = exc.reason
            self._evaluate_checks(run, procedure)
        except _Abort as exc:
            final_status = RunStatus.ABORTED
            reason = exc.reason
        except Exception as exc:  # pragma: no cover - defensive
            final_status = RunStatus.ABORTED
            reason = f"runner exception: {type(exc).__name__}: {exc}"
        finally:
            self._finish(run, final_status, reason)

    def _finish(self, run: ProcedureRun, status: RunStatus, reason: str) -> None:
        for result in run.steps:
            if result.status in {"running", "awaiting"}:
                result.status = "failed" if status is RunStatus.FAILED else "skipped"
                result.ended_at = utc_now()
            elif result.status == "pending":
                result.status = "skipped"
        try:
            state = self.runtime.command("safe")
            self._event(run, "kernel_forced_safe", kernel_event=state["guardrail"].get("event"))
        except Exception as exc:  # pragma: no cover - defensive
            self._event(run, "kernel_safe_failed", error=str(exc))
        try:
            if self.runtime.state()["recording"]["active"]:
                state = self.runtime.stop_recording()
                run.recording = state.get("completed_recording")
                self._event(run, "recording_stopped", **(run.recording or {}))
        except Exception as exc:  # pragma: no cover - defensive
            self._event(run, "recording_stop_failed", error=str(exc))
        # Persist before publishing the terminal status so an observer that sees ``terminal``
        # always finds run.json and procedure.json on disk.
        run.outcome_reason = reason
        run.ended_at = utc_now()
        run.current_step = None
        self._event(run, "finished", status=status.value, reason=reason)
        self._persist(run, status)
        with self._lock:
            run.status = status
            self._active = None
        if self.on_finish is not None:
            try:
                self.on_finish(run)
            except Exception:  # pragma: no cover - hooks must not break the runner
                pass

    def _persist(self, run: ProcedureRun, status: RunStatus | None = None) -> None:
        target = self.evidence_dir / "procedure_runs" / run.run_id
        target.mkdir(parents=True, exist_ok=True)
        run.evidence_dir = str(target)
        procedure = self._procedures.get(run.run_id)
        if procedure is not None and not (target / "procedure.json").is_file():
            (target / "procedure.json").write_text(
                json.dumps(procedure.raw, indent=2, sort_keys=True), encoding="utf-8"
            )
        document = run.to_dict()
        if status is not None:
            document["status"] = status.value
            document["terminal"] = status.terminal
        (target / "run.json").write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        if status is not None and status.terminal:
            from certarig.edge.bundle import write_run_bundle

            seed = getattr(getattr(self.runtime.hardware, "settings", None), "seed", None)
            write_run_bundle(
                target,
                document,
                {
                    "title": procedure.title if procedure is not None else run.procedure_id,
                    "seed": seed,
                    "contract_hash": self._contract_hash(),
                    "rig_id": self.config.rig_id,
                    "hardware_mode": self.config.hardware.mode,
                    "config_hash": self.config.config_hash,
                    **self.bundle_context(),
                },
            )
