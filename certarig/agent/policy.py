"""A deterministic rule-based "brain" for the FakeProvider.

It lets the whole agent path (intent -> skill -> procedure -> approvals -> report) run end to end
without an LLM API key: in CI, in the Studio demo and on the bench. When a real provider is
configured this module is not used. It is intentionally simple and transparent.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from .providers.base import Message, ProviderResponse, ToolSpec
from .providers.fake import call, say, tool_call
from .skills import SkillIndex

_STATUS_WORDS = {
    "status",
    "state",
    "reading",
    "readings",
    "pressure",
    "flow",
    "telemetry",
    "how is",
    "what is",
}
_SAFE_WORDS = {"stop", "safe", "halt", "kill"}
_ABORT_WORDS = {"abort", "cancel"}
_ACK_WORDS = {"done", "acknowledged", "confirmed", "continue"}


class RuleBasedPolicy:
    def __init__(self, skills: SkillIndex, max_waits: int = 6) -> None:
        self.skills = skills
        self.max_waits = max_waits

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _last_user(messages: Sequence[Message]) -> str:
        for message in reversed(messages):
            if message.role == "user":
                return message.content
        return ""

    @staticmethod
    def _turn(messages: Sequence[Message]) -> list[Message]:
        """Messages since the last user message (the current turn)."""
        index = max((i for i, m in enumerate(messages) if m.role == "user"), default=-1)
        return list(messages[index + 1 :])

    @staticmethod
    def _results(turn: Sequence[Message]) -> list[tuple[str, dict[str, Any]]]:
        out: list[tuple[str, dict[str, Any]]] = []
        for message in turn:
            if message.role == "tool":
                try:
                    out.append((message.name or "", json.loads(message.content)))
                except json.JSONDecodeError:
                    out.append((message.name or "", {"raw": message.content}))
        return out

    @staticmethod
    def _tool_available(tools: Sequence[ToolSpec], name: str) -> bool:
        return any(tool.name == name for tool in tools)

    # ------------------------------------------------------------ policy
    def __call__(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        turn = self._turn(messages)
        results = self._results(turn)
        request = self._last_user(messages).lower()
        if not results:
            return self._open_turn(request, messages, tools)
        return self._continue_turn(request, results, tools, messages)

    def _open_turn(
        self, request: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        words = set(re.findall(r"[a-z]+", request))
        if words & _ABORT_WORDS:
            run_id = self._active_run_id(messages)
            if run_id:
                return call(
                    tool_call("abort_procedure", {"run_id": run_id, "reason": "operator asked to abort"})
                )
            return call(tool_call("force_safe"))
        if words & _SAFE_WORDS and not (words & {"powerdown", "shutdown", "shut", "power"}):
            return call(tool_call("force_safe"))
        if words & _ACK_WORDS:
            run_id = self._active_run_id(messages)
            if run_id:
                return call(tool_call("wait_for_run", {"run_id": run_id, "timeout_s": 60}))
        matches = self.skills.match(request)
        if matches and matches[0][1] >= 0.5:
            skill = matches[0][0]
            return call(tool_call("read_skill", {"name": skill.name}))
        if words & _STATUS_WORDS:
            return call(tool_call("read_state"))
        return call(tool_call("list_skills"))

    def _continue_turn(
        self,
        request: str,
        results: list[tuple[str, dict[str, Any]]],
        tools: Sequence[ToolSpec],
        messages: Sequence[Message],
    ) -> ProviderResponse:
        name, last = results[-1]
        # refusals first
        if last.get("code") == "approval_required" and self._tool_available(tools, "request_approval"):
            failed_tool = str(last.get("tool"))
            return call(
                tool_call(
                    "request_approval",
                    {
                        "tool": failed_tool,
                        "args": self._last_tool_args(messages, failed_tool),
                        "reason": f"operator asked: {request[:120]}",
                    },
                )
            )
        if name == "request_approval" and last.get("approval_id"):
            return call(
                tool_call("wait_for_approval", {"approval_id": last["approval_id"], "timeout_s": 300})
            )
        if name == "wait_for_approval":
            if last.get("status") == "granted":
                return call(
                    tool_call(
                        str(last["tool"]), {**dict(last.get("args", {})), "approval_id": last["approval_id"]}
                    )
                )
            return say(
                f"The operator did not grant approval for {last.get('tool')} (status {last.get('status')}). Nothing was changed."
            )
        if last.get("code") == "tool_not_available" or (last.get("policy") == "never"):
            return say(
                f"I cannot do that on this rig: {last.get('error')}. The capability manifest does not allow it."
            )
        if "error" in last and name not in {"wait_for_run", "read_skill"}:
            return say(f"The rig refused {name}: {last['error']}. The rig is unchanged.")

        if name == "list_skills":
            names = ", ".join(s["name"] for s in last.get("skills", []))
            return say(f"I can run these procedures: {names}. Tell me which one, or ask for the rig status.")
        if name == "read_skill":
            procedure_id = last.get("procedure_id")
            if not procedure_id:
                return say(f"Skill {last.get('name')} has no procedure attached.")
            return call(tool_call("run_procedure", {"procedure_id": str(procedure_id)}))
        if name == "run_procedure":
            return call(tool_call("wait_for_run", {"run_id": str(last["run_id"]), "timeout_s": 120}))
        if name == "wait_for_run":
            waits = sum(1 for n, _ in results if n == "wait_for_run")
            if last.get("status") == "awaiting_operator":
                step = next((s for s in last.get("steps", []) if s["status"] == "awaiting"), None)
                instruction = step["instruction"] if step else "the current step"
                return say(
                    f"Operator action needed: {instruction} Acknowledge the step in Studio when done; "
                    f"I cannot acknowledge physical steps myself. (run {last['run_id']})"
                )
            if not last.get("terminal"):
                if waits >= self.max_waits:
                    return say(
                        f"Run {last['run_id']} is still in progress at step {last.get('current_step')}. Ask me again for an update."
                    )
                return call(tool_call("wait_for_run", {"run_id": str(last["run_id"]), "timeout_s": 120}))
            if last.get("procedure_id") == "safe_powerdown" and last.get("status") == "passed":
                # SKILL.md sequence: bundle the evidence, then ask for the (human approved) shutdown.
                return call(tool_call("export_evidence", {"label": "pre-shutdown"}))
            return say(self._report(last))
        if name == "export_evidence":
            return call(tool_call("shutdown", {"reason": "bench work complete; evidence exported"}))
        if name == "shutdown":
            record = last.get("record", {})
            return say(
                f"Shutdown accepted ({last.get('status')}); kernel forced safe and evidence flushed. "
                f"Poweroff: {record.get('poweroff')}. Wait for the SD activity LED to go idle, then remove "
                "PWR IN and the external 5 V supply."
            )
        if name == "read_state":
            return say(self._state_summary(last))
        if name in {"force_safe", "reset_trip", "request_permit"}:
            guardrail = last.get("guardrail", {})
            return say(
                f"Kernel event {guardrail.get('event')}; reason {guardrail.get('reason')}; output high: {last.get('outputs', {}).get('gpio23_command_high')}."
            )
        if name == "abort_procedure":
            return say(f"Run {last.get('run_id')} aborted; the kernel was forced safe.")
        return say(f"Done: {name} returned {json.dumps(last)[:300]}.")

    @staticmethod
    def _last_tool_args(messages: Sequence[Message], name: str) -> dict[str, Any]:
        for message in reversed(messages):
            if message.role == "assistant":
                for item in message.tool_calls:
                    if item.name == name:
                        return {k: v for k, v in item.arguments.items() if k != "approval_id"}
        return {}

    @staticmethod
    def _active_run_id(messages: Sequence[Message]) -> str | None:
        for message in reversed(messages):
            if message.role == "tool" and message.name in {"run_procedure", "wait_for_run"}:
                try:
                    payload = json.loads(message.content)
                except json.JSONDecodeError:
                    continue
                if payload.get("run_id") and not payload.get("terminal"):
                    return str(payload["run_id"])
        return None

    @staticmethod
    def _report(run: dict[str, Any]) -> str:
        failed = [s for s in run.get("steps", []) if s["status"] == "failed"]
        checks = run.get("checks", [])
        passed_checks = sum(1 for c in checks if c["passed"])
        events = ", ".join(run.get("kernel_events", [])[-6:]) or "none"
        lines = [
            f"Procedure {run.get('procedure_id')} {str(run.get('status')).upper()}: {run.get('outcome_reason')}.",
            f"Checks {passed_checks}/{len(checks)} passed. Kernel events: {events}.",
        ]
        if failed:
            lines.append(
                "Failed steps: " + "; ".join(f"{s['step_id']} ({s.get('reason')})" for s in failed) + "."
            )
        if run.get("recording"):
            rec = run["recording"]
            lines.append(
                f"Evidence CSV {rec.get('filename')} ({rec.get('samples')} rows, sha256 {str(rec.get('sha256'))[:12]}…)."
            )
        if run.get("status") != "passed" and run.get("recovery"):
            lines.append("Recovery: " + str(run["recovery"]).strip())
        return " ".join(lines)

    @staticmethod
    def _state_summary(state: dict[str, Any]) -> str:
        samples = ", ".join(f"{s['channel_id']} {s['value']} {s['unit']}" for s in state.get("samples", []))
        guardrail = state.get("guardrail", {})
        return (
            f"{samples}. E-stop {'active' if guardrail.get('estop_active') else 'released'}, "
            f"trip {'latched' if guardrail.get('trip_latched') else 'clear'}, reason {guardrail.get('reason')}, "
            f"output {'HIGH' if state.get('outputs', {}).get('gpio23_command_high') else 'off'}."
        )
