"""Plant values published onto an in-process MQTT/Modbus tag bus."""

from __future__ import annotations

from typing import Any

from certarig.edge.hardware.base import HardwareAdapter, HardwareError
from certarig.edge.models import RigSnapshot

from .plant import SimulatedRig


class PlantOnBus(HardwareAdapter):
    """Drive :class:`SimulatedRig` physics, then expose the values through another adapter."""

    def __init__(self, plant: SimulatedRig, adapter: HardwareAdapter) -> None:
        self.plant = plant
        self.adapter = adapter
        self.drop: set[str] = set()

    def _address(self, channel_id: str) -> str:
        channel = self.plant.config.channel(channel_id)
        source = getattr(channel, "source", None) or {}
        if source.get("topic"):
            return str(source["topic"])
        if source.get("register") is not None:
            return f"hr/{source['register']}"
        return str(source.get("address") or channel_id)

    def snapshot(self) -> RigSnapshot:
        snap = self.plant.snapshot()
        bus = getattr(self.adapter, "bus", None)
        if bus is not None:
            for sample in snap.samples:
                if sample.channel_id in self.drop:
                    continue
                bus.set(self._address(sample.channel_id), float(sample.value))
            self.adapter.estop = snap.emergency_stop_active  # type: ignore[attr-defined]
        return self.adapter.snapshot()

    def set_valve(self, open_state: bool) -> None:
        try:
            self.adapter.set_valve(open_state)
        except HardwareError:
            if open_state:
                raise
        self.plant.set_valve(False if getattr(self.adapter, "observe_only", False) else open_state)

    def force_safe_state(self) -> None:
        self.adapter.force_safe_state()
        self.plant.force_safe_state()

    def output_is_safe(self) -> bool:
        return self.adapter.output_is_safe() and self.plant.output_is_safe()

    def close(self) -> None:
        self.force_safe_state()
        self.adapter.close()
        self.plant.close()

    def set_target(self, name: str, value: float) -> None:
        self.plant.set_target(name, value)

    def ramp(self, name: str, target: float, over_s: float) -> None:
        self.plant.ramp(name, target, over_s)

    def press_estop(self, pressed: bool = True) -> None:
        self.plant.press_estop(pressed)

    def inject(self, kind: str, channel: str | None = None, **params: Any) -> None:
        if kind == "dropout" and channel:
            resolved = self.plant._resolve(channel).config.channel_id
            self.drop.add(resolved)
        self.plant.inject(kind, channel, **params)

    def clear(self, kind: str | None = None, channel: str | None = None) -> None:
        if channel:
            resolved = self.plant._resolve(channel).config.channel_id
            self.drop.discard(resolved)
        elif kind == "dropout" or kind is None:
            self.drop.clear()
        self.plant.clear(kind, channel)

    @property
    def sim_time(self) -> float:
        return self.plant.sim_time

    @property
    def log(self) -> list[dict[str, Any]]:
        return self.plant.log

    @property
    def output(self) -> bool:
        return bool(getattr(self.adapter, "output", False) or self.plant.output)

    @output.setter
    def output(self, value: bool) -> None:
        self.adapter.output = bool(value)  # type: ignore[attr-defined]
        self.plant.output = bool(value)
