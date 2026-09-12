"""Closed predicate grammar evaluated by pure functions.

Grammar (validated by ``procedure.schema.json``)::

    {"signal": "pressure", "op": ">", "value": 4.2}
    {"signal_state": "pressure", "eq": "high"}
    {"quality": "flow", "eq": "good"}
    {"state": "drive_high", "eq": false}
    {"all": [...]}, {"any": [...]}, {"not": {...}}

A missing signal makes a numeric comparison false (never true by accident).
"""

from __future__ import annotations

import math
import operator
from collections.abc import Callable
from typing import Any

from .facts import Facts

_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": lambda a, b: math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9),
    "!=": lambda a, b: not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9),
}


class PredicateError(ValueError):
    pass


def evaluate(predicate: dict[str, Any], facts: Facts) -> bool:
    if "signal" in predicate:
        value = facts.signals.get(str(predicate["signal"]))
        if value is None or not math.isfinite(value):
            return False
        op = _OPS.get(str(predicate["op"]))
        if op is None:
            raise PredicateError(f"unknown operator {predicate['op']!r}")
        return bool(op(float(value), float(predicate["value"])))
    if "signal_state" in predicate:
        return facts.signal_states.get(str(predicate["signal_state"]), "missing") == predicate["eq"]
    if "quality" in predicate:
        return facts.qualities.get(str(predicate["quality"]), "missing") == predicate["eq"]
    if "state" in predicate:
        current = facts.states.get(str(predicate["state"]))
        expected = predicate["eq"]
        if current is None:
            raise PredicateError(f"unknown state {predicate['state']!r}")
        if isinstance(expected, bool) or isinstance(current, bool):
            return bool(current) is bool(expected)
        return str(current) == str(expected)
    if "all" in predicate:
        return all(evaluate(item, facts) for item in predicate["all"])
    if "any" in predicate:
        return any(evaluate(item, facts) for item in predicate["any"])
    if "not" in predicate:
        return not evaluate(predicate["not"], facts)
    raise PredicateError(f"unsupported predicate {predicate!r}")


def describe(predicate: dict[str, Any]) -> str:
    if "signal" in predicate:
        return f"{predicate['signal']} {predicate['op']} {predicate['value']}"
    if "signal_state" in predicate:
        return f"{predicate['signal_state']} state == {predicate['eq']}"
    if "quality" in predicate:
        return f"{predicate['quality']} quality == {predicate['eq']}"
    if "state" in predicate:
        return f"{predicate['state']} == {str(predicate['eq']).lower()}"
    if "all" in predicate:
        return "(" + " and ".join(describe(item) for item in predicate["all"]) + ")"
    if "any" in predicate:
        return "(" + " or ".join(describe(item) for item in predicate["any"]) + ")"
    if "not" in predicate:
        return "not " + describe(predicate["not"])
    return repr(predicate)


def observed(predicate: dict[str, Any], facts: Facts) -> dict[str, Any]:
    """Snapshot of the values a predicate looked at, for evidence."""
    if "signal" in predicate:
        return {predicate["signal"]: facts.signals.get(str(predicate["signal"]))}
    if "signal_state" in predicate:
        return {f"{predicate['signal_state']}.state": facts.signal_states.get(str(predicate["signal_state"]))}
    if "quality" in predicate:
        return {f"{predicate['quality']}.quality": facts.qualities.get(str(predicate["quality"]))}
    if "state" in predicate:
        return {predicate["state"]: facts.states.get(str(predicate["state"]))}
    merged: dict[str, Any] = {}
    for item in (
        predicate.get("all", [])
        + predicate.get("any", [])
        + ([predicate["not"]] if "not" in predicate else [])
    ):
        merged.update(observed(item, facts))
    return merged


def referenced_signals(predicate: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("signal", "signal_state", "quality"):
        if key in predicate:
            names.add(str(predicate[key]))
    for item in predicate.get("all", []) + predicate.get("any", []):
        names |= referenced_signals(item)
    if "not" in predicate:
        names |= referenced_signals(predicate["not"])
    return names
