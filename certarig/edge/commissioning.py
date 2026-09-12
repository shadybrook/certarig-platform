from __future__ import annotations

import math
from dataclasses import dataclass

from .models import RigConfig, RigSnapshot, in_valid_range


@dataclass(frozen=True)
class InterlockResult:
    drive_high: bool
    permit_requested: bool
    trip_latched: bool
    event: str


class DryBenchInterlock:
    """Deterministic state machine for the Phase 3 output test.

    This class does not access GPIO. Releasing the E-stop never restores a
    previous permit; the operator must reset the trip and request permit again.
    """

    def __init__(self, allow_output: bool = False) -> None:
        self.allow_output = allow_output
        self.permit_requested = False
        self.trip_latched = True
        self.estop_active = True

    @property
    def drive_high(self) -> bool:
        return bool(
            self.allow_output and self.permit_requested and not self.trip_latched and not self.estop_active
        )

    def result(self, event: str) -> InterlockResult:
        return InterlockResult(
            drive_high=self.drive_high,
            permit_requested=self.permit_requested,
            trip_latched=self.trip_latched,
            event=event,
        )

    def observe(self, estop_active: bool) -> InterlockResult:
        previous = self.estop_active
        self.estop_active = bool(estop_active)
        if self.estop_active:
            was_requested = self.permit_requested
            self.permit_requested = False
            self.trip_latched = True
            if not previous:
                return self.result("estop_open_forced_safe")
            if was_requested:
                return self.result("estop_active_request_cleared")
        elif previous:
            return self.result("estop_closed_reset_required")
        return self.result("")

    def command(self, command: str) -> InterlockResult:
        requested = command.strip().lower()
        if requested == "safe":
            self.permit_requested = False
            return self.result("operator_safe")
        if requested == "reset":
            self.permit_requested = False
            if self.estop_active:
                self.trip_latched = True
                return self.result("reset_rejected_estop_open")
            self.trip_latched = False
            return self.result("trip_reset_output_safe")
        if requested == "permit":
            if not self.allow_output:
                self.permit_requested = False
                return self.result("permit_rejected_monitor_only")
            if self.estop_active:
                self.permit_requested = False
                self.trip_latched = True
                return self.result("permit_rejected_estop_open")
            if self.trip_latched:
                self.permit_requested = False
                return self.result("permit_rejected_reset_required")
            self.permit_requested = True
            return self.result("permit_accepted")
        return self.result("unknown_command")


@dataclass(frozen=True)
class ProcessInterlockResult:
    drive_high: bool
    permit_requested: bool
    trip_latched: bool
    estop_active: bool
    process_healthy: bool
    reason: str
    event: str
    channels: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "drive_high": self.drive_high,
            "permit_requested": self.permit_requested,
            "trip_latched": self.trip_latched,
            "estop_active": self.estop_active,
            "process_healthy": self.process_healthy,
            "reason": self.reason,
            "event": self.event,
            "channels": list(self.channels),
        }


