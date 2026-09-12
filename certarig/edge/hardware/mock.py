from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from ..models import RigConfig, RigSnapshot, Sample
from .base import HardwareAdapter


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class MockHardware(HardwareAdapter):
    """Deterministic hardware adapter used for tests and laptop demonstrations."""

    def __init__(
        self,
        config: RigConfig,
        pressure_profile: Callable[[int, bool], float] | None = None,
    ) -> None:
        self.config = config
        self.valve_open = False
        self.emergency_stop_active = False
        self.sample_index = 0
        self.closed = False
        self.pressure_profile = pressure_profile or self._default_pressure

    @staticmethod
    def _default_pressure(index: int, valve_open: bool) -> float:
        if not valve_open:
            return max(0.05, 0.15 - index * 0.01)
        return min(2.35, 0.25 + index * 0.28)

    def snapshot(self) -> RigSnapshot:
        captured = utc_now()
        pressure = self.pressure_profile(self.sample_index, self.valve_open)
        flow = 0.0 if not self.valve_open else min(8.0, pressure * 2.9)
        samples: list[Sample] = []
        for channel in self.config.channels:
            if channel.unit.lower() == "bar":
                value = pressure
            elif channel.unit.lower() in {"l/min", "lpm"}:
                value = flow
            else:
                value = 1.0 if self.valve_open else 0.0
            quality = "good" if channel.valid_min <= value <= channel.valid_max else "out_of_range"
            samples.append(
                Sample(
                    channel_id=channel.channel_id,
                    value=round(value, 4),
                    unit=channel.unit,
                    raw_value=None,
                    quality=quality,
                    captured_at=captured,
                )
            )
        self.sample_index += 1
        return RigSnapshot(
            rig_id=self.config.rig_id,
            config_hash=self.config.config_hash,
            emergency_stop_active=self.emergency_stop_active,
            output_safe=not self.valve_open,
            samples=tuple(samples),
            captured_at=captured,
        )

    def set_valve(self, open_state: bool) -> None:
        if self.closed:
            raise RuntimeError("hardware adapter is closed")
        if open_state and self.emergency_stop_active:
            raise RuntimeError("emergency stop is active")
        self.valve_open = bool(open_state)

    def force_safe_state(self) -> None:
        self.valve_open = False

    def output_is_safe(self) -> bool:
        return not self.valve_open

    def close(self) -> None:
        self.force_safe_state()
        self.closed = True
