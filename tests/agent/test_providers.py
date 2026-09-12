from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from certarig.agent.providers import make_provider
from certarig.agent.providers.anthropic_provider import (
    parse_anthropic_response,
    to_anthropic_messages,
    to_anthropic_tools,
)
from certarig.agent.providers.base import (
    Message,
    ProviderError,
    ProviderResponse,
    ToolCall,
    ToolSpec,
    context_fingerprint,
)
from certarig.agent.providers.openai_provider import (
    parse_openai_response,
    to_openai_messages,
    to_openai_tools,
)

TOOLS = [ToolSpec("read_state", "Read state", {"type": "object", "properties": {}})]
CONVERSATION = [
    Message(role="user", content="status?"),
    Message(
        role="assistant",
        content="",
        tool_calls=(ToolCall("c1", "read_state", {}), ToolCall("c2", "read_rig", {"x": 1})),
    ),
    Message(role="tool", content='{"ok": true}', tool_call_id="c1", name="read_state"),
    Message(role="tool", content='{"rig": 1}', tool_call_id="c2", name="read_rig"),
    Message(role="assistant", content="All good."),
]


def test_message_roundtrip_and_fingerprint_is_stable() -> None:
    for message in CONVERSATION:
        assert Message.from_dict(message.to_dict()) == message
    a = context_fingerprint("sys", CONVERSATION, TOOLS)
    b = context_fingerprint("sys", [Message.from_dict(m.to_dict()) for m in CONVERSATION], TOOLS)
    assert a == b
    assert context_fingerprint("sys2", CONVERSATION, TOOLS) != a
    assert context_fingerprint("sys", CONVERSATION, []) != a
    response = ProviderResponse(text="hi", tool_calls=[ToolCall("1", "t", {"a": 1})], stop_reason="tool_use")
    assert ProviderResponse.from_dict(response.to_dict()).tool_calls[0].arguments == {"a": 1}


def test_anthropic_conversion_merges_tool_results_into_one_user_message() -> None:
    converted = to_anthropic_messages(CONVERSATION)
    assert [m["role"] for m in converted] == ["user", "assistant", "user", "assistant"]
    tool_results = converted[2]["content"]
    assert [b["type"] for b in tool_results] == ["tool_result", "tool_result"]
    assert tool_results[1]["tool_use_id"] == "c2"
    assert converted[1]["content"][0] == {"type": "tool_use", "id": "c1", "name": "read_state", "input": {}}
    tools = to_anthropic_tools(TOOLS)
    assert tools[0]["input_schema"] == TOOLS[0].parameters
    with pytest.raises(ProviderError):
        to_anthropic_messages([Message(role="system", content="x")])


def test_anthropic_response_parsing_with_sdk_like_objects_and_dicts() -> None:
    sdk_like = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Let me check."),
            SimpleNamespace(type="tool_use", id="toolu_1", name="read_state", input={"a": 1}),
        ],
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        model="claude-x",
    )
    parsed = parse_anthropic_response(sdk_like)
    assert parsed.text == "Let me check."
    assert parsed.tool_calls == [ToolCall("toolu_1", "read_state", {"a": 1})]
    assert parsed.usage == {"input_tokens": 10, "output_tokens": 5}
    assert parsed.stop_reason == "tool_use"
    dict_like = SimpleNamespace(
        content=[{"type": "tool_use", "id": "t2", "name": "force_safe", "input": "{}"}]
    )
    parsed = parse_anthropic_response(dict_like)
    assert parsed.text is None and parsed.tool_calls[0].name == "force_safe"


def test_openai_conversion_and_parsing() -> None:
    converted = to_openai_messages("SYSTEM", CONVERSATION)
    assert converted[0] == {"role": "system", "content": "SYSTEM"}
    assert converted[2]["tool_calls"][1]["function"] == {
        "name": "read_rig",
        "arguments": json.dumps({"x": 1}),
    }
    assert converted[3] == {"role": "tool", "tool_call_id": "c1", "content": '{"ok": true}'}
    assert to_openai_tools(TOOLS)[0]["function"]["parameters"] == TOOLS[0].parameters

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1", function=SimpleNamespace(name="read_state", arguments='{"a": 2}')
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
        model="gpt-x",
    )
    parsed = parse_openai_response(response)
    assert parsed.tool_calls == [ToolCall("call_1", "read_state", {"a": 2})]
    assert parsed.usage == {"input_tokens": 3, "output_tokens": 4}
    text_only = {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]}
    assert parse_openai_response(text_only).text == "done"
    with pytest.raises(ProviderError):
        parse_openai_response({"choices": []})
    bad_json = {
        "choices": [{"message": {"tool_calls": [{"id": "1", "function": {"name": "x", "arguments": "{"}}]}}]
    }
    with pytest.raises(ProviderError):
        parse_openai_response(bad_json)


def test_make_provider_requires_keys_and_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    assert make_provider("fake").name == "fake"
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        make_provider("anthropic")
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        make_provider("openai")
    with pytest.raises(ProviderError):
        make_provider("mystery")
    with pytest.raises(ProviderError):
        make_provider("replay")
