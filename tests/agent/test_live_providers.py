"""Opt-in live provider smoke. CI stays Fake. Skips without keys."""

from __future__ import annotations

import os

import pytest

from certarig.agent.providers import make_provider
from certarig.agent.providers.base import Message

pytestmark = pytest.mark.live_llm


def test_anthropic_or_openai_returns_text() -> None:
    key_a = os.environ.get("ANTHROPIC_API_KEY")
    key_o = os.environ.get("OPENAI_API_KEY")
    if not key_a and not key_o:
        pytest.skip("no live LLM key in this environment")
    name = "anthropic" if key_a else "openai"
    provider = make_provider(name)
    response = provider.complete(
        system="Reply with the single word ok.",
        messages=[Message(role="user", content="Say ok.")],
        tools=[],
    )
    assert response.text
    assert "ok" in response.text.lower()
