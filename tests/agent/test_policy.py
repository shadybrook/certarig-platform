"""Pure unit tests for the rule-based demo policy (no server)."""

from __future__ import annotations

import json
from typing import Any

from certarig.agent.policy import RuleBasedPolicy
from certarig.agent.providers.base import Message, ToolCall
from certarig.agent.skills import SkillIndex
from tests.support import SKILLS_DIR

POLICY = RuleBasedPolicy(SkillIndex.load(SKILLS_DIR), max_waits=2)


def _turn(user: str, *results: tuple[str, dict[str, Any]]) -> list[Message]:
    messages = [Message(role="user", content=user)]
    for index, (name, payload) in enumerate(results):
        call = ToolCall(f"c{index}", name, {})
        messages.append(Message(role="assistant", content="", tool_calls=(call,)))
        messages.append(Message(role="tool", content=json.dumps(payload), tool_call_id=call.id, name=name))
    return messages


def _first_call(messages: list[Message]) -> tuple[str, dict[str, Any]] | None:
    response = POLICY("system", messages, [])
    if response.tool_calls:
        return response.tool_calls[0].name, response.tool_calls[0].arguments
    return None


def _text(messages: list[Message]) -> str:
    response = POLICY("system", messages, [])
    assert not response.tool_calls
    return response.text or ""


def test_opening_moves() -> None:
    assert _first_call(_turn("abort now")) == ("force_safe", {})
    assert _first_call(_turn("done")) == ("list_skills", {})
    assert _first_call(_turn("what can you do")) == ("list_skills", {})
    assert _first_call(_turn("verify the pressure trip")) == ("read_skill", {"name": "pressure_guardrail"})
    assert _first_call(_turn("how is the flow")) == ("read_state", {})
    assert _first_call(_turn("gibberish")) == ("list_skills", {})


def test_active_run_is_tracked_across_turns() -> None:
    history = _turn("cycle the relay", ("run_procedure", {"run_id": "r1", "status": "running"}))
    history.append(Message(role="assistant", content="working"))
    history.append(Message(role="user", content="abort"))
    assert _first_call(history) == ("abort_procedure", {"run_id": "r1", "reason": "operator asked to abort"})
    history[-1] = Message(role="user", content="done")
    assert _first_call(history) == ("wait_for_run", {"run_id": "r1", "timeout_s": 60})
    finished = _turn(
        "cycle the relay", ("wait_for_run", {"run_id": "r1", "terminal": True, "status": "passed"})
    )
    finished.append(Message(role="assistant", content="ok"))
    finished.append(Message(role="user", content="abort"))
    assert _first_call(finished) == ("force_safe", {})


def test_approval_dance() -> None:
    from certarig.agent.providers.base import ToolSpec

    tools = [ToolSpec("request_approval", "", {})]
    refused = _turn(
        "reset", ("reset_trip", {"code": "approval_required", "tool": "reset_trip", "error": "x"})
    )
    response = POLICY("s", refused, tools)
    assert response.tool_calls[0].name == "request_approval"
    assert response.tool_calls[0].arguments["tool"] == "reset_trip"
    assert response.tool_calls[0].arguments["args"] == {}
    requested = refused + _turn("", ("request_approval", {"approval_id": "apr1"}))[1:]
    assert _first_call(requested) == ("wait_for_approval", {"approval_id": "apr1", "timeout_s": 300})
    granted = (
        requested
        + _turn(
            "",
            (
                "wait_for_approval",
                {"status": "granted", "tool": "reset_trip", "args": {}, "approval_id": "apr1"},
            ),
        )[1:]
    )
    assert _first_call(granted) == ("reset_trip", {"approval_id": "apr1"})
    denied = requested + _turn("", ("wait_for_approval", {"status": "denied", "tool": "reset_trip"}))[1:]
    assert "did not grant" in _text(denied)