class ProcessGuardrail:
    """Fail-safe Phase 3 guardrail for E-stop and required process channels.

    The guardrail is deliberately independent of GPIO and the dashboard. It
    latches every unsafe observation, never restarts automatically, and only
    permits an output after a healthy observation followed by explicit reset
    and permit commands.
    """

    def __init__(self, config: RigConfig, allow_output: bool = False) -> None:
        self.config = config
        self.allow_output = allow_output
        self.permit_requested = False
        self.trip_latched = True
        self.estop_active = True
        self.process_healthy = False
        self.reason = "startup_safe"
        self.channels: tuple[dict[str, object], ...] = ()
        self._condition = "startup"
        self._last_values: dict[str, float] = {}
        self._stuck_counts: dict[str, int] = {}

    @property
    def drive_high(self) -> bool:
        return bool(
            self.allow_output
            and self.permit_requested
            and not self.trip_latched
            and not self.estop_active
            and self.process_healthy
        )

    def result(self, event: str = "") -> ProcessInterlockResult:
        return ProcessInterlockResult(
            drive_high=self.drive_high,
            permit_requested=self.permit_requested,
            trip_latched=self.trip_latched,
            estop_active=self.estop_active,
            process_healthy=self.process_healthy,
            reason=self.reason,
            event=event,
            channels=self.channels,
        )

    @staticmethod
    def _event_prefix(channel_id: str, concept: str, unit: str) -> str:
        if concept and concept != "signal":
            return concept
        lowered = unit.lower()
        if lowered == "bar":
            return "pressure"
        if lowered in {"l/min", "lpm"}:
            return "flow"
        return "".join(character if character.isalnum() else "_" for character in channel_id).strip("_")

    def observe(self, snapshot: RigSnapshot) -> ProcessInterlockResult:
        previous_estop = self.estop_active
        previous_condition = self._condition
        self.estop_active = bool(snapshot.emergency_stop_active)
        samples = {sample.channel_id: sample for sample in snapshot.samples}
        statuses: list[dict[str, object]] = []
        first_problem: tuple[str, str] | None = None

        for channel in self.config.channels:
            if not channel.required:
                continue
            abort = self.config.abort_limits.get(channel.concept)
            safe_max = min(channel.safe_max, abort) if abort is not None else channel.safe_max
            sample = samples.get(channel.channel_id)
            state = "safe"
            value: float | None = None
            quality = "missing"
            if sample is None:
                state = "invalid"
            else:
                value = float(sample.value)
                quality = sample.quality
                if (
                    quality == "good"
                    and value is not None
                    and math.isfinite(value)
                    and channel.stuck_samples
                ):
                    previous = self._last_values.get(channel.channel_id)
                    epsilon = channel.stuck_epsilon if channel.stuck_epsilon is not None else 1e-6
                    if previous is not None and abs(value - previous) < epsilon:
                        self._stuck_counts[channel.channel_id] = (
                            self._stuck_counts.get(channel.channel_id, 0) + 1
                        )
                    else:
                        self._stuck_counts[channel.channel_id] = 0
                    self._last_values[channel.channel_id] = value
                    if self._stuck_counts.get(channel.channel_id, 0) >= channel.stuck_samples:
                        quality = "stuck"
                if not math.isfinite(value) or quality not in {"good"}:
                    state = "invalid"
                    if not math.isfinite(value):
                        value = None
                elif not in_valid_range(channel, value):
                    state = "invalid"
                elif value < channel.safe_min and not (
                    channel.safe_min == 0.0 and in_valid_range(channel, value)
                ):
                    state = "low"
                elif value > safe_max:
                    state = "high"
            statuses.append(
                {
                    "channel_id": channel.channel_id,
                    "concept": channel.concept,
                    "value": value,
                    "unit": channel.unit,
                    "quality": quality,
                    "safe_min": channel.safe_min,
                    "safe_max": safe_max,
                    "state": state,
                }
            )
            if first_problem is None and state != "safe":
                prefix = self._event_prefix(channel.channel_id, channel.concept, channel.unit)
                first_problem = (state, prefix)

        self.channels = tuple(statuses)
        event = ""
        if self.estop_active:
            self._condition = "estop_open"
            self.process_healthy = first_problem is None
            self.permit_requested = False
            self.trip_latched = True
            self.reason = "estop_open"
            if not previous_estop or previous_condition != self._condition:
                event = "estop_open_forced_safe"
        elif first_problem is not None:
            state, prefix = first_problem
            self._condition = f"{prefix}_{state}"
            self.process_healthy = False
            self.permit_requested = False
            self.trip_latched = True
            self.reason = self._condition
            if previous_condition != self._condition:
                if state == "invalid":
                    event = "sensor_invalid_forced_safe"
                else:
                    event = f"{prefix}_{state}_forced_safe"
        else:
            self._condition = "process_safe"
            self.process_healthy = True
            if previous_estop:
                self.reason = "reset_required"
                event = "estop_closed_reset_required"
            elif previous_condition != self._condition:
                self.reason = "reset_required"
                event = "process_safe_reset_required"
            elif self.drive_high:
                self.reason = "permit_active"
            elif self.trip_latched:
                self.reason = "reset_required"
            elif not self.permit_requested:
                self.reason = "output_safe"
        return self.result(event)

    def command(self, command: str) -> ProcessInterlockResult:
        requested = command.strip().lower()
        if requested == "safe":
            self.permit_requested = False
            self.trip_latched = True
            self.reason = "operator_safe"
            return self.result("operator_safe")
        if requested == "reset":
            self.permit_requested = False
            if self.estop_active:
                self.trip_latched = True
                self.reason = "estop_open"
                return self.result("reset_rejected_estop_open")
            if not self.process_healthy:
                self.trip_latched = True
                return self.result("reset_rejected_process_unsafe")
            self.trip_latched = False
            self.reason = "output_safe"
            return self.result("trip_reset_output_safe")
        if requested == "permit":
            if not self.allow_output:
                self.permit_requested = False
                self.reason = "monitor_only"
                return self.result("permit_rejected_monitor_only")
            if self.estop_active:
                self.permit_requested = False
                self.trip_latched = True
                self.reason = "estop_open"
                return self.result("permit_rejected_estop_open")
            if not self.process_healthy:
                self.permit_requested = False
                self.trip_latched = True
                return self.result("permit_rejected_process_unsafe")
            if self.trip_latched:
                self.permit_requested = False
                self.reason = "reset_required"
                return self.result("permit_rejected_reset_required")
            self.permit_requested = True
            self.reason = "permit_active"
            return self.result("permit_accepted")
        return self.result("unknown_command")

    def fail_safe(self, reason: str = "sensor_runtime_error") -> ProcessInterlockResult:
        self.permit_requested = False
        self.trip_latched = True
        self.process_healthy = False
        self.reason = reason
        self._condition = reason
        return self.result(f"{reason}_forced_safe")
