"""MQTT observe adapter. Tests use an in-process TagBus; no broker required."""

from __future__ import annotations

import json
import math
import os
import threading
from datetime import UTC, datetime
from typing import Any

from ..models import RigConfig, RigSnapshot, Sample
from .base import HardwareAdapter, HardwareError
from .bus import TagBus


class MqttHardware(HardwareAdapter):
    def __init__(self, config: RigConfig, bus: TagBus | None = None) -> None:
        self.config = config
        self.bus = bus or TagBus()
        self.observe_only = bool(config.hardware.observe_only)
        self.output = False
        self.closed = False
        self.estop = False
        self.network = (config.hardware.mqtt or {}).get("broker", "in-process") != "in-process"
        self.connected = False
        self._lock = threading.RLock()
        self._observations: dict[str, tuple[float, str, str]] = {}
        self._client: Any = None
        if self.network:
            if not self.observe_only:
                raise HardwareError("MQTT network adapters are observe_only")
            try:
                import paho.mqtt.client as mqtt
            except ImportError as exc:
                raise HardwareError("install certarig[mqtt] for a network broker") from exc
            settings = config.hardware.mqtt or {}
            topics = [_address(c) for c in config.channels]
            if len(set(topics)) != len(topics) or any(not t or "+" in t or "#" in t for t in topics):
                raise HardwareError("Map unique exact MQTT topics, not wildcards")
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if settings.get("username_env"):
                self._client.username_pw_set(os.environ[str(settings["username_env"])], os.environ.get(str(settings.get("password_env", ""))))
            if settings.get("tls"):
                self._client.tls_set()
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            self._client.connect_async(str(settings["broker"]), int(settings.get("port", 1883)), keepalive=10)
            self._client.loop_start()
            return
        for channel in config.channels:
            rest = channel.safe_min + (channel.safe_max - channel.safe_min) * 0.4
            self.bus.set(_address(channel), rest)

    def snapshot(self) -> RigSnapshot:
        captured = datetime.now(UTC).isoformat()
        samples = []
        for channel in self.config.channels:
            if self.network:
                with self._lock:
                    value, timestamp, quality = self._observations.get(_address(channel), (0.0, captured, "missing"))
                    if not self.connected:
                        quality = "disconnected"
                    age = (datetime.now(UTC) - datetime.fromisoformat(timestamp)).total_seconds()
                    if quality == "good" and not 0 <= age <= float((self.config.hardware.mqtt or {}).get("max_age_s", 1)):
                        quality = "stale"
                samples.append(Sample(channel.channel_id, value, channel.unit, None, quality, timestamp))
                continue
            value = self.bus.get(_address(channel))
            quality = "good" if channel.valid_min <= value <= channel.valid_max else "out_of_range"
            samples.append(
                Sample(channel.channel_id, value, channel.unit, None, quality, captured)
            )
        return RigSnapshot(
            self.config.rig_id,
            self.config.config_hash,
            self.estop,
            not self.output,
            tuple(samples),
            datetime.now(UTC).isoformat(),
        )

    def set_valve(self, open_state: bool) -> None:
        if open_state and (self.observe_only or self.network):
            raise HardwareError("observe_only")
        self.output = bool(open_state)
        if not self.network:
            self.bus.publish("command/valve", self.output)

    def force_safe_state(self) -> None:
        self.output = False
        if not self.network:
            self.bus.publish("command/valve", False)

    def output_is_safe(self) -> bool:
        return not self.output

    def close(self) -> None:
        self.force_safe_state()
        self.closed = True
        if self._client is not None:
            self._client.disconnect()
            self._client.loop_stop()

    def status(self) -> dict[str, Any]:
        return {"transport": "mqtt_broker" if self.network else "in_process_fixture", "connected": self.connected if self.network else True, "observe_only": self.observe_only, "remote_output_state": "unknown"}

    def _on_connect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        with self._lock:
            self.connected = reason_code == 0
            self._observations.clear()
        if self.connected:
            for channel in self.config.channels:
                client.subscribe(_address(channel), qos=1)

    def _on_disconnect(self, client: Any, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        with self._lock:
            self.connected = False
            self._observations.clear()

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        channel = next((c for c in self.config.channels if _address(c) == message.topic), None)
        if channel is None:
            return
        timestamp = datetime.now(UTC).isoformat()
        value, quality = 0.0, "malformed"
        try:
            raw = json.loads(message.payload)
            if not isinstance(raw, dict) or isinstance(raw["value"], bool) or not isinstance(raw["value"], (float, int)):
                raise ValueError("numeric JSON value required")
            value = float(raw["value"])
            source_time = datetime.fromisoformat(raw["captured_at"])
            if not math.isfinite(value) or source_time.tzinfo is None or raw["unit"] != channel.unit:
                raise ValueError("invalid source value, unit or timestamp")
            timestamp = source_time.isoformat()
            quality = "retained" if message.retain else "good" if channel.valid_min <= value <= channel.valid_max else "out_of_range"
            if raw.get("quality", "good") != "good":
                quality = "bad_source_quality"
        except (ValueError, TypeError, KeyError, UnicodeError):
            value = 0.0
        with self._lock:
            self._observations[message.topic] = (value, timestamp, quality)


def _address(channel: Any) -> str:
    source = getattr(channel, "source", None) or {}
    return str(source.get("topic") or source.get("address") or channel.channel_id)
