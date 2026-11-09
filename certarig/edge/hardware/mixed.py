"""Non-blocking cached acquisition and pure conversion helpers for reviewed Pi sources."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from ..models import ChannelConfig, Sample


class SourceSampler:
    """One bounded queue (the latest value), no work on the kernel sampling thread.

    A device read may be stuck in an OS driver. Its daemon cannot block control or
    shutdown; the last observation ages out. Hardware cutoff remains independent.
    """

    def __init__(
        self, channel: ChannelConfig, read: Callable[[], tuple[float, float | None]], interval: float = 0.1
    ) -> None:
        self.channel = channel
        self.read = read
        self.interval = interval
        self._latest: Sample | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"sensor-{channel.channel_id}")

    def start(self) -> None:
        self._thread.start()

    def acquire(self) -> None:
        quality = "good"
        try:
            value, raw = self.read()
            if not math.isfinite(value) or (raw is not None and not math.isfinite(raw)):
                raise ValueError("non-finite observation")
            if not self.channel.valid_min <= value <= self.channel.valid_max:
                quality = "out_of_range"
        except Exception:
            value, raw, quality = 0.0, None, "read_error"
        self._latest = Sample(
            self.channel.channel_id, value, self.channel.unit, raw, quality, datetime.now(UTC).isoformat()
        )

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.acquire()
            self._stop.wait(self.interval)

    def sample(self) -> Sample:
        sample = self._latest
        if sample is None:
            return Sample(
                self.channel.channel_id,
                0.0,
                self.channel.unit,
                None,
                "missing",
                datetime.now(UTC).isoformat(),
            )
        return sample

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.1)


class PulseCounter:
    def __init__(
        self, pulses_per_litre: float, window_s: float = 1.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        if (
            not math.isfinite(pulses_per_litre)
            or pulses_per_litre <= 0
            or not math.isfinite(window_s)
            or window_s <= 0
        ):
            raise ValueError("pulse calibration and window must be positive")
        self.pulses_per_litre, self.window_s, self.clock = pulses_per_litre, window_s, clock
        self._pulses: deque[float] = deque()
        self._lock = threading.Lock()

    def pulse(self) -> None:
        with self._lock:
            self._prune()
            self._pulses.append(self.clock())

    def _prune(self) -> None:
        while self._pulses and self._pulses[0] <= self.clock() - self.window_s:
            self._pulses.popleft()

    def read(self) -> tuple[float, float]:
        with self._lock:
            self._prune()
            count = len(self._pulses)
            return count * 60 / self.window_s / self.pulses_per_litre, float(count)


def w1_temperature(path: Path) -> tuple[float, float]:
    text = path.read_text()
    lines = text.splitlines()
    if len(lines) < 2 or not lines[0].endswith("YES") or "t=" not in lines[1]:
        raise ValueError("1-Wire CRC or temperature missing")
    raw = float(lines[1].split("t=", 1)[1])
    return raw / 1000, raw


def shunt_current(data: list[int], shunt_ohms: float) -> tuple[float, float]:
    if not math.isfinite(shunt_ohms) or shunt_ohms <= 0:
        raise ValueError("Measured shunt resistance required")
    raw = int.from_bytes(bytes(data), "big", signed=True)
    return raw * 0.00001 / shunt_ohms, float(raw)
