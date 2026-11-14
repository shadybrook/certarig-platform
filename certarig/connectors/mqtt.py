"""MQTT source facade over the existing broker-connected Edge adapter."""

from __future__ import annotations

from typing import Any


class MqttSource:
    def __init__(self, config: Any):
        from certarig.edge.hardware.mqtt import MqttHardware

        if not config.hardware.observe_only:
            raise ValueError("MQTT observation source requires observe_only")
        self.adapter = MqttHardware(config)

    def read(self) -> list[dict[str, Any]]:
        samples = self.adapter.snapshot().samples
        return [
            {
                "channel_id": s.channel_id,
                "value": s.value,
                "unit": s.unit,
                "captured_at": s.captured_at,
                "quality": s.quality
                if s.quality in {"good", "missing", "stale", "disconnected", "out_of_range"}
                else "invalid",
                "raw_value": s.raw_value,
                "timestamp_origin": "source",
            }
            for s in samples
        ]

    def status(self) -> dict[str, Any]:
        return self.adapter.status()

    def close(self) -> None:
        self.adapter.close()
