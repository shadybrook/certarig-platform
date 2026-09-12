"""Procedure drafts that do not need an LLM. Studio's authoring wizard uses these."""

from __future__ import annotations

from typing import Any


def templates() -> list[dict[str, Any]]:
    return [
        {
            "id": "guardrail_trip",
            "title": "Guardrail trip and recover",
            "needs": ["signal"],
        },
        {
            "id": "truth_table",
            "title": "Output truth table",
            "needs": [],
        },
        {
            "id": "soak",
            "title": "Timed soak",
            "needs": ["signal"],
        },
        {
            "id": "anomaly_snapshot",
            "title": "Anomaly snapshot",
            "needs": [],
        },
        {
            "id": "blank",
            "title": "Blank procedure",
            "needs": [],
        },
    ]


def build_procedure(
    template_id: str,
    *,
    signal: str = "pressure",
    concept: str | None = None,
    trip: float = 4.2,
    hold_s: float = 2.0,
    title: str | None = None,
) -> dict[str, Any]:
    concept_name = concept or signal
    if template_id == "guardrail_trip":
        return {
            "id": f"{signal}_guardrail"[:64],
            "title": title or f"{signal} guardrail",
            "version": 1,
            "domain": "process",
            "timeout_s": 600,
            "applies_to": {"concepts": [concept_name]},
            "record": True,
            "steps": [
                {
                    "id": "pre",
                    "type": "expect",
                    "predicate": {"signal": signal, "op": "<", "value": trip},
                    "within_ms": 30000,
                },
                {"id": "arm", "type": "command", "command": "permit"},
                {
                    "id": "raise",
                    "type": "await_operator",
                    "instruction": f"Raise {signal} slowly past {trip}.",
                    "timeout_s": 180,
                },
                {
                    "id": "trip",
                    "type": "trigger",
                    "predicate": {"signal": signal, "op": ">", "value": trip},
                    "timeout_s": 120,
                },
                {
                    "id": "off",
                    "type": "expect",
                    "predicate": {"state": "output_high", "eq": False},
                    "within_ms": 5000,
                },
                {"id": "end_safe", "type": "command", "command": "safe"},
            ],
        }
    if template_id == "truth_table":
        return {
            "id": "output_truth_table",
            "title": title or "Output truth table",
            "version": 1,
            "domain": "electronics",
            "timeout_s": 120,
            "record": True,
            "steps": [
                {"id": "safe", "type": "command", "command": "safe"},
                {"id": "reset", "type": "command", "command": "reset"},
                {"id": "permit", "type": "command", "command": "permit"},
                {
                    "id": "high",
                    "type": "expect",
                    "predicate": {"state": "output_high", "eq": True},
                    "within_ms": 5000,
                },
                {"id": "off", "type": "command", "command": "safe"},
            ],
        }
    if template_id == "soak":
        return {
            "id": f"{signal}_soak"[:64],
            "title": title or f"{signal} soak",
            "version": 1,
            "domain": "reliability",
            "timeout_s": 300,
            "applies_to": {"concepts": [concept_name]},
            "record": True,
            "steps": [
                {
                    "id": "in_band",
                    "type": "expect",
                    "predicate": {"signal": signal, "op": "<", "value": trip},
                    "within_ms": 30000,
                },
                {"id": "hold", "type": "wait", "duration_ms": max(1, int(hold_s * 1000))},
                {
                    "id": "still_in_band",
                    "type": "expect",
                    "predicate": {"signal": signal, "op": "<", "value": trip},
                    "within_ms": 10000,
                },
                {"id": "end_safe", "type": "command", "command": "safe"},
            ],
        }
    if template_id == "anomaly_snapshot":
        return {
            "id": "anomaly_snapshot",
            "title": title or "Anomaly snapshot",
            "version": 1,
            "record": False,
            "steps": [{"id": "mark", "type": "wait", "duration_ms": 200}],
        }
    return {
        "id": "untitled",
        "title": title or "Untitled procedure",
        "version": 1,
        "record": True,
        "steps": [{"id": "safe", "type": "command", "command": "safe"}],
    }
