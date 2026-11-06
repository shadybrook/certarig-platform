"""Machine tools compatible with the existing AgentSession and provider adapters."""

from __future__ import annotations

import time
from typing import Any

from certarig.agent.providers.base import ToolSpec
from certarig.agent.tools import ToolResult

from .gateway import Gateway, Intent


class MachineTools:
    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                "machine_status",
                "Observe the commissioned VIRTUAL printer.",
                {"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                "machine_command",
                "Request a job action; start and resume need operator approval.",
                {
                    "type": "object",
                    "properties": {
                        "machine_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["start", "pause", "resume", "cancel"]},
                        "job": {"type": "string"},
                        "sha256": {"type": "string"},
                        "approval_id": {"type": "string"},
                    },
                    "required": ["machine_id", "action", "job", "sha256"],
                    "additionalProperties": False,
                },
            ),
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        try:
            if name == "machine_status" and not arguments:
                result = self.gateway.adapter.status()
            elif name == "machine_command":
                if set(arguments) - {"machine_id", "action", "job", "sha256", "approval_id"}:
                    raise ValueError("unexpected_arguments")
                intent = Intent(**{k: v for k, v in arguments.items() if k != "approval_id"})
                result = self.gateway.execute(intent, arguments.get("approval_id"))
            else:
                raise ValueError("tool_not_available")
            return ToolResult(name, arguments, True, result, (time.monotonic() - started) * 1000)
        except Exception as exc:
            # Never echo HTTP exception objects: they may contain secret-bearing request details.
            reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            return ToolResult(name, {}, False, {"error": reason}, (time.monotonic() - started) * 1000)
