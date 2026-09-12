from __future__ import annotations

import json
import os
from typing import Any

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rig_id", "config_hash", "purpose", "pressure_limit_bar", "steps"],
    "properties": {
        "rig_id": {"type": "string"},
        "config_hash": {"type": "string"},
        "purpose": {"type": "string", "minLength": 1, "maxLength": 240},
        "pressure_limit_bar": {"type": "number", "exclusiveMinimum": 0},
        "steps": {
            "type": "array",
            "minItems": 1,
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "action",
                    "duration_ms",
                    "valve_open",
                    "expected_pressure_min",
                    "expected_pressure_max",
                ],
                "properties": {
                    "action": {"type": "string", "enum": ["set_valve", "hold", "sample"]},
                    "duration_ms": {"type": "integer", "minimum": 0, "maximum": 10000},
                    "valve_open": {"type": ["boolean", "null"]},
                    "expected_pressure_min": {"type": ["number", "null"]},
                    "expected_pressure_max": {"type": ["number", "null"]},
                },
            },
        },
    },
}


AGENT_INSTRUCTIONS = """You are the CertaRig planning assistant.
You may propose a short commissioning plan from the supplied read only rig snapshot and constraints.
You do not approve plans, execute plans, control GPIO, change limits, or claim that hardware is safe.
Use only the supplied rig_id and config_hash. Keep pressure_limit_bar at or below the approved abort limit.
If material evidence is missing or a sample has invalid quality, propose only a sample step and explain the evidence request in purpose.
Every proposed output will be validated again by deterministic server policy and a human must approve it before execution.
"""


def propose_plan_with_openai(
    snapshot: dict[str, Any],
    pressure_abort_bar: float,
    objective: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Return a strict plan proposal. This function has no actuator or approval capability."""

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("install the agent extra with: pip install -e '.[agent]'") from exc

    selected_model = model or os.environ.get("CERTARIG_OPENAI_MODEL", "gpt-5.5")
    client = OpenAI()
    response = client.responses.create(
        model=selected_model,
        instructions=AGENT_INSTRUCTIONS,
        input=json.dumps(
            {
                "objective": objective,
                "approved_pressure_abort_bar": pressure_abort_bar,
                "snapshot": snapshot,
            },
            sort_keys=True,
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": "certarig_plan_proposal",
                "strict": True,
                "schema": PLAN_SCHEMA,
            }
        },
    )
    proposal = json.loads(response.output_text)
    if proposal.get("rig_id") != snapshot.get("rig_id"):
        raise RuntimeError("agent returned a different rig_id")
    if proposal.get("config_hash") != snapshot.get("config_hash"):
        raise RuntimeError("agent returned a stale configuration hash")
    if float(proposal.get("pressure_limit_bar", 0)) > pressure_abort_bar:
        raise RuntimeError("agent proposal exceeds the approved pressure limit")
    return proposal
