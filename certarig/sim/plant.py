"""A physics-lite rig simulator that implements the hardware adapter interface.

The simulator is the digital twin of the wave-1 bench and the test oracle for the whole
platform. It is deterministic under a seed with a fixed physics step, supports operator
inputs (pot moves as ramps), and can inject the faults that matter for interlock testing.

Fault kinds:

* ``dropout``   the channel disappears from the snapshot (missing sample)
* ``bad_quality`` the channel reports quality ``bad`` while keeping a value
* ``stuck``     the channel freezes at its current value
* ``drift``     the channel value drifts at ``rate`` units per simulated second
* ``saturate``  the channel reads above ``valid_max`` (ADC rail)
* ``estop_wire_break`` the E-stop reads active regardless of the button
* ``driver_failure`` ``set_valve(True)`` raises
* ``snapshot_failure`` ``snapshot()`` raises once per configured count
"""

from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from certarig.edge.hardware.base import HardwareAdapter, HardwareError
from certarig.edge.models import ChannelConfig, RigConfig, RigSnapshot, Sample


@dataclass
class _Ramp:
    start_value: float
    target: float
    start_t: float
    duration_s: float

    def value_at(self, t: float) -> float:
        if self.duration_s <= 0 or t >= self.start_t + self.duration_s:
            return self.target
        fraction = max(0.0, (t - self.start_t) / self.duration_s)
        return self.start_value + (self.target - self.start_value) * fraction


@dataclass
class _Channel:
    config: ChannelConfig
    target: float
    actual: float
    ramp: _Ramp | None = None
    faults: dict[str, dict[str, Any]] = field(default_factory=dict)
    drift_offset: float = 0.0


@dataclass
class SimSettings:
    seed: int = 1
    time_scale: float = 1.0
    fixed_dt_s: float | None = None
    lag_s: float = 0.15
    noise: dict[str, float] = field(default_factory=dict)
    epoch: datetime = field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC))

    @classmethod
    def from_config(cls, config: RigConfig, raw: dict[str, Any] | None = None) -> SimSettings:
        raw = raw or {}
        noise: dict[str, float] = {}
        if "noise_bar" in raw:
            noise["pressure"] = float(raw["noise_bar"])
        if "noise_l_min" in raw:
            noise["flow"] = float(raw["noise_l_min"])
        extra = raw.get("noise")
        if isinstance(extra, dict):
            for concept, value in extra.items():
                noise[str(concept)] = float(value)
        return cls(
            seed=int(raw.get("seed", 1)),
            time_scale=float(raw.get("time_scale", 1.0)),
            fixed_dt_s=config.sample_interval_ms / 1000.0,
            lag_s=float(raw.get("lag_s", 0.15)),
            noise=noise,
        )


