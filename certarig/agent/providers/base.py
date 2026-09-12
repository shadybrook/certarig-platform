"""Provider-neutral message and tool model for the CertaRig agent.

Every provider adapter converts to and from these dataclasses. The orchestrator, the
transcript log and the tests never see a provider-specific object.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: str  # user | assistant | tool
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tool_calls"] = [asdict(call) for call in self.tool_calls]
        return value

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Message:
        return cls(
            role=str(raw["role"]),
            content=str(raw.get("content", "")),
            tool_calls=tuple(
                ToolCall(str(c["id"]), str(c["name"]), dict(c.get("arguments", {})))
                for c in raw.get("tool_calls", [])
            ),
            tool_call_id=raw.get("tool_call_id"),
            name=raw.get("name"),
        )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResponse:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "tool_calls": [asdict(call) for call in self.tool_calls],
            "stop_reason": self.stop_reason,
            "usage": self.usage,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProviderResponse:
        return cls(
            text=raw.get("text"),
            tool_calls=[
                ToolCall(str(c["id"]), str(c["name"]), dict(c.get("arguments", {})))
                for c in raw.get("tool_calls", [])
            ],
            stop_reason=str(raw.get("stop_reason", "end_turn")),
            usage=dict(raw.get("usage", {})),
            model=str(raw.get("model", "")),
        )


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse: ...


class ProviderError(RuntimeError):
    pass


def context_fingerprint(system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> str:
    """Stable hash of what the model was shown; used by the replay provider."""
    import hashlib

    payload = {
        "system": system,
        "messages": [message.to_dict() for message in messages],
        "tools": [tool.name for tool in tools],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
