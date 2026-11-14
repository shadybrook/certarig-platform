"""Bounded Modbus TCP register observation. Only read function codes 03 and 04."""

from __future__ import annotations

import math
import socket
import struct
import time
from datetime import UTC, datetime
from typing import Any

TYPES = {"uint16": (1, "H"), "int16": (1, "h"), "uint32": (2, "I"), "int32": (2, "i"), "float32": (2, "f")}


class ModbusSource:
    def __init__(
        self,
        settings: dict[str, Any],
        channels: list[dict[str, Any]],
        connect: Any = socket.create_connection,
    ):
        self.settings, self.channels, self.connect = settings, channels, connect
        self.timeout = float(settings.get("timeout_s", 0.25))
        self.host, self.port = settings.get("host"), settings.get("port", 502)
        if (
            not isinstance(self.host, str)
            or not self.host
            or "://" in self.host
            or not isinstance(self.port, int)
            or not 1 <= self.port <= 65535
            or not 0 < self.timeout <= 1
            or not 1 <= len(channels) <= 16
        ):
            raise ValueError("Exact operator-configured Modbus endpoint and bounded polling required")
        for channel in channels:
            source = channel.get("source", {})
            if (
                source.get("function", 3) not in {3, 4}
                or source.get("data_type", "uint16") not in TYPES
                or not isinstance(source.get("register"), int)
                or not 0 <= source["register"] <= 65534
                or not 1 <= source.get("device_id", 1) <= 247
                or source.get("byte_order", "big") not in {"big", "little"}
                or source.get("word_order", "big") not in {"big", "little"}
            ):
                raise ValueError("Invalid read-only register mapping")
            for key in ("gain", "offset"):
                number = source.get(key, 1 if key == "gain" else 0)
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or not math.isfinite(number)
                ):
                    raise ValueError("Finite Modbus scaling required")
        self.transaction, self.connected, self.closed = 0, False, False
        self.error: str | None = None

    @staticmethod
    def _recv(stream: Any, length: int, deadline: float) -> bytes:
        data = bytearray()
        while len(data) < length:
            stream.settimeout(max(0.001, deadline - time.monotonic()))
            chunk = stream.recv(length - len(data))
            if not chunk or time.monotonic() >= deadline:
                raise OSError("Incomplete or timed-out Modbus response")
            data.extend(chunk)
        return bytes(data)

    def read(self) -> list[dict[str, Any]]:
        if self.closed:
            return []
        values = []
        deadline = time.monotonic() + 2
        try:
            with self.connect((self.host, self.port), timeout=self.timeout) as stream:
                for channel in self.channels:
                    source = channel["source"]
                    function, unit = source.get("function", 3), source.get("device_id", 1)
                    count, code = TYPES[source.get("data_type", "uint16")]
                    self.transaction = (self.transaction + 1) % 65536
                    stream.settimeout(min(self.timeout, max(0.001, deadline - time.monotonic())))
                    stream.sendall(
                        struct.pack(
                            ">HHHBBHH", self.transaction, 0, 6, unit, function, source["register"], count
                        )
                    )
                    header = self._recv(stream, 7, min(deadline, time.monotonic() + self.timeout))
                    transaction, protocol, size, returned_unit = struct.unpack(">HHHB", header)
                    if (
                        transaction != self.transaction
                        or protocol != 0
                        or returned_unit != unit
                        or not 2 <= size <= 254
                    ):
                        raise ValueError("Mismatched Modbus response header")
                    payload = self._recv(stream, size - 1, min(deadline, time.monotonic() + self.timeout))
                    if len(payload) != 2 + count * 2 or payload[0] != function or payload[1] != count * 2:
                        raise ValueError("Invalid register reply or Modbus exception")
                    words = [payload[i : i + 2] for i in range(2, len(payload), 2)]
                    if source.get("word_order", "big") == "little":
                        words.reverse()
                    if source.get("byte_order", "big") == "little":
                        words = [w[::-1] for w in words]
                    raw = struct.unpack(">" + code, b"".join(words))[0]
                    value = raw * source.get("gain", 1) + source.get("offset", 0)
                    if not math.isfinite(value):
                        raise ValueError("Invalid Modbus measurement")
                    values.append(
                        {
                            "channel_id": channel["channel_id"],
                            "value": value,
                            "raw_value": raw,
                            "unit": channel["unit"],
                            "captured_at": datetime.now(UTC).isoformat(),
                            "quality": "good",
                            "timestamp_origin": "gateway_acquisition_not_device",
                        }
                    )
                self.connected, self.error = True, None
        except (OSError, ValueError, struct.error):
            self.connected, self.error = False, "disconnected_or_invalid_response"
            return []
        return values

    def status(self) -> dict[str, Any]:
        return {
            "transport": "modbus_tcp",
            "connected": self.connected,
            "error": self.error,
            "observe_only": True,
            "remote_output_state": "unknown",
            "timestamp_origin": "gateway_acquisition_not_device",
            "allowed_functions": [3, 4],
        }

    def close(self) -> None:
        self.closed, self.connected = True, False
