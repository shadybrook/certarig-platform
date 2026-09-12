"""In-process tag bus used by the MQTT and Modbus adapters in tests and sim twins."""

from __future__ import annotations

import threading
from typing import Any


class TagBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[str, float] = {}
        self._commands: list[tuple[str, Any]] = []

    def set(self, address: str, value: float) -> None:
        with self._lock:
            self._values[address] = float(value)

    def get(self, address: str, default: float = 0.0) -> float:
        with self._lock:
            return float(self._values.get(address, default))

    def publish(self, address: str, value: Any) -> None:
        with self._lock:
            self._commands.append((address, value))

    def commands(self) -> list[tuple[str, Any]]:
        with self._lock:
            return list(self._commands)
