"""In-process tests of the procedure runner state machine against a hand-driven rig."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from certarig.edge.live import LiveBenchRuntime
from certarig.edge.runtime import ProcedureLibrary, ProcedureRunner, ProcedureValidationError, RunStatus
from certarig.edge.runtime.library import load_procedure_file, validate_procedure
from certarig.edge.runtime.model import Procedure
from certarig.edge.runtime.runner import RunnerError
from tests.support import SKILLS_DIR, ControllableRig, fast_config, wait_until


class Harness:
    def __init__(self, temp: str, allow_output: bool = True) -> None:
        self.config = fast_config()
        self.rig = ControllableRig(self.config)
        self.runtime = LiveBenchRuntime(
            self.config, self.rig, Path(temp) / "evidence", allow_output=allow_output
        )
        self.runtime.start()
        self.library = ProcedureLibrary(self.config, drafts_dir=Path(temp) / "drafts")
        self.library.load_directory(SKILLS_DIR)
        self.runner = ProcedureRunner(self.runtime, self.config, Path(temp) / "evidence", lambda: "contract")

    def procedure(self, procedure_id: str) -> Procedure:
        procedure = self.library.get(procedure_id)
        assert procedure is not None, procedure_id
        return procedure

    def run(self, procedure_id: str, label: str = "test") -> str:
        return self.runner.start(self.procedure(procedure_id), label, "tester").run_id

    def at_step(self, run_id: str, step_id: str, timeout: float = 10.0) -> None:
        assert wait_until(lambda: self.runner.get(run_id).current_step == step_id, timeout), (  # type: ignore[union-attr]
            f"never reached {step_id}: {self.runner.get(run_id).to_dict()}"  # type: ignore[union-attr]
        )

    def finished(self, run_id: str, timeout: float = 30.0) -> RunStatus:
        assert wait_until(lambda: self.runner.get(run_id).status.terminal, timeout)  # type: ignore[union-attr]
        run = self.runner.get(run_id)
        assert run is not None
        return run.status

    def close(self) -> None:
        self.runner.close()
        self.runtime.close()


@pytest.fixture
def harness() -> Iterator[Harness]:
    with tempfile.TemporaryDirectory() as temp:
        h = Harness(temp)
        try:
            yield h
        finally:
            h.close()


def test_library_loads_the_shipped_procedures() -> None:
    config = fast_config()
    library = ProcedureLibrary(config)
    loaded = library.load_directory(SKILLS_DIR)
    ids = sorted(p.id for p in loaded)
    assert {
        "pressure_guardrail",
        "estop_anti_restart",
        "relay_truth_table",
        "adc_validation",
        "safe_powerdown",
        "anomaly_report",
    } <= set(ids)
    assert [row["path"] for row in library.skipped] == []
    summary = library.get("pressure_guardrail").summary()  # type: ignore[union-attr]
    assert summary["operator_steps"] == 0 and summary["requires_output"] is True
    assert len(summary["procedure_hash"]) == 64


def test_relay_truth_table_passes_automatically(harness: Harness) -> None:
    run_id = harness.run("relay_truth_table")
    assert harness.finished(run_id) is RunStatus.PASSED
    run = harness.runner.get(run_id)
    assert run is not None
    assert all(step.status == "passed" for step in run.steps)
    assert all(check["passed"] for check in run.checks)
    assert harness.rig.output is False
    assert run.recording is not None and run.recording["samples"] > 0
    assert harness.runtime.state()["recording"]["active"] is False
    persisted = json.loads((Path(run.evidence_dir) / "run.json").read_text())  # type: ignore[arg-type]
    assert persisted["status"] == "passed"
    assert (Path(run.evidence_dir) / "procedure.json").is_file()  # type: ignore[arg-type]
    listing = harness.runner.list()
    assert listing[0]["run_id"] == run_id and listing[0]["status"] == "passed"


def test_pressure_guardrail_with_operator_moves(harness: Harness) -> None:
    run_id = harness.run("pressure_guardrail", "guardrail")
    harness.at_step(run_id, "raise_pressure")
    assert harness.rig.output is True  # permitted and energised before the trip
    harness.rig.set("pressure_emulator", 5.0)
    harness.at_step(run_id, "lower_pressure")
    assert harness.rig.output is False
    harness.rig.set("pressure_emulator", 2.0)
    assert harness.finished(run_id) is RunStatus.PASSED
    run = harness.runner.get(run_id)
    assert run is not None
    events = [row["event"] for row in run.kernel_events]
    assert "pressure_high_forced_safe" in events and "permit_rejected_reset_required" in events
    by_step = {step.step_id: step for step in run.steps}
    assert by_step["output_removed"].detail["satisfied_after_ms"] <= 500
    assert run.peaks["pressure"] == 5.0
    assert all(check["passed"] for check in run.checks), run.checks


def test_estop_anti_restart(harness: Harness) -> None:
    run_id = harness.run("estop_anti_restart")
    harness.at_step(run_id, "press_estop")
    harness.rig.estop = True
    harness.at_step(run_id, "release_estop")
    assert harness.rig.output is False
    harness.rig.estop = False
    assert harness.finished(run_id) is RunStatus.PASSED
    run = harness.runner.get(run_id)
    assert run is not None
    assert {"estop_open_forced_safe", "estop_closed_reset_required"} <= {
        row["event"] for row in run.kernel_events
    }


def test_preconditions_fail_fast_and_leave_kernel_safe(harness: Harness) -> None:
    harness.rig.set("pressure_emulator", 4.1)  # above the 4.0 precondition, below trip
    assert wait_until(lambda: harness.runtime.state()["samples"][0]["value"] == 4.1)
    run_id = harness.run("pressure_guardrail")
    assert harness.finished(run_id) is RunStatus.FAILED
    run = harness.runner.get(run_id)
    assert run is not None
    assert run.outcome_reason.startswith("preconditions not met")
    assert all(step.status == "skipped" for step in run.steps)
    assert harness.rig.output is False
    assert run.events[-1]["kind"] == "finished"


def test_abort_during_trigger(harness: Harness) -> None:
    run_id = harness.run("pressure_guardrail")
    harness.at_step(run_id, "raise_pressure")
    assert harness.rig.output is True
    harness.runner.abort(run_id, "operator changed their mind", "tester")
    assert harness.finished(run_id, 5) is RunStatus.ABORTED
    run = harness.runner.get(run_id)
    assert run is not None
    assert "operator changed their mind" in run.outcome_reason
    assert harness.rig.output is False
    assert run.recording is not None  # stopped and checksummed on abort
    assert harness.runner.active is None
    with pytest.raises(RunnerError, match="already ended"):
        harness.runner.abort(run_id, "again", "tester")


def test_unexpected_estop_aborts_a_step_that_does_not_allow_it(harness: Harness) -> None:
    run_id = harness.run("relay_truth_table")
    harness.at_step(run_id, "cycle1_hold")
    harness.rig.estop = True
    assert harness.finished(run_id, 5) is RunStatus.ABORTED
    run = harness.runner.get(run_id)
    assert run is not None
    assert "emergency stop" in run.outcome_reason
    assert harness.rig.output is False


def test_await_operator_ack_flow(harness: Harness) -> None:
    run_id = harness.run("safe_powerdown")
    assert wait_until(lambda: harness.runner.get(run_id).status is RunStatus.AWAITING_OPERATOR)  # type: ignore[union-attr]
    run = harness.runner.get(run_id)
    assert run is not None and run.current_step == "confirm_bench"
    awaiting = next(step for step in run.steps if step.step_id == "confirm_bench")
    assert awaiting.status == "awaiting" and "Confirm the green indicator" in (awaiting.instruction or "")
    with pytest.raises(RunnerError):
        harness.runner.ack(run_id, "final_safe", "tester")
    with pytest.raises(KeyError):
        harness.runner.ack("run_missing", "confirm_bench", "tester")
    harness.runner.ack(run_id, "confirm_bench", "chintan")
    assert harness.finished(run_id) is RunStatus.PASSED
    run = harness.runner.get(run_id)
    assert run is not None
    assert awaiting.detail["acknowledged_by"] == "chintan"
    assert run.recording is None  # record: false


def test_only_one_run_at_a_time_and_output_requirement(harness: Harness) -> None:
    run_id = harness.run("safe_powerdown")
    with pytest.raises(RunnerError, match="already active"):
        harness.run("relay_truth_table")
    harness.runner.abort(run_id, "cleanup", "tester")
    harness.finished(run_id)
    with tempfile.TemporaryDirectory() as temp:
        monitor = Harness(temp, allow_output=False)
        try:
            with pytest.raises(RunnerError, match="monitor-only"):
                monitor.run("relay_truth_table")
            unapproved = Procedure.from_dict(monitor.procedure("safe_powerdown").raw, approved=False)
            with pytest.raises(RunnerError, match="not approved"):
                monitor.runner.start(unapproved, "x", "tester")
        finally:
            monitor.close()


def test_timeouts_fail_steps(harness: Harness) -> None:
    raw = json.loads(json.dumps(harness.procedure("pressure_guardrail").raw))
    raw["id"] = "quick_timeout"
    raw["steps"][4]["timeout_s"] = 0.2  # raise_pressure trigger
    procedure = Procedure.from_dict(raw)
    assert validate_procedure(raw, harness.config) == []
    run_id = harness.runner.start(procedure, "t", "tester").run_id
    assert harness.finished(run_id) is RunStatus.FAILED
    run = harness.runner.get(run_id)
    assert run is not None
    assert "raise_pressure failed" in run.outcome_reason
    failed = next(step for step in run.steps if step.step_id == "raise_pressure")
    assert "observed" in failed.detail and failed.detail["observed"]["pressure"] is not None
    assert harness.rig.output is False


def test_hold_failure_and_expect_timeout(harness: Harness) -> None:
    raw = {
        "id": "hold_check",
        "version": 1,
        "title": "hold must persist",
        "record": False,
        "steps": [
            {"id": "reset", "type": "command", "command": "reset"},
            {
                "id": "permit",
                "type": "command",
                "command": "permit",
                "expect": {"state": "output_high", "eq": True},
            },
            {
                "id": "hold",
                "type": "expect",
                "predicate": {"state": "output_high", "eq": True},
                "hold_ms": 800,
            },
        ],
    }
    procedure = Procedure.from_dict(raw)
    run_id = harness.runner.start(procedure, "h", "tester").run_id
    harness.at_step(run_id, "hold")
    harness.rig.set("pressure_emulator", 6.0)  # trip during hold
    assert harness.finished(run_id) is RunStatus.FAILED
    run = harness.runner.get(run_id)
    assert run is not None and "did not hold" in run.outcome_reason
    harness.rig.set("pressure_emulator", 2.0)


def test_evaluate_checks_can_fail_a_passed_sequence(harness: Harness) -> None:
    raw = {
        "id": "check_fail",
        "version": 1,
        "title": "checks fail",
        "record": False,
        "steps": [{"id": "safe", "type": "command", "command": "safe"}],
        "evaluate": [{"event_observed": "permit_accepted"}, {"signal": "pressure", "peak_below": 0.1}],
    }
    run_id = harness.runner.start(Procedure.from_dict(raw), "c", "tester").run_id
    assert harness.finished(run_id) is RunStatus.FAILED
    run = harness.runner.get(run_id)
    assert run is not None
    assert run.outcome_reason == "2 evaluation check(s) failed"
    assert [row["passed"] for row in run.checks] == [False, False]


def test_record_steps_and_mark(harness: Harness) -> None:
    raw = {
        "id": "record_steps",
        "version": 1,
        "title": "explicit recording",
        "record": False,
        "steps": [
            {"id": "start", "type": "record", "action": "start", "label": "explicit"},
            {"id": "mark", "type": "record", "action": "mark", "label": "midpoint"},
            {"id": "pause", "type": "wait", "duration_ms": 100},
            {"id": "stop", "type": "record", "action": "stop"},
        ],
    }
    run_id = harness.runner.start(Procedure.from_dict(raw), "r", "tester").run_id
    assert harness.finished(run_id) is RunStatus.PASSED
    run = harness.runner.get(run_id)
    assert run is not None
    assert run.recording is not None and run.recording["filename"].endswith("_explicit.csv")
    assert any(event["kind"] == "mark" for event in run.events)


# ---------------------------------------------------------------- validation & drafts
def test_validation_catches_semantic_errors() -> None:
    config = fast_config()
    base = load_procedure_file(SKILLS_DIR / "electronics/relay_truth_table/procedure.yaml", config).raw
    raw = json.loads(json.dumps(base))
    raw["steps"][0]["id"] = raw["steps"][1]["id"]
    assert any("duplicate step ids" in e for e in validate_procedure(raw, config))
    raw = json.loads(json.dumps(base))
    raw["steps"][0]["predicate"] = {"signal": "chamber_pressure", "op": "<", "value": 1}
    assert any("unknown signals" in e for e in validate_procedure(raw, config))
    raw = json.loads(json.dumps(base))
    raw["evaluate"] = [{"step_passed": "ghost"}]
    assert any("unknown step" in e for e in validate_procedure(raw, config))
    raw = json.loads(json.dumps(base))
    raw["applies_to"] = {"concepts": ["chamber_pressure"], "hardware_modes": ["mock"]}
    errors = validate_procedure(raw, config)
    assert any("required concepts" in e for e in errors) and any("hardware mode" in e for e in errors)
    raw = json.loads(json.dumps(base))
    raw["steps"].append({"id": "rec", "type": "record", "action": "stop"})
    errors = validate_procedure(raw, config)
    assert any("no recording to stop" in e for e in errors) and any("cannot be combined" in e for e in errors)
    assert validate_procedure("nope", config) == ["procedure must be a mapping"]
    assert validate_procedure({"id": "x"}, config)  # schema errors
    with pytest.raises(ProcedureValidationError):
        ProcedureLibrary(config).add_draft({"id": "bad"}, "agent")


def test_drafts_are_inert_until_approved() -> None:
    with tempfile.TemporaryDirectory() as temp:
        config = fast_config()
        library = ProcedureLibrary(config, drafts_dir=Path(temp))
        raw = {
            "id": "draft_one",
            "version": 1,
            "title": "A drafted procedure",
            "record": False,
            "steps": [{"id": "safe", "type": "command", "command": "safe"}],
        }
        draft = library.add_draft(raw, "agent")
        assert draft.approved is False and library.get("draft_one") is None
        assert library.drafts()[0]["procedure_hash"] == draft.procedure_hash
        assert library.draft(draft.procedure_hash) is not None
        assert list(Path(temp).glob("draft_one-*.yaml"))
        approved = library.approve_draft(draft.procedure_hash, "engineer")
        assert approved.approved is True and library.get("draft_one") is not None
        assert library.drafts() == []
        with pytest.raises(KeyError):
            library.approve_draft(draft.procedure_hash, "engineer")
        second = library.add_draft(raw, "agent")
        library.reject_draft(second.procedure_hash)
        with pytest.raises(KeyError):
            library.reject_draft(second.procedure_hash)
        # newer version replaces, older does not
        newer = dict(raw, version=2)
        library.add(Procedure.from_dict(newer))
        assert library.get("draft_one").version == 2  # type: ignore[union-attr]
        library.add(Procedure.from_dict(raw))
        assert library.get("draft_one").version == 2  # type: ignore[union-attr]
