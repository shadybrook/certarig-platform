from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import CONCEPT_BY_UNIT, ChannelConfig, HardwareConfig, RigConfig
from .schemas import validate_against_schema


class ConfigurationError(ValueError):
    pass


def canonical_hash(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{field} must be numeric")
    return float(value)


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{field} must be true or false")
    return value


def load_config(path: str | Path) -> RigConfig:
    source = Path(path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    return load_config_dict(raw)


def load_config_dict(raw: Any) -> RigConfig:
    if not isinstance(raw, dict):
        raise ConfigurationError("configuration root must be an object")
    validate_against_schema(raw, "rig.schema.json", ConfigurationError)

    channels_raw = raw.get("channels")
    if not isinstance(channels_raw, list) or not channels_raw:
        raise ConfigurationError("at least one channel is required")

    channels: list[ChannelConfig] = []
    identifiers: set[str] = set()
    for index, item in enumerate(channels_raw):
        if not isinstance(item, dict):
            raise ConfigurationError(f"channels[{index}] must be an object")
        channel_id = str(item.get("channel_id", "")).strip()
        if not channel_id or channel_id in identifiers:
            raise ConfigurationError(f"channels[{index}] has a missing or duplicate channel_id")
        identifiers.add(channel_id)
        valid_min = _require_number(item.get("valid_min"), f"{channel_id}.valid_min")
        valid_max = _require_number(item.get("valid_max"), f"{channel_id}.valid_max")
        safe_min = _require_number(item.get("safe_min"), f"{channel_id}.safe_min")
        safe_max = _require_number(item.get("safe_max"), f"{channel_id}.safe_max")
        if not valid_min <= safe_min <= safe_max <= valid_max:
            raise ConfigurationError(f"{channel_id} safe range must be inside valid range")
        warning_min = (
            _require_number(item["warning_min"], f"{channel_id}.warning_min")
            if item.get("warning_min") is not None
            else None
        )
        warning_max = (
            _require_number(item["warning_max"], f"{channel_id}.warning_max")
            if item.get("warning_max") is not None
            else None
        )
        if warning_max is not None and not safe_min <= warning_max <= safe_max:
            raise ConfigurationError(f"{channel_id} warning_max must be inside the safe range")
        if warning_min is not None and not safe_min <= warning_min <= safe_max:
            raise ConfigurationError(f"{channel_id} warning_min must be inside the safe range")
        unit = str(item.get("unit", ""))
        concept = str(item.get("concept") or CONCEPT_BY_UNIT.get(unit.lower(), "signal"))
        required = bool(item.get("required", True))
        calibration_id = item.get("calibration_id")
        if required and not str(calibration_id or "").strip():
            raise ConfigurationError(f"{channel_id} requires a calibration_id")

        channels.append(
            ChannelConfig(
                channel_id=channel_id,
                kind=str(item.get("kind", "analog")),
                unit=unit,
                concept=concept,
                warning_min=warning_min,
                warning_max=warning_max,
                valid_min=valid_min,
                valid_max=valid_max,
                safe_min=safe_min,
                safe_max=safe_max,
                calibration_id=str(calibration_id) if calibration_id else None,
                required=required,
                adc_channel=int(item["adc_channel"]) if item.get("adc_channel") is not None else None,
                raw_min_v=float(item["raw_min_v"]) if item.get("raw_min_v") is not None else None,
                raw_max_v=float(item["raw_max_v"]) if item.get("raw_max_v") is not None else None,
                engineering_min=float(item["engineering_min"])
                if item.get("engineering_min") is not None
                else None,
                engineering_max=float(item["engineering_max"])
                if item.get("engineering_max") is not None
                else None,
            )
        )

    hardware_raw = raw.get("hardware", {})
    hardware = HardwareConfig(
        mode=str(hardware_raw.get("mode", "mock")),
        i2c_bus=int(hardware_raw.get("i2c_bus", 1)),
        ads1115_address=int(hardware_raw.get("ads1115_address", 0x48)),
        valve_output_gpio=int(hardware_raw.get("valve_output_gpio", 23)),
        emergency_stop_gpio=int(hardware_raw.get("emergency_stop_gpio", 24)),
        emergency_stop_active_high=_require_bool(
            hardware_raw.get("emergency_stop_active_high", True),
            "hardware.emergency_stop_active_high",
        ),
        relay_feedback_gpio=(
            int(hardware_raw["relay_feedback_gpio"])
            if hardware_raw.get("relay_feedback_gpio") is not None
            else None
        ),
        output_active_high=_require_bool(
            hardware_raw.get("output_active_high", True),
            "hardware.output_active_high",
        ),
        simulator=dict(hardware_raw["simulator"]) if hardware_raw.get("simulator") is not None else None,
    )
    sample_interval_ms = int(raw.get("sample_interval_ms", 100))
    if sample_interval_ms < 20:
        raise ConfigurationError("sample_interval_ms must be at least 20")
    pressure_abort_bar = _require_number(raw.get("pressure_abort_bar"), "pressure_abort_bar")
    pressure_channels = [channel for channel in channels if channel.unit.lower() == "bar"]
    if not pressure_channels:
        raise ConfigurationError("at least one pressure channel with unit bar is required")
    if pressure_abort_bar > min(channel.safe_max for channel in pressure_channels):
        raise ConfigurationError("pressure_abort_bar may not exceed the configured pressure safe_max")

    return RigConfig(
        rig_id=str(raw.get("rig_id", "")).strip(),
        revision=str(raw.get("revision", "")).strip(),
        sample_interval_ms=sample_interval_ms,
        pressure_abort_bar=pressure_abort_bar,
        hardware=hardware,
        channels=tuple(channels),
        config_hash=canonical_hash(raw),
    )
