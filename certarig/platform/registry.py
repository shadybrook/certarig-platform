"""Observation-only intersection of agent tools, connector capabilities and a live lease."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import jsonschema

from certarig.agent.providers.base import ToolSpec
from certarig.agent.tools import ToolRegistry, ToolResult

from .contracts import READ_TOOLS


class ScopedRegistry:
    def __init__(self, registry: Any, allowed: list[str], guard: Callable[[], Any]):
        self.registry, self.allowed, self.guard = registry, set(allowed) & READ_TOOLS, guard

    def specs(self) -> list[ToolSpec]:
        return [s for s in self.registry.specs() if s.name in self.allowed]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        try:
            self.guard()
            spec = next((s for s in self.specs() if s.name == name), None)
            if spec is None:
                raise PermissionError("Tool is outside this agent and asset scope")
            jsonschema.validate(arguments, {**spec.parameters, "additionalProperties": False})
            result: ToolResult = self.registry.execute(name, arguments)
            self.guard()  # Revocation while a connector request is in flight discards its result.
            return result
        except (PermissionError, KeyError, ValueError, jsonschema.ValidationError) as exc:
            return ToolResult(name, arguments, False, {"code": "scope_denied", "error": str(exc)[:500]}, 0)

    @classmethod
    def connected(cls, client: Any, allowed: list[str], guard: Callable[[], Any]) -> ScopedRegistry:
        return cls(ToolRegistry(client), allowed, guard)


class FixtureRegistry:
    """Recorded synthetic inputs, never a live connector."""

    def __init__(self, case: str):
        self.case = case

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name,
                "Deterministic evaluation fixture: " + name,
                {"type": "object", "properties": {}, "additionalProperties": False},
            )
            for name in READ_TOOLS
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        data = {
            "fixture": True,
            "case": self.case,
            "asset": "bench-a",
            "signals": [
                {
                    "channel_id": "temperature",
                    "value": 25.0,
                    "unit": "bar" if self.case == "wrong_unit" else "degC",
                    "expected_unit": "degC",
                    "stale": self.case == "stale_data",
                    "calibration": "fixture-only",
                }
            ],
            "observation_only": True,
        }
        return ToolResult(name, arguments, True, data, 0)
