"""The agent orchestrator: model <-> tools loop with hard limits and a full transcript.

The orchestrator is deliberately dumb about safety: it forwards tool calls to the registry and
records what happened. Safety lives in the Edge node (manifest, approvals, kernel). What the
orchestrator does enforce is bookkeeping: bounded turns, bounded tool calls per turn, no
unknown tools, and a transcript entry for every event.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .providers.base import (
    LLMProvider,
    Message,
    ProviderError,
    ToolSpec,
    context_fingerprint,
)
from .tools import ToolRegistry, ToolResult
from .transcript import Transcript

SYSTEM_PROMPT = """You are the CertaRig test-operations assistant for the rig "{rig_id}" (revision {revision}).

You interpret operator intent, choose and run approved procedures, relay instructions, and explain
results in plain engineering language. You never evaluate a measurement yourself: the deterministic
Edge kernel compares numbers, enforces limits and drives outputs. You act only through the tools you
are given. Tools you do not see do not exist for you.

Rules:
1. Before running a procedure, read its skill guidance (read_skill) unless you already have it in this conversation.
2. Start procedures with run_procedure and follow them with wait_for_run. Relay any operator instruction verbatim.
3. Never claim a result the tools did not return. Quote outcome_reason and kernel_events when reporting.
4. If a tool returns approval_required, explain to the operator what you want to do and why, call
   request_approval, then wait_for_approval, then retry with approval_id. Never try to work around a refusal.
5. If anything looks unsafe or unclear, call force_safe and ask the operator.
6. Be brief. Operators are busy. Numbers with units. No speculation about hardware you cannot observe.
7. Commissioning is a fact-gathering loop, not a scripted quiz (same idea as plan mode). Before you
   propose a rig map you must learn: modules on the bench; each analogue signal (customer name,
   concept, unit, trip); what stays observe-only. Diagram notes are optional. Ask in your own words,
   in any order, one question or several. A single operator message may fill every slot. After each
   reply call answer_interview with what you learned (or the raw text). Call read_interview to see
   missing facts. Call attach_interview_image only to store a labeled photo (diagram slot).
   Call propose_rig_map only when missing is empty. A human applies. Never energise
   from a guessed map. request_auto_arm is usually not even visible; it never calls set_valve.

Rig contract: config_hash {config_hash}, capability manifest {manifest_id}. Hardware mode {hardware_mode}.
Signals: {signals}.

