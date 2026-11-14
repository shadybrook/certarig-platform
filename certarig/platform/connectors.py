"""Reviewed public connector mapping proposals, never arbitrary endpoint execution."""

from __future__ import annotations

from typing import Any

from .contracts import encoded, fingerprint
from .store import Actor, uid
from .workbench import text


def registered(platform: Any, actor: Actor) -> list[dict[str, Any]]:
    """Public enrollment metadata only; never expose endpoint or credential fields."""
    platform.reviewer(actor)
    enrolled = {a["connector"] for a in platform.store.listing("asset", actor.org_id)}
    return [
        {
            "id": identifier,
            "name": str(config.get("name", identifier)),
            "mode": config.get("mode", "operator-registered"),
            "enrolled": identifier in enrolled,
            "observation_only": True,
        }
        for identifier, config in platform.connectors.items()
        if config.get("org_id") == actor.org_id
    ]


class ConnectorProfiles:
    def __init__(self, platform: Any):
        self.p, self.s = platform, platform.store

    def create(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {"asset_id", "name", "transport", "channels"} or body["transport"] not in {
            "mqtt",
            "serial_jsonl",
            "modbus_tcp",
        }:
            raise ValueError("Choose a supported observation transport and public mappings")
        asset = self.p.asset(actor, body["asset_id"])
        channels = body["channels"]
        if not isinstance(channels, list) or not 1 <= len(channels) <= 16 or len(encoded(channels)) > 32000:
            raise ValueError("One to sixteen bounded channel mappings required")
        identities = set()
        allowed = {
            "channel_id",
            "unit",
            "calibration_id",
            "valid_min",
            "valid_max",
            "safe_min",
            "safe_max",
            "max_age_s",
            "source",
        }
        for channel in channels:
            if set(channel) != allowed:
                raise ValueError(
                    "Each channel requires identity, units, calibration, limits, freshness and source"
                )
            for key in ("channel_id", "unit", "calibration_id"):
                text(channel[key], 128)
            if channel["channel_id"] in identities:
                raise ValueError("Duplicate channel identity")
            identities.add(channel["channel_id"])
            if (
                not channel["valid_min"] <= channel["safe_min"] < channel["safe_max"] <= channel["valid_max"]
                or not 0 < channel["max_age_s"] <= 60
            ):
                raise ValueError("Contradictory operating limits or freshness")
            source = channel["source"]
            if not isinstance(source, dict):
                raise ValueError("Public signal source required")
            permitted = (
                {"topic"}
                if body["transport"] == "mqtt"
                else (
                    {"channel_id"}
                    if body["transport"] == "serial_jsonl"
                    else {
                        "register",
                        "device_id",
                        "data_type",
                        "function",
                        "byte_order",
                        "word_order",
                        "gain",
                        "offset",
                    }
                )
            )
            if set(source) - permitted or not source or "://" in str(source) or "@" in str(source):
                raise ValueError(
                    "Only public mapping fields allowed; keep endpoints and credentials in operator settings"
                )
            if body["transport"] == "mqtt" and (
                not isinstance(source.get("topic"), str)
                or not source["topic"]
                or "+" in source["topic"]
                or "#" in source["topic"]
            ):
                raise ValueError("Unique exact MQTT topics required")
            if body["transport"] == "serial_jsonl" and source.get("channel_id") != channel["channel_id"]:
                raise ValueError("Serial source identity must match channel identity")
            if body["transport"] == "modbus_tcp":
                from certarig.connectors.modbus import ModbusSource

                ModbusSource({"host": "operator-configured"}, [channel])
        value = {
            "id": uid("cpr"),
            "org_id": actor.org_id,
            "owner_id": actor.user_id,
            **body,
            "name": text(body["name"], 120),
            "base_profile_hash": asset["profile_hash"],
            "status": "proposed",
            "observe_only": True,
        }
        value["hash"] = fingerprint(value)
        return self.s.put("connector_profile", value)

    def get(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.s.get("connector_profile", identifier, actor.org_id)
        self.p.asset(actor, value["asset_id"])
        return value

    def review(self, actor: Actor, identifier: str) -> dict[str, Any]:
        self.p.reviewer(actor)
        with self.s.atomic():
            value = self.get(actor, identifier)
            if value["owner_id"] == actor.user_id:
                raise PermissionError("Independent mapping review required")
            if (
                value["base_profile_hash"] != self.p.asset(actor, value["asset_id"])["profile_hash"]
                or value["status"] != "proposed"
            ):
                raise ValueError("Stale or already reviewed mapping proposal")
            value.update(status="reviewed_for_operator_installation", reviewer_id=actor.user_id)
            return self.s.put("connector_profile", value)
