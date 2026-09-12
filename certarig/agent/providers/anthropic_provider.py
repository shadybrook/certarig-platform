"""Anthropic Messages API adapter (tool use). The SDK is imported lazily."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

from .base import Message, ProviderError, ProviderResponse, ToolCall, ToolSpec

DEFAULT_MODEL = "claude-sonnet-4-5"


def to_anthropic_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """Convert neutral messages to Anthropic content blocks, merging consecutive tool results."""
    out: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "user":
            out.append({"role": "user", "content": [{"type": "text", "text": message.content}]})
        elif message.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                blocks.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
        elif message.role == "tool":
            block = {"type": "tool_result", "tool_use_id": message.tool_call_id, "content": message.content}
            if (
                out
                and out[-1]["role"] == "user"
                and out[-1]["content"]
                and out[-1]["content"][0].get("type") == "tool_result"
            ):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        else:
            raise ProviderError(f"unsupported role {message.role}")
    return out


def to_anthropic_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}
        for tool in tools
    ]


def parse_anthropic_response(response: Any) -> ProviderResponse:
    text_parts: list[str] = []
    calls: list[ToolCall] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if block_type == "text":
            text_parts.append(str(getattr(block, "text", None) or block.get("text", "")))
        elif block_type == "tool_use":
            block_id = getattr(block, "id", None) or block.get("id")
            name = getattr(block, "name", None) or block.get("name")
            arguments = getattr(block, "input", None) or block.get("input", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            calls.append(ToolCall(str(block_id), str(name), dict(arguments or {})))
    usage = getattr(response, "usage", None)
    usage_dict = {}
    if usage is not None:
        usage_dict = {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        }
    return ProviderResponse(
        text="\n".join(text_parts) if text_parts else None,
        tool_calls=calls,
        stop_reason=str(getattr(response, "stop_reason", "end_turn") or "end_turn"),
        usage=usage_dict,
        model=str(getattr(response, "model", "")),
    )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None, max_tokens: int = 2048) -> None:
        self.model = model or os.environ.get("CERTARIG_ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("install certarig[anthropic] to use the Anthropic provider") from exc
        self._client = anthropic.Anthropic(api_key=key)

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                messages=to_anthropic_messages(messages),
                tools=to_anthropic_tools(tools) if tools else [],
            )
        except Exception as exc:  # pragma: no cover - network
            raise ProviderError(f"anthropic request failed: {exc}") from exc
        return parse_anthropic_response(response)
