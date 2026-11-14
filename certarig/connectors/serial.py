"""Receive-only bounded JSON-line observation. Never transmits application bytes."""

from __future__ import annotations

import json
import re
import threading
from typing import Any

from .observation import checked_sample


class SerialSource:
    def __init__(self, settings: dict[str, Any], channels: dict[str, str], factory: Any = None):
        port, baud = settings.get("port", ""), settings.get("baudrate", 115200)
        if (
            not isinstance(port, str)
            or not re.fullmatch(r"(?:/dev/[A-Za-z0-9_./-]+|COM[0-9]+)", port)
            or "/../" in port
            or baud not in {9600, 19200, 38400, 57600, 115200}
        ):
            raise ValueError("Configure an exact local serial device and supported baud rate")
        timeout = float(settings.get("timeout_s", 0.1))
        if not 0 < timeout <= 0.25 or not 0 < float(settings.get("max_age_s", 1)) <= 60:
            raise ValueError("Serial timeout/freshness outside bounded limits")
        if factory is None:
            import serial

            factory = serial.Serial
        self.settings, self.channels = settings, channels
        self.lock = threading.RLock()
        self.samples: dict[str, dict[str, Any]] = {}
        self.error: str | None = None
        self.connected = False
        self.stop = threading.Event()
        # Configure inactive control lines before opening. Some drivers can still pulse
        # lines on open; this is reported and requires a separate physical wiring review.
        self.port = factory(
            port=None,
            baudrate=baud,
            timeout=timeout,
            write_timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            exclusive=True,
        )
        self.port.dtr = False
        self.port.rts = False
        self.port.port = port
        self.port.open()
        self.connected = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def ingest(self, line: bytes) -> None:
        try:
            if len(line) > 4096 or not line.endswith(b"\n"):
                raise ValueError("Oversized or incomplete serial frame")
            raw = json.loads(line)
            if not isinstance(raw, dict) or raw.get("channel_id") not in self.channels:
                raise ValueError("Unmapped serial channel")
            sample = checked_sample(
                raw,
                expected_unit=self.channels[raw["channel_id"]],
                max_age_s=float(self.settings.get("max_age_s", 1)),
            )
            with self.lock:
                self.samples[sample["channel_id"]] = sample
                self.error = None
        except (ValueError, KeyError, TypeError, UnicodeError):
            with self.lock:
                self.samples.clear()
                self.error = "malformed"

    def _loop(self) -> None:
        pending = bytearray()
        dropping = False
        while not self.stop.is_set():
            try:
                data = self.port.read(512)
                for byte in data:
                    if byte == 10:
                        if not dropping:
                            self.ingest(bytes(pending) + b"\n")
                        pending.clear()
                        dropping = False
                    elif not dropping:
                        pending.append(byte)
                        if len(pending) >= 4096:
                            pending.clear()
                            dropping = True
                            with self.lock:
                                self.samples.clear()
                                self.error = "malformed"
            except (OSError, ValueError):
                with self.lock:
                    self.connected = False
                    self.samples.clear()
                return

    def read(self) -> list[dict[str, Any]]:
        with self.lock:
            return [
                checked_sample(
                    v, expected_unit=self.channels[k], max_age_s=float(self.settings.get("max_age_s", 1))
                )
                for k, v in self.samples.items()
            ]

    def status(self) -> dict[str, Any]:
        return {
            "transport": "serial_jsonl",
            "connected": self.connected,
            "quality": self.error or "good",
            "observe_only": True,
            "remote_output_state": "unknown",
            "control_line_state": "requested_inactive_not_physically_verified",
            "application_bytes_sent": 0,
        }

    def close(self) -> None:
        self.stop.set()
        self.port.close()
        self.thread.join(timeout=1)
        self.connected = False
