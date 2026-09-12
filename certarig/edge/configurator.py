"""Propose and apply rig / capability documents without a silent rewrite."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .atomic import write_json_atomic
from .capabilities import CapabilityManifest
from .config import load_config_dict
from .models import RigConfig

HARDWARE_IDENTITY_KEYS = ("mode", "i2c_bus", "ads1115_address", "valve_output_gpio", "emergency_stop_gpio")


def _diff(before: dict[str, Any], after: dict[str, Any], prefix: str = "") -> list[str]:
    rows: list[str] = []
    keys = sorted(set(before) | set(after))
    for key in keys:
        path = f"{prefix}.{key}" if prefix else key
        if key not in before:
            rows.append(f"+ {path}")
        elif key not in after:
            rows.append(f"- {path}")
        elif before[key] != after[key]:
            if isinstance(before[key], dict) and isinstance(after[key], dict):
                rows.extend(_diff(before[key], after[key], path))
            else:
                rows.append(f"~ {path}")
    return rows


def merge_document(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if not patch:
        return copy.deepcopy(current)
    if "channels" in patch or "rig_id" in patch or "hardware" in patch or "abort_limits" in patch:
        merged = copy.deepcopy(current)
        merged.update(copy.deepcopy(patch))
        return merged
    return copy.deepcopy(patch)


def restart_required(current: RigConfig, proposed: RigConfig) -> bool:
    ch = current.hardware
    ph = proposed.hardware
    if any(getattr(ch, key) != getattr(ph, key) for key in HARDWARE_IDENTITY_KEYS):
        return True
    current_map = {(c.channel_id, c.adc_channel, json.dumps(c.source, sort_keys=True)) for c in current.channels}
    proposed_map = {(c.channel_id, c.adc_channel, json.dumps(c.source, sort_keys=True)) for c in proposed.channels}
    return current_map != proposed_map


def propose_rig(current_raw: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    proposed_raw = merge_document(current_raw, incoming)
    proposed = load_config_dict(proposed_raw)
    current = load_config_dict(current_raw)
    return {
        "diff": _diff(current_raw, proposed_raw),
        "current_hash": current.config_hash,
        "next_hash": proposed.config_hash,
        "restart_required": restart_required(current, proposed),
        "document": proposed_raw,
    }


def apply_rig(path: Path, current_raw: dict[str, Any], incoming: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    current = load_config_dict(current_raw)
    if current.config_hash != expected_hash:
        raise ValueError("expected_current_hash does not match the file on disk")
    preview = propose_rig(current_raw, incoming)
    write_json_atomic(path, preview["document"])
    return preview


def propose_capabilities(current_raw: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    proposed_raw = merge_document(current_raw, incoming)
    proposed = CapabilityManifest.from_dict(proposed_raw)
    current = CapabilityManifest.from_dict(current_raw)
    return {
        "diff": _diff(current_raw, proposed_raw),
        "current_hash": current.manifest_hash,
        "next_hash": proposed.manifest_hash,
        "restart_required": False,
        "document": proposed_raw,
    }


def apply_capabilities(path: Path, current_raw: dict[str, Any], incoming: dict[str, Any], expected_hash: str) -> dict[str, Any]:
    current = CapabilityManifest.from_dict(current_raw)
    if current.manifest_hash != expected_hash:
        raise ValueError("expected_current_hash does not match the file on disk")
    preview = propose_capabilities(current_raw, incoming)
    write_json_atomic(path, preview["document"])
    return preview
