"""Modbus TCP observe adapter backed by an in-process register map."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import RigConfig, RigSnapshot, Sample, in_valid_range
from .base import HardwareAdapter, HardwareError
from .bus import TagBus


class ModbusHardware(HardwareAdapter):
    def __init__(self, config: RigConfig, bus: TagBus | None = None) -> None:
        self.config = config
        self.bus = bus or TagBus()
        self.observe_only = bool(config.hardware.observe_only)
        self.output = False
        self.closed = False
        self.estop = False
        for channel in config.channels:
            rest = channel.safe_min + (channel.safe_max - channel.safe_min) * 0.4
            self.bus.set(_address(channel), rest)

    def snapshot(self) -> RigSnapshot:
        captured = datetime.now(UTC).isoformat()
        samples = []
        for channel in self.config.channels:
            value = self.bus.get(_address(channel))
            quality = "good" if in_valid_range(channel, value) else "out_of_range"
            samples.append(
                Sample(channel.channel_id, value, channel.unit, None, quality, captured)
            )
        return RigSnapshot(
            self.config.rig_id,
            self.config.config_hash,
            self.estop,
            not self.output,
            tuple(samples),
            captured,
        )

    def set_valve(self, open_state: bool) -> None:
        if open_state and self.observe_only:
            raise HardwareError("observe_only")
        self.output = bool(open_state)
        self.bus.publish("coil/valve", int(self.output))

    def force_safe_state(self) -> None:
        self.output = False
        self.bus.publish("coil/valve", 0)

    def output_is_safe(self) -> bool:
        return not self.output

    def close(self) -> None:
        self.force_safe_state()
        self.closed = True


def _address(channel: Any) -> str:
    source = getattr(channel, "source", None) or {}
    if source.get("register") is not None:
        return f"hr/{source['register']}"
    return str(source.get("address") or channel.channel_id)
