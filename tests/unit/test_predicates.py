from __future__ import annotations

import math

import pytest

from certarig.edge.config import load_config
from certarig.edge.runtime.facts import Facts, build_facts, concept_index
from certarig.edge.runtime.predicates import PredicateError, describe, evaluate, observed, referenced_signals
from tests.support import CONFIG_DIR

CONFIG = load_config(CONFIG_DIR / "rig.wave1.json")


def facts(**overrides: object) -> Facts:
    base = Facts(
        signals={"pressure": 2.0, "flow": 8.0, "pressure_emulator": 2.0, "flow_emulator": 8.0},
        signal_states={"pressure": "safe", "flow": "safe"},
        qualities={"pressure": "good", "flow": "good"},
        states={
            "estop_active": False,
            "trip_latched": True,
            "permit_requested": False,
            "drive_high": False,
            "process_healthy": True,
            "output_high": False,
            "relay_energized_expected": False,
            "recording_active": False,
            "reason": "reset_required",
            "last_event": "process_safe_reset_required",
            "status": "ok",
        },
    )
    for key, value in overrides.items():
        getattr(base, key).update(value)  # type: ignore[arg-type]
    return base


@pytest.mark.parametrize(
    "op, value, expected",
    [
        ("<", 3.0, True),
        ("<=", 2.0, True),
        (">", 2.0, False),
        (">=", 2.0, True),
        ("==", 2.0, True),
        ("!=", 2.0, False),
    ],
)
def test_numeric_operators(op: str, value: float, expected: bool) -> None:
    assert evaluate({"signal": "pressure", "op": op, "value": value}, facts()) is expected


def test_missing_or_non_finite_signal_is_never_true() -> None:
    assert evaluate({"signal": "nope", "op": "<", "value": 1e9}, facts()) is False
    assert (
        evaluate({"signal": "pressure", "op": "<", "value": 1e9}, facts(signals={"pressure": None})) is False
    )
    assert (
        evaluate({"signal": "pressure", "op": ">", "value": -1}, facts(signals={"pressure": math.nan}))
        is False
    )


def test_state_quality_signal_state_and_combinators() -> None:
    f = facts()
    assert evaluate({"state": "estop_active", "eq": False}, f)
    assert evaluate({"state": "reason", "eq": "reset_required"}, f)
    assert not evaluate({"state": "reason", "eq": "permit_active"}, f)
    assert evaluate({"quality": "pressure", "eq": "good"}, f)
    assert evaluate({"quality": "absent", "eq": "missing"}, f)
    assert evaluate({"signal_state": "pressure", "eq": "safe"}, f)
    assert evaluate(
        {"all": [{"state": "estop_active", "eq": False}, {"signal": "flow", "op": "<", "value": 9}]}, f
    )
    assert not evaluate(
        {"all": [{"state": "estop_active", "eq": True}, {"signal": "flow", "op": "<", "value": 9}]}, f
    )
    assert evaluate(
        {"any": [{"state": "estop_active", "eq": True}, {"signal": "flow", "op": "<", "value": 9}]}, f
    )
    assert evaluate({"not": {"state": "output_high", "eq": True}}, f)


def test_errors_for_unknown_shapes() -> None:
    with pytest.raises(PredicateError):
        evaluate({"state": "made_up", "eq": True}, facts())
    with pytest.raises(PredicateError):
        evaluate({"signal": "pressure", "op": "~", "value": 1}, facts())
    with pytest.raises(PredicateError):
        evaluate({"weird": 1}, facts())


def test_describe_observed_and_referenced_signals() -> None:
    predicate = {
        "all": [
            {"signal": "pressure", "op": ">", "value": 4.2},
            {"not": {"state": "output_high", "eq": True}},
        ]
    }
    assert describe(predicate) == "(pressure > 4.2 and not output_high == true)"
    assert observed(predicate, facts()) == {"pressure": 2.0, "output_high": False}
    assert referenced_signals({"any": [predicate, {"quality": "flow", "eq": "good"}]}) == {"pressure", "flow"}
    assert describe({"quality": "flow", "eq": "good"}) == "flow quality == good"
    assert describe({"signal_state": "flow", "eq": "high"}) == "flow state == high"
    assert "weird" in describe({"weird": 1})


def test_build_facts_from_runtime_state() -> None:
    index = concept_index(CONFIG)
    assert index["pressure"] == "pressure_emulator" and index["flow_emulator"] == "flow_emulator"
    state = {
        "status": "ok",
        "captured_at": "t",
        "sample_index": 7,
        "samples": [
            {"channel_id": "pressure_emulator", "value": 1.5, "quality": "good"},
            {"channel_id": "flow_emulator", "value": None, "quality": "bad"},
        ],
        "guardrail": {
            "estop_active": False,
            "trip_latched": False,
            "permit_requested": True,
            "drive_high": True,
            "process_healthy": True,
            "reason": "permit_active",
            "channels": [
                {"channel_id": "pressure_emulator", "value": 1.5, "state": "safe"},
                {"channel_id": "flow_emulator", "value": None, "state": "invalid"},
            ],
        },
        "outputs": {"gpio23_command_high": True, "relay_energized_expected": True},
        "recording": {"active": True},
        "last_event": "permit_accepted",
    }
    built = build_facts(CONFIG, state)
    assert built.signal("pressure") == 1.5 and built.signal("flow") is None
    assert built.signal_states["flow"] == "invalid" and built.qualities["flow"] == "bad"
    assert built.states["drive_high"] is True and built.states["recording_active"] is True
    assert built.sample_index == 7
    # missing everything still yields conservative defaults
    empty = build_facts(CONFIG, {})
    assert empty.states["estop_active"] is True and empty.signal_states["pressure"] == "missing"
