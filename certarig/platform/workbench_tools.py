"""Manifest-driven authoring tools. Applying, reviewing and granting access are absent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from certarig.agent.providers.base import ToolSpec
from certarig.agent.tools import ToolResult

MANIFEST = Path(__file__).resolve().parents[1] / "schemas" / "workbench-tools.json"


class WorkbenchRegistry:
    def __init__(self, api: Any, actor: Any):
        self.api, self.actor = api, actor
        self.manifest = json.loads(MANIFEST.read_text())

    def specs(self) -> list[ToolSpec]:
        return [ToolSpec(r["name"], r["description"], r["parameters"]) for r in self.manifest["tools"]]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        try:
            self.api.platform.actor(self.actor)
            row = next((r for r in self.manifest["tools"] if r["name"] == name), None)
            if row is None:
                raise PermissionError("Unknown authoring tool; human authority operations are unavailable")
            jsonschema.validate(arguments, row["parameters"])
            path = [arguments.get(p[1:], p) if p.startswith(":") else p for p in row["path"]]
            body = {k: v for k, v in arguments.items() if ":" + k not in row["path"]}
            result = self.api.route(self.actor, row["method"], path, body)
            self.api.platform.actor(self.actor)
            return ToolResult(name, arguments, True, result, 0)
        except (ValueError, KeyError, PermissionError, jsonschema.ValidationError) as exc:
            return ToolResult(name, arguments, False, {"error": str(exc)[:500], "authority": "none"}, 0)
