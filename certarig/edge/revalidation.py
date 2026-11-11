"""Conservative, source-explained qualification dependencies for a changed rig."""

from __future__ import annotations

from typing import Any

from .config import canonical_hash
from .models import RigConfig


def model_revision(config: RigConfig) -> str:
    return "thermal-rc-v1" if (config.hardware.simulator or {}).get("plant") == "thermal_rc" else "generic-lag-v1"


def test_profile(config: RigConfig) -> dict[str, Any]:
    """Exclude deployment transport/mode, retain all tested signal/control semantics."""
    raw = config.public_dict()
    hardware = raw["hardware"]
    return {
        "channels": sorted(raw["channels"], key=lambda c: c["channel_id"]),
        "abort_limits": raw["abort_limits"],
        "sample_interval_ms": raw["sample_interval_ms"],
        "wiring_revision": raw["wiring_revision"],
        "controls": {
            k: v
            for k, v in hardware.items()
            if k not in {"mode", "observe_only", "simulator", "mqtt", "modbus"}
        },
        "model": hardware.get("simulator") or {},
        "model_revision": model_revision(config),
    }


def profile_hash(config: RigConfig) -> str:
    return canonical_hash(test_profile(config))


def revalidation(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old = {c["channel_id"]: c for c in before.get("channels", [])}
    new = {c["channel_id"]: c for c in after.get("channels", [])}
    changes: list[dict[str, Any]] = []
    for cid in sorted(old.keys() | new.keys()):
        fields = sorted(
            k
            for k in (old.get(cid, {}).keys() | new.get(cid, {}).keys())
            if old.get(cid, {}).get(k) != new.get(cid, {}).get(k)
        )
        if fields:
            changes.append(
                {
                    "channel_id": cid,
                    "fields": fields,
                    "repeat": ["channel_identity", "calibration", "range_and_quality", "procedure_rehearsal"],
                    "reason": "Changed measurement claim invalidates its prior qualification",
                }
            )
    other = sorted(
        k for k in before.keys() | after.keys() if k != "channels" and before.get(k) != after.get(k)
    )
    full = bool(other)
    return {
        "changed_channels": changes,
        "changed_rig_fields": other,
        "full_qualification": full,
        "required_checks": ["mapping_review", "all_supported_procedures", "safe_state_and_recovery"]
        if full
        else sorted({check for c in changes for check in c["repeat"]}),
        "reason": "Rig-level or unclassified change requires full qualification"
        if full
        else "Repeat the declared dependencies of changed channels; this is not a globally minimal-test proof",
        "execution_authority": "new_review_and_approval_required" if before != after else "unchanged",
    }