def test_refusals_and_errors_become_plain_language() -> None:
    assert "capability manifest" in _text(
        _turn("x", ("bypass", {"code": "tool_not_available", "error": "nope"}))
    )
    assert "capability manifest" in _text(_turn("x", ("ack", {"policy": "never", "error": "never"})))
    assert "rig refused force_safe" in _text(_turn("x", ("force_safe", {"error": "boom"})))
    assert "no procedure attached" in _text(_turn("x", ("read_skill", {"name": "s"})))
    assert "I can run these procedures: a, b" in _text(
        _turn("x", ("list_skills", {"skills": [{"name": "a"}, {"name": "b"}]}))
    )


def test_run_progression_and_reports() -> None:
    assert _first_call(_turn("x", ("read_skill", {"procedure_id": "p"}))) == (
        "run_procedure",
        {"procedure_id": "p"},
    )
    assert _first_call(_turn("x", ("run_procedure", {"run_id": "r"}))) == (
        "wait_for_run",
        {"run_id": "r", "timeout_s": 120},
    )
    waiting = {"run_id": "r", "status": "running", "terminal": False, "current_step": "s1"}
    assert _first_call(_turn("x", ("wait_for_run", waiting))) == (
        "wait_for_run",
        {"run_id": "r", "timeout_s": 120},
    )
    assert "still in progress" in _text(_turn("x", ("wait_for_run", waiting), ("wait_for_run", waiting)))
    awaiting = {
        "run_id": "r",
        "status": "awaiting_operator",
        "steps": [{"status": "passed"}, {"status": "awaiting", "instruction": "Press the button."}],
    }
    assert "Press the button." in _text(_turn("x", ("wait_for_run", awaiting)))
    failed = {
        "run_id": "r",
        "terminal": True,
        "status": "failed",
        "procedure_id": "p",
        "outcome_reason": "step s2 failed",
        "steps": [{"step_id": "s2", "status": "failed", "reason": "timeout"}],
        "checks": [{"passed": False}],
        "kernel_events": ["a", "b"],
        "recording": {"filename": "f.csv", "samples": 3, "sha256": "abcdef0123456789"},
        "recovery": "Vent the line.",
    }
    text = _text(_turn("x", ("wait_for_run", failed)))
    assert (
        "FAILED" in text and "s2 (timeout)" in text and "Recovery: Vent the line." in text and "f.csv" in text
    )
    assert "Checks 0/1" in text


def test_state_and_command_summaries() -> None:
    state = {
        "samples": [{"channel_id": "p", "value": 1.5, "unit": "bar"}],
        "guardrail": {"estop_active": True, "trip_latched": True, "reason": "estop_open"},
        "outputs": {"gpio23_command_high": True},
    }
    text = _text(_turn("status", ("read_state", state)))
    assert (
        "p 1.5 bar" in text and "E-stop active" in text and "trip latched" in text and "output HIGH" in text
    )
    cmd = _text(
        _turn(
            "x",
            (
                "request_permit",
                {"guardrail": {"event": "permit_accepted", "reason": "permit_active"}, "outputs": {}},
            ),
        )
    )
    assert "permit_accepted" in cmd
    assert "aborted" in _text(_turn("x", ("abort_procedure", {"run_id": "r"})))
    assert "Done: mystery" in _text(_turn("x", ("mystery", {"k": 1})))


def test_powerdown_sequence_follows_the_skill() -> None:
    passed = {"run_id": "r", "terminal": True, "status": "passed", "procedure_id": "safe_powerdown"}
    assert _first_call(_turn("shut down", ("wait_for_run", passed))) == (
        "export_evidence",
        {"label": "pre-shutdown"},
    )
    exported = _turn("shut down", ("wait_for_run", passed), ("export_evidence", {"filename": "x.zip"}))
    assert _first_call(exported) == ("shutdown", {"reason": "bench work complete; evidence exported"})
    done = (
        exported
        + _turn("", ("shutdown", {"status": "shutting_down", "record": {"poweroff": "scheduled"}}))[1:]
    )
    text = _text(done)
    assert "Shutdown accepted" in text and "Poweroff: scheduled" in text
