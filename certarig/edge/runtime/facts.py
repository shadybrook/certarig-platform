"""Normalise a live runtime state document into flat, typed facts for predicates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import RigConfig


@dataclass(frozen=True)
class Facts:
    signals: dict[str, float | None] = field(default_factory=dict)
    signal_states: dict[str, str] = field(default_factory=dict)
    qualities: dict[str, str] = field(default_factory=dict)
    states: dict[str, bool | str] = field(default_factory=dict)
    captured_at: str = ""
    sample_index: int = -1

    def signal(self, name: str) -> float | None:
        return self.signals.get(name)


def concept_index(config: RigConfig) -> dict[str, str]:
    """Map concept -> channel_id (first required channel wins) and channel_id -> itself."""
    index: dict[str, str] = {}
    for channel in config.channels:
        index[channel.channel_id] = channel.channel_id
        if channel.concept not in index and channel.required:
            index[channel.concept] = channel.channel_id
    for channel in config.channels:
        index.setdefault(channel.concept, channel.channel_id)
    return index


def build_facts(config: RigConfig, state: dict[str, Any]) -> Facts:
    index = concept_index(config)
    samples = {row["channel_id"]: row for row in state.get("samples", [])}
    guardrail = state.get("guardrail", {})
    channel_status = {row["channel_id"]: row for row in guardrail.get("channels", [])}
    signals: dict[str, float | None] = {}
    signal_states: dict[str, str] = {}
    qualities: dict[str, str] = {}
    for name, channel_id in index.items():
        sample = samples.get(channel_id)
        status = channel_status.get(channel_id)
        value = None
        if status is not None and status.get("value") is not None:
            value = float(status["value"])
        elif sample is not None and sample.get("value") is not None:
            value = float(sample["value"])
        signals[name] = value
        signal_states[name] = str(status["state"]) if status else "missing"
        qualities[name] = str(sample["quality"]) if sample else "missing"
    outputs = state.get("outputs", {})
    recording = state.get("recording", {})
    states: dict[str, bool | str] = {
        "estop_active": bool(guardrail.get("estop_active", True)),
        "trip_latched": bool(guardrail.get("trip_latched", True)),
        "permit_requested": bool(guardrail.get("permit_requested", False)),
        "drive_high": bool(guardrail.get("drive_high", False)),
        "process_healthy": bool(guardrail.get("process_healthy", False)),
        "output_high": bool(outputs.get("gpio23_command_high", False)),
        "relay_energized_expected": bool(outputs.get("relay_energized_expected", False)),
        "recording_active": bool(recording.get("active", False)),
        "reason": str(guardrail.get("reason", "")),
        "last_event": str(state.get("last_event", "")),
        "status": str(state.get("status", "")),
    }
    return Facts(
        signals=signals,
        signal_states=signal_states,
        qualities=qualities,
        states=states,
        captured_at=str(state.get("captured_at", "")),
        sample_index=int(state.get("sample_index", -1)),
    )