class SimulatedRig(HardwareAdapter):
    """Deterministic simulated bench. Thread-safe; operator methods may be called from any thread."""

    def __init__(self, config: RigConfig, settings: SimSettings | None = None) -> None:
        self.config = config
        self.settings = settings or SimSettings.from_config(config, config.hardware.simulator)
        self._rng = random.Random(self.settings.seed)
        self._lock = threading.RLock()
        self._t = 0.0  # simulated seconds
        self._samples = 0
        self._channels: dict[str, _Channel] = {}
        for channel in config.channels:
            rest = channel.safe_min + (channel.safe_max - channel.safe_min) * 0.5
            self._channels[channel.channel_id] = _Channel(channel, target=rest, actual=rest)
        self._concepts = {channel.concept: channel.channel_id for channel in reversed(config.channels)}
        self.estop_pressed = False
        self.output = False
        self.closed = False
        self._global_faults: dict[str, dict[str, Any]] = {}
        self._snapshot_failures_remaining = 0
        self.log: list[dict[str, Any]] = []
        self.set_valve_calls = 0

    # ----------------------------------------------------------------- helpers
    def _resolve(self, name: str) -> _Channel:
        channel_id = self._concepts.get(name, name)
        try:
            return self._channels[channel_id]
        except KeyError as exc:
            raise KeyError(f"unknown channel or concept {name!r}") from exc

    def _record(self, what: str, **payload: Any) -> None:
        self.log.append({"t": round(self._t, 6), "what": what, **payload})

    @property
    def sim_time(self) -> float:
        with self._lock:
            return self._t

    def _now(self) -> str:
        return (self.settings.epoch + timedelta(seconds=self._t)).isoformat()

    # --------------------------------------------------------- operator inputs
    def set_target(self, name: str, value: float) -> None:
        with self._lock:
            channel = self._resolve(name)
            channel.ramp = None
            channel.target = float(value)
            self._record("set_target", channel=channel.config.channel_id, value=float(value))

    def ramp(self, name: str, to: float, over_s: float) -> None:
        with self._lock:
            channel = self._resolve(name)
            channel.ramp = _Ramp(channel.target, float(to), self._t, float(over_s))
            self._record("ramp", channel=channel.config.channel_id, to=float(to), over_s=float(over_s))

    def press_estop(self, pressed: bool = True) -> None:
        with self._lock:
            self.estop_pressed = bool(pressed)
            self._record("estop", pressed=bool(pressed))

    def release_estop(self) -> None:
        self.press_estop(False)

    def inject(self, kind: str, channel: str | None = None, **params: Any) -> None:
        with self._lock:
            if kind in {"estop_wire_break", "driver_failure"}:
                self._global_faults[kind] = params
            elif kind == "snapshot_failure":
                self._snapshot_failures_remaining = int(params.get("count", 1))
            elif channel is None:
                raise ValueError(f"fault {kind} needs a channel")
            else:
                target = self._resolve(channel)
                if kind == "stuck":
                    params = {**params, "value": target.actual}
                target.faults[kind] = params
            self._record("inject", kind=kind, channel=channel, params=params)

    def clear(self, kind: str | None = None, channel: str | None = None) -> None:
        with self._lock:
            if channel is not None:
                target = self._resolve(channel)
                if kind is None:
                    target.faults.clear()
                else:
                    target.faults.pop(kind, None)
            elif kind is None:
                self._global_faults.clear()
                for item in self._channels.values():
                    item.faults.clear()
                self._snapshot_failures_remaining = 0
            else:
                self._global_faults.pop(kind, None)
                for item in self._channels.values():
                    item.faults.pop(kind, None)
            self._record("clear", kind=kind, channel=channel)

    def faults(self) -> dict[str, Any]:
        with self._lock:
            return {
                "global": dict(self._global_faults),
                "channels": {cid: dict(ch.faults) for cid, ch in self._channels.items() if ch.faults},
            }

    # ---------------------------------------------------------------- physics
    def _advance(self, dt: float) -> None:
        self._t += dt
        alpha = 1.0 if self.settings.lag_s <= 0 else 1.0 - math.exp(-dt / self.settings.lag_s)
        for channel in self._channels.values():
            if channel.ramp is not None:
                channel.target = channel.ramp.value_at(self._t)
                if self._t >= channel.ramp.start_t + channel.ramp.duration_s:
                    channel.ramp = None
            if "stuck" in channel.faults:
                continue
            channel.actual += (channel.target - channel.actual) * alpha
            if "drift" in channel.faults:
                channel.drift_offset += float(channel.faults["drift"].get("rate", 0.01)) * dt

    def _measure(self, channel: _Channel) -> tuple[float, float | None, str]:
        cfg = channel.config
        if "stuck" in channel.faults:
            value = float(channel.faults["stuck"]["value"])
        else:
            value = channel.actual + channel.drift_offset
        sigma = self.settings.noise.get(cfg.concept, 0.0)
        if sigma:
            value += self._rng.gauss(0.0, sigma)
        if "saturate" in channel.faults:
            value = cfg.valid_max + float(channel.faults["saturate"].get("overshoot", 0.5))
        raw: float | None = None
        if cfg.raw_min_v is not None and cfg.raw_max_v is not None and cfg.engineering_max is not None:
            eng_min = cfg.engineering_min or 0.0
            span = (cfg.engineering_max - eng_min) or 1.0
            raw = cfg.raw_min_v + (value - eng_min) / span * (cfg.raw_max_v - cfg.raw_min_v)
            raw = round(raw, 5)
        quality = "good" if cfg.valid_min <= value <= cfg.valid_max else "bad"
        if "bad_quality" in channel.faults:
            quality = "bad"
        return round(value, 5), raw, quality

    # ------------------------------------------------------- adapter interface
    def snapshot(self) -> RigSnapshot:
        with self._lock:
            if self._snapshot_failures_remaining > 0:
                self._snapshot_failures_remaining -= 1
                raise HardwareError("simulated sensor bus failure")
            dt = self.settings.fixed_dt_s or self.config.sample_interval_ms / 1000.0
            self._advance(dt * self.settings.time_scale)
            self._samples += 1
            now = self._now()
            samples: list[Sample] = []
            for channel in self._channels.values():
                if "dropout" in channel.faults:
                    continue
                value, raw, quality = self._measure(channel)
                samples.append(
                    Sample(
                        channel_id=channel.config.channel_id,
                        value=value,
                        unit=channel.config.unit,
                        raw_value=raw,
                        quality=quality,
                        captured_at=now,
                    )
                )
            estop_active = self.estop_pressed or "estop_wire_break" in self._global_faults
            if estop_active and self.output:
                # NC2 removes relay power independently of software.
                self.output = False
                self._record("nc2_dropped_output")
            return RigSnapshot(
                rig_id=self.config.rig_id,
                config_hash=self.config.config_hash,
                emergency_stop_active=estop_active,
                output_safe=not self.output,
                samples=tuple(samples),
                captured_at=now,
            )

    def set_valve(self, open_state: bool) -> None:
        with self._lock:
            self.set_valve_calls += 1
            if open_state:
                if "driver_failure" in self._global_faults:
                    raise HardwareError("simulated relay driver failure")
                if self.estop_pressed or "estop_wire_break" in self._global_faults:
                    raise HardwareError("emergency stop is active")
            if self.output != bool(open_state):
                self._record("output", high=bool(open_state))
            self.output = bool(open_state)

    def force_safe_state(self) -> None:
        with self._lock:
            if self.output:
                self._record("output", high=False, forced=True)
            self.output = False

    def output_is_safe(self) -> bool:
        with self._lock:
            return not self.output

    def close(self) -> None:
        with self._lock:
            self.output = False
            self.closed = True

    # ------------------------------------------------------------- inspection
    def describe(self) -> dict[str, Any]:
        with self._lock:
            return {
                "sim_time_s": round(self._t, 3),
                "samples": self._samples,
                "seed": self.settings.seed,
                "time_scale": self.settings.time_scale,
                "estop_pressed": self.estop_pressed,
                "output": self.output,
                "channels": {
                    cid: {
                        "target": round(ch.target, 4),
                        "actual": round(ch.actual, 4),
                        "faults": sorted(ch.faults),
                    }
                    for cid, ch in self._channels.items()
                },
                "global_faults": sorted(self._global_faults),
            }
