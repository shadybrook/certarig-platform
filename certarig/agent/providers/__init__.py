"""LLM provider adapters. Select with :func:`make_provider`."""

from __future__ import annotations

from .base import LLMProvider, Message, ProviderError, ProviderResponse, ToolCall, ToolSpec
from .fake import FakeProvider, ReplayProvider


def make_provider(name: str, model: str | None = None, **kwargs: object) -> LLMProvider:
    lowered = name.lower()
    if lowered == "fake":
        return FakeProvider()
    if lowered == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model)
    if lowered == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=model)
    if lowered == "replay":
        path = kwargs.get("path")
        if not path:
            raise ProviderError("replay provider needs path=")
        return ReplayProvider(str(path))
    raise ProviderError(f"unknown provider {name!r}; choose fake, anthropic, openai or replay")


__all__ = [
    "FakeProvider",
    "LLMProvider",
    "Message",
    "ProviderError",
    "ProviderResponse",
    "ReplayProvider",
    "ToolCall",
    "ToolSpec",
    "make_provider",
]
