"""Natural-language procedure authoring with a validate-and-repair loop.

The model is asked to call ``submit_procedure`` with a procedure document. The document is
validated by the Edge node (schema + rig semantics). Errors are fed back and the model may
try again a bounded number of times. The final draft is stored as *unapproved*; an engineer
approves it in Studio. The model never gets to make a procedure runnable on its own.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from certarig.edge.client import EdgeApiError, EdgeClient
from certarig.edge.schemas import load_schema

from .providers.base import LLMProvider, Message, ProviderError, ToolSpec

AUTHORING_PROMPT = """You write CertaRig procedures. A procedure is a JSON document that follows the schema below.
Only use signals that exist on this rig. Predicates use the closed grammar: signal/op/value,
signal_state/eq, quality/eq, state/eq, all/any/not. Step types: command (safe|reset|permit),
expect (predicate, within_ms, hold_ms), trigger (predicate, timeout_s, instruction),
await_operator (instruction, timeout_s, confirm), wait (duration_ms), record (start|stop|mark).
Set requires_output: true if the procedure energises the permit output.
Include an evaluate section with the checks that make the procedure pass or fail, and a
recovery paragraph for the operator.

Rig signals: {signals}
Existing procedure ids (do not reuse): {existing}

Reference procedure:
{example}

Schema (abridged):
{schema}

Respond only by calling submit_procedure.
"""

SUBMIT_TOOL = ToolSpec(
    "submit_procedure",
    "Submit the procedure document for validation.",
    {
        "type": "object",
        "properties": {"procedure": {"type": "object"}},
        "required": ["procedure"],
        "additionalProperties": False,
    },
)


@dataclass
class AuthoringResult:
    ok: bool
    procedure: dict[str, Any] | None
    errors: list[str]
    attempts: int
    draft: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


def _abridged_schema() -> str:
    schema = load_schema("procedure.schema.json")
    keep = {
        key: schema["properties"][key]
        for key in ("id", "version", "title", "requires_output", "record", "steps", "evaluate")
    }
    return json.dumps({"properties": keep, "step_types": list(_step_types(schema))}, indent=1)[:4000]


def _step_types(schema: dict[str, Any]) -> list[str]:
    types = []
    for option in schema["$defs"]["step"]["oneOf"]:
        for part in option.get("allOf", []):
            const = part.get("properties", {}).get("type", {}).get("const")
            if const:
                types.append(str(const))
    return types


def author_procedure(
    provider: LLMProvider,
    client: EdgeClient,
    request: str,
    example: dict[str, Any] | None = None,
    max_attempts: int = 3,
    submit_draft: bool = True,
) -> AuthoringResult:
    rig = client.rig()
    existing = [row["id"] for row in client.procedures().get("procedures", [])]
    signals = ", ".join(f"{row['channel_id']} as {row['concept']} ({row['unit']})" for row in rig["signals"])
    system = AUTHORING_PROMPT.format(
        signals=signals,
        existing=", ".join(existing) or "none",
        example=json.dumps(example or {}, indent=1)[:3000],
        schema=_abridged_schema(),
    )
    messages: list[Message] = [Message(role="user", content=request)]
    history: list[dict[str, Any]] = []
    errors: list[str] = []
    procedure: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = provider.complete(system, messages, [SUBMIT_TOOL])
        except ProviderError as exc:
            return AuthoringResult(False, None, [str(exc)], attempt, history=history)
        call = next((c for c in response.tool_calls if c.name == "submit_procedure"), None)
        if call is None:
            errors = ["the model did not call submit_procedure"]
            history.append({"attempt": attempt, "errors": errors, "text": response.text})
            messages.append(Message(role="assistant", content=response.text or ""))
            messages.append(Message(role="user", content="You must respond by calling submit_procedure."))
            continue
        candidate = call.arguments.get("procedure")
        validation = client.request(
            "POST", "/v1/procedures/validate", {"procedure": candidate}, contract=False
        )
        errors = list(validation.get("errors", []))
        if isinstance(candidate, dict) and candidate.get("id") in existing:
            errors.append(f"procedure id {candidate.get('id')!r} already exists; choose a new id")
        history.append(
            {
                "attempt": attempt,
                "errors": errors,
                "procedure_id": (candidate or {}).get("id") if isinstance(candidate, dict) else None,
            }
        )
        messages.append(Message(role="assistant", content="", tool_calls=(call,)))
        if not errors and isinstance(candidate, dict):
            procedure = candidate
            messages.append(
                Message(
                    role="tool", content=json.dumps({"valid": True}), tool_call_id=call.id, name=call.name
                )
            )
            break
        messages.append(
            Message(
                role="tool",
                content=json.dumps({"valid": False, "errors": errors}),
                tool_call_id=call.id,
                name=call.name,
            )
        )
        messages.append(Message(role="user", content="Fix every error listed and submit again."))
    if procedure is None:
        return AuthoringResult(False, None, errors, len(history), history=history)
    draft: dict[str, Any] | None = None
    if submit_draft:
        try:
            draft = client.post("/v1/procedures/drafts", {"procedure": procedure})
        except EdgeApiError as exc:
            return AuthoringResult(False, procedure, [str(exc)], len(history), history=history)
    return AuthoringResult(True, procedure, [], len(history), draft=draft, history=history)
