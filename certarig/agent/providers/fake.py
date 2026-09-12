"""Deterministic providers for tests, demos and replay.

* :class:`FakeProvider` plays a script of responses, or delegates to a rule-based policy
  function when no script is given. It never needs a network or an API key.
* :class:`ReplayProvider` replays the model responses recorded in a session transcript and
  fails loudly if the context the model would see has diverged from the recording.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from .base import Message, ProviderError, ProviderResponse, ToolCall, ToolSpec, context_fingerprint

Policy = Callable[[str, Sequence[Message], Sequence[ToolSpec]], ProviderResponse]


def tool_call(name: str, arguments: dict[str, Any] | None = None, call_id: str | None = None) -> ToolCall:
    return ToolCall(call_id or f"call_{name}_{next(_COUNTER)}", name, dict(arguments or {}))


_COUNTER = itertools.count(1)


def say(text: str) -> ProviderResponse:
    return ProviderResponse(text=text, stop_reason="end_turn", model="fake")


def call(*calls: ToolCall, text: str | None = None) -> ProviderResponse:
    return ProviderResponse(text=text, tool_calls=list(calls), stop_reason="tool_use", model="fake")


class FakeProvider:
    name = "fake"

    def __init__(
        self, script: Iterable[ProviderResponse] | None = None, policy: Policy | None = None
    ) -> None:
        self.model = "fake-scripted" if script is not None else "fake-policy"
        self._script = list(script) if script is not None else None
        self._policy = policy
        self.calls: list[dict[str, Any]] = []

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        self.calls.append(
            {"system": system, "messages": [m.to_dict() for m in messages], "tools": [t.name for t in tools]}
        )
        if self._script is not None:
            if not self._script:
                raise ProviderError("fake provider script exhausted")
            response = self._script.pop(0)
            return response
        if self._policy is None:
            return say("I have nothing to do.")
        return self._policy(system, messages, tools)


class ReplayProvider:
    name = "replay"

    def __init__(self, path: str | Path, strict: bool = True) -> None:
        self.path = Path(path)
        self.strict = strict
        self.model = "replay"
        rows = [
            json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        self._records = [row for row in rows if row.get("kind") == "model_response"]
        self._index = 0

    @property
    def remaining(self) -> int:
        return len(self._records) - self._index

    def complete(
        self, system: str, messages: Sequence[Message], tools: Sequence[ToolSpec]
    ) -> ProviderResponse:
        if self._index >= len(self._records):
            raise ProviderError("replay exhausted: the live run made more model calls than the recording")
        record = self._records[self._index]
        self._index += 1
        fingerprint = context_fingerprint(system, messages, tools)
        if self.strict and record["fingerprint"] != fingerprint:
            raise ProviderError(
                f"replay divergence at call {self._index}: the context shown to the model differs from the recording"
            )
        return ProviderResponse.from_dict(record["response"])
