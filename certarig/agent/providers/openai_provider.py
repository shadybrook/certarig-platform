"""OpenAI Chat Completions adapter (function tools). The SDK is imported lazily.

Any OpenAI-compatible endpoint works by setting ``OPENAI_BASE_URL`` (Ollama, vLLM, Azure...).
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

from .base import Message, ProviderError, ProviderResponse, ToolCall, ToolSpec

DEFAULT_MODEL = "gpt-4.1-mini"


def to_openai_messages(system: str, messages: Sequence[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for message in messages:
        if message.role == "user":
            out.append({"role": "user", "content": message.content})
        elif message.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": message.content or None}
            if message.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                    }
                    for call in message.tool_calls
                ]
            out.append(entry)
        elif message.role == "tool":
            out.append({"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content})
        else:
            raise ProviderError(f"unsupported role {message.role}")
    return out


def to_openai_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
        }
        for tool in tools
    ]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def parse_openai_response(response: Any) -> ProviderResponse:
    choices = _get(response, "choices") or []
    if not choices:
        raise ProviderError("openai response had no choices")
    choice = choices[0]
    message = _get(choice, "message")
    calls: list[ToolCall] = []
    for raw in _get(message, "tool_calls") or []:
        function = _get(raw, "function")
        arguments = _get(function, "arguments") or "{}"
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"tool call arguments were not valid JSON: {exc}") from exc
        calls.append(ToolCall(str(_get(raw, "id")), str(_get(function, "name")), parsed))
    usage = _get(response, "usage")
    usage_dict = {}
    if usage is not None:
        usage_dict = {
            "input_tokens": int(_get(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(_get(usage, "completion_tokens", 0) or 0),
        }
    content = _get(message, "content")
    return ProviderResponse(
        text=str(content) if content else None,
        tool_calls=calls,
        stop_reason=str(_get(choice, "finish_reason", "stop") or "stop"),
        usage=usage_dict,
        model=str(_get(response, "model", "") or ""),
    )


class OpenAIProvider:
    name = "openai"

    def __init__(
        self, model: str | None = None, api_key: str | None = None, base_url: str | None = None
    ) -> None:
        self.model = model or os.environ.get("CERTARIG_OPENAI_MODEL", DEFAULT_MODEL)
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OPENAI_API_KEY is not set")
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError("install certarig[openai] to use the OpenAI provider") from exc
        self._client = openai.OpenAI(api_key=key, base_url=base_url or os.environ.get("OPENAI_BASE_URL"))

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        kwargs: dict[str, Any] = {"model": self.model, "messages": to_openai_messages(system, messages)}
        if tools:
            kwargs["tools"] = to_openai_tools(tools)
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # pragma: no cover - network
            raise ProviderError(f"openai request failed: {exc}") from exc
        return parse_openai_response(response)