Skills available:
{skills}
"""


class OrchestratorError(RuntimeError):
    pass


class ToolExecutor(Protocol):
    def specs(self) -> list[ToolSpec]: ...

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult: ...


def build_system_prompt(registry: ToolRegistry) -> str:
    rig = registry.client.rig()
    signals = ", ".join(
        f"{row['channel_id']} ({row['concept']}, {row['unit']})" for row in rig.get("signals", [])
    )
    return SYSTEM_PROMPT.format(
        rig_id=rig["rig"]["rig_id"],
        revision=rig["rig"]["revision"],
        config_hash=rig["config_hash"][:16],
        manifest_id=rig["manifest_id"],
        hardware_mode=rig["rig"]["hardware"]["mode"],
        signals=signals,
        skills=registry.skills.prompt_index() or "- none",
    )


@dataclass
class TurnResult:
    text: str
    tool_results: list[ToolResult] = field(default_factory=list)
    model_calls: int = 0
    stopped_reason: str = "end_turn"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tool_calls": [{"name": r.name, "arguments": r.arguments, "ok": r.ok} for r in self.tool_results],
            "model_calls": self.model_calls,
            "stopped_reason": self.stopped_reason,
        }


class AgentSession:
    def __init__(
        self,
        provider: LLMProvider,
        registry: ToolExecutor,
        transcript: Transcript,
        max_model_calls_per_turn: int = 16,
        max_tool_calls_per_response: int = 4,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.transcript = transcript
        self.max_model_calls = max_model_calls_per_turn
        self.max_tool_calls = max_tool_calls_per_response
        self.on_event = on_event
        self.messages: list[Message] = []
        if system_prompt is not None:
            self.system = system_prompt
        elif isinstance(registry, ToolRegistry):
            self.system = build_system_prompt(registry)
        else:
            raise OrchestratorError("system_prompt is required when the executor is not a ToolRegistry")
        contract = registry.client.contract_hash if isinstance(registry, ToolRegistry) else None
        self.transcript.write(
            "session_started",
            provider=provider.name,
            model=provider.model,
            system=self.system,
            tools=[spec.name for spec in registry.specs()],
            contract_hash=contract,
        )

    # ------------------------------------------------------------ loop
    def _emit(self, entry: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event(entry)

    def _tools(self) -> list[ToolSpec]:
        return self.registry.specs()

    def send(self, user_text: str) -> TurnResult:
        self.messages.append(Message(role="user", content=user_text))
        self._emit(self.transcript.write("user", content=user_text))
        results: list[ToolResult] = []
        model_calls = 0
        while True:
            if model_calls >= self.max_model_calls:
                text = (
                    "I stopped: too many steps in one turn. The rig is unchanged since the last tool result."
                )
                self.messages.append(Message(role="assistant", content=text))
                self._emit(self.transcript.write("assistant", content=text, stopped_reason="max_model_calls"))
                return TurnResult(text, results, model_calls, "max_model_calls")
            tools = self._tools()
            try:
                response = self.provider.complete(self.system, self.messages, tools)
            except ProviderError as exc:
                self._emit(self.transcript.write("error", error=str(exc)))
                raise OrchestratorError(str(exc)) from exc
            model_calls += 1
            self._emit(
                self.transcript.write(
                    "model_response",
                    fingerprint=context_fingerprint(self.system, self.messages, tools),
                    response=response.to_dict(),
                )
            )
            if not response.tool_calls:
                text = response.text or ""
                self.messages.append(Message(role="assistant", content=text))
                self._emit(self.transcript.write("assistant", content=text))
                return TurnResult(text, results, model_calls, response.stop_reason)
            calls = response.tool_calls[: self.max_tool_calls]
            self.messages.append(
                Message(role="assistant", content=response.text or "", tool_calls=tuple(calls))
            )
            for call in calls:
                self._emit(
                    self.transcript.write("tool_call", id=call.id, name=call.name, arguments=call.arguments)
                )
                result = self.registry.execute(call.name, call.arguments)
                results.append(result)
                self._emit(
                    self.transcript.write(
                        "tool_result",
                        id=call.id,
                        name=call.name,
                        ok=result.ok,
                        elapsed_ms=result.elapsed_ms,
                        result=result.result,
                    )
                )
                self.messages.append(
                    Message(role="tool", content=result.content(), tool_call_id=call.id, name=call.name)
                )
            if len(response.tool_calls) > self.max_tool_calls:
                self.messages.append(
                    Message(
                        role="user",
                        content=f"Only the first {self.max_tool_calls} tool calls were executed. Continue.",
                    )
                )

    def close(self, reason: str = "closed") -> None:
        self.transcript.write("session_ended", reason=reason, messages=len(self.messages))


# ---------------------------------------------------------------------- replay
def replay_session(transcript_path: str, strict: bool = True) -> list[dict[str, Any]]:
    """Re-drive a recorded session offline: recorded model responses + recorded tool results.

    Returns the assistant texts produced. If ``strict`` the replay fails on any divergence in
    the context shown to the model, which proves the transcript is a complete, reproducible
    record of the session.
    """
    from .providers.fake import ReplayProvider

    rows = Transcript.read(transcript_path)
    started = next(row for row in rows if row["kind"] == "session_started")
    recorded_results = [row for row in rows if row["kind"] == "tool_result"]
    provider = ReplayProvider(transcript_path, strict=strict)

    class _ReplayRegistry:
        def __init__(self) -> None:
            self._index = 0

        def specs(self) -> list[ToolSpec]:
            return [ToolSpec(name, "", {}) for name in started["tools"]]

        def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
            if self._index >= len(recorded_results):
                raise OrchestratorError("replay: more tool calls than recorded")
            record = recorded_results[self._index]
            self._index += 1
            if record["name"] != name:
                raise OrchestratorError(f"replay divergence: tool {name} vs recorded {record['name']}")
            return ToolResult(
                name, arguments, bool(record["ok"]), record["result"], float(record["elapsed_ms"])
            )

    outputs: list[dict[str, Any]] = []
    session = AgentSession(
        provider,
        _ReplayRegistry(),
        Transcript(transcript_path + ".replay.jsonl"),
        max_model_calls_per_turn=64,
        system_prompt=started["system"],
    )
    for row in rows:
        if row["kind"] == "user":
            result = session.send(row["content"])
            outputs.append(result.to_dict())
    if strict and provider.remaining:
        raise OrchestratorError("replay: recording has more model responses than were consumed")
    return outputs


def summarize_transcript(path: str) -> dict[str, Any]:
    rows = Transcript.read(path)
    return {
        "session_id": rows[0]["session_id"] if rows else None,
        "provider": next((r["provider"] for r in rows if r["kind"] == "session_started"), None),
        "user_turns": sum(1 for r in rows if r["kind"] == "user"),
        "model_calls": sum(1 for r in rows if r["kind"] == "model_response"),
        "tool_calls": sum(1 for r in rows if r["kind"] == "tool_call"),
        "refusals": sum(1 for r in rows if r["kind"] == "tool_result" and not r["ok"]),
        "tools_used": sorted({r["name"] for r in rows if r["kind"] == "tool_call"}),
        "entries": len(rows),
        "assistant_final": next((r["content"] for r in reversed(rows) if r["kind"] == "assistant"), None),
    }


def pretty(entry: dict[str, Any]) -> str:
    kind = entry["kind"]
    if kind == "tool_call":
        return f"→ {entry['name']}({json.dumps(entry['arguments'])})"
    if kind == "tool_result":
        status = "ok" if entry["ok"] else "refused"
        return f"← {entry['name']} {status} ({entry['elapsed_ms']} ms)"
    if kind == "assistant":
        return f"assistant: {entry['content']}"
    if kind == "user":
        return f"operator: {entry['content']}"
    return kind
