from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class PlanState(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    BLOCKED = "blocked"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    STOPPED = "stopped"


class RunOutcome(StrEnum):
    COMPLETED = "completed"
    SAFE_ABORT = "safe_abort"
    BLOCKED = "blocked"
    STOPPED = "stopped"


@dataclass(frozen=True)
class ChannelConfig:
    channel_id: str
    kind: str
    unit: str
    valid_min: float
    valid_max: float
    safe_min: float
    safe_max: float
    calibration_id: str | None
    required: bool = True
    adc_channel: int | None = None
    raw_min_v: float | None = None
    raw_max_v: float | None = None
    engineering_min: float | None = None
    engineering_max: float | None = None
    concept: str = "signal"
    warning_min: float | None = None
    warning_max: float | None = None


CONCEPT_BY_UNIT = {
    "bar": "pressure",
    "psi": "pressure",
    "kpa": "pressure",
    "l/min": "flow",
    "lpm": "flow",
    "kg/s": "mass_flow",
    "c": "temperature",
    "degc": "temperature",
    "k": "temperature",
    "v": "voltage",
    "a": "current",
}


@dataclass(frozen=True)
class HardwareConfig:
    mode: str = "mock"
    i2c_bus: int = 1
    ads1115_address: int = 0x48
    valve_output_gpio: int = 23
    emergency_stop_gpio: int = 24
    emergency_stop_active_high: bool = True
    relay_feedback_gpio: int | None = 25
    output_active_high: bool = True
    simulator: dict[str, Any] | None = None


@dataclass(frozen=True)
class RigConfig:
    rig_id: str
    revision: str
    sample_interval_ms: int
    pressure_abort_bar: float
    hardware: HardwareConfig
    channels: tuple[ChannelConfig, ...]
    config_hash: str

    def public_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["channels"] = [asdict(channel) for channel in self.channels]
        return value

    def channel(self, channel_id: str) -> ChannelConfig | None:
        for channel in self.channels:
            if channel.channel_id == channel_id:
                return channel
        return None

    def signals(self) -> list[dict[str, Any]]:
        """Customer signal to CertaRig concept mapping, as shown in Studio onboarding."""
        rows: list[dict[str, Any]] = []
        for channel in self.channels:
            source = f"ADS1115:A{channel.adc_channel}" if channel.adc_channel is not None else "virtual"
            rows.append(
                {
                    "channel_id": channel.channel_id,
                    "source_id": source,
                    "concept": channel.concept,
                    "unit": channel.unit,
                    "required": channel.required,
                    "limits": {
                        "valid": [channel.valid_min, channel.valid_max],
                        "warning": [channel.warning_min, channel.warning_max],
                        "trip": [
                            channel.safe_min,
                            min(channel.safe_max, self.pressure_abort_bar)
                            if channel.concept == "pressure"
                            else channel.safe_max,
                        ],
                    },
                    "calibration_id": channel.calibration_id,
                }
            )
        rows.append(
            {
                "channel_id": "emergency_stop",
                "source_id": f"GPIO{self.hardware.emergency_stop_gpio}",
                "concept": "emergency_stop",
                "unit": "bool",
                "required": True,
                "limits": None,
                "calibration_id": None,
            }
        )
        return rows

    def actuators(self) -> list[dict[str, Any]]:
        return [
            {
                "actuator_id": "main_output",
                "concept": "permit_relay",
                "source_id": f"GPIO{self.hardware.valve_output_gpio}",
                "feedback_source_id": (
                    f"GPIO{self.hardware.relay_feedback_gpio}"
                    if self.hardware.relay_feedback_gpio is not None
                    else None
                ),
                "active_high": self.hardware.output_active_high,
            }
        ]


@dataclass(frozen=True)
class Sample:
    channel_id: str
    value: float
    unit: str
    raw_value: float | None
    quality: str
    captured_at: str


@dataclass(frozen=True)
class RigSnapshot:
    rig_id: str
    config_hash: str
    emergency_stop_active: bool
    output_safe: bool
    samples: tuple[Sample, ...]
    captured_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rig_id": self.rig_id,
            "config_hash": self.config_hash,
            "emergency_stop_active": self.emergency_stop_active,
            "output_safe": self.output_safe,
            "samples": [asdict(sample) for sample in self.samples],
            "captured_at": self.captured_at,
        }


@dataclass(frozen=True)
class PlanStep:
    action: str
    duration_ms: int
    valve_open: bool | None = None
    expected_pressure_min: float | None = None
    expected_pressure_max: float | None = None


@dataclass
class CommissioningPlan:
    plan_id: str
    rig_id: str
    config_hash: str
    purpose: str
    pressure_limit_bar: float
    steps: list[PlanStep]
    state: PlanState = PlanState.PROPOSED
    findings: list[str] = field(default_factory=list)
    created_at: str = ""
    approved_at: str | None = None
    approved_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        return value


@dataclass(frozen=True)
class EvidenceEvent:
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any]
    recorded_at: str


@dataclass(frozen=True)
class RunResult:
    run_id: str
    plan_id: str
    outcome: RunOutcome
    reason: str
    started_at: str
    completed_at: str
    max_pressure_bar: float
    evidence_checksum: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["outcome"] = self.outcome.value
        return value
