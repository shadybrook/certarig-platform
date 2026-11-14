"""Versioned descriptions and deterministic support reports; no qualification authority."""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any

import jsonschema

from .contracts import fingerprint
from .store import Actor, uid

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "bench-spec-facts.json"
# Canonical value = original * gain + offset. Quantity and reference context remain separate.
UNITS = {
    "pressure": ("bar", {"bar": (1.0, 0.0), "kPa": (0.01, 0.0), "Pa": (0.00001, 0.0)}),
    "flow": ("L/min", {"L/min": (1.0, 0.0), "mL/min": (0.001, 0.0)}),
    "temperature": ("degC", {"degC": (1.0, 0.0), "K": (1.0, -273.15), "degF": (5 / 9, -160 / 9)}),
    "temperature_delta": ("delta_degC", {"delta_degC": (1.0, 0.0), "delta_K": (1.0, 0.0)}),
    "voltage": ("V", {"V": (1.0, 0.0)}),
    "current": ("A", {"A": (1.0, 0.0), "mA": (0.001, 0.0)}),
    "digital": ("state", {"state": (1.0, 0.0)}),
}
TEMPLATES = {
    "thermal_soak": {"temperature"},
    "pressure_guardrail": {"pressure"},
    "flow_guardrail": {"flow"},
    "dual_pot_guardrail": {"pressure", "flow"},
}
TRANSPORTS = {"simulator", "mqtt", "serial_jsonl", "modbus_tcp"}


def provenance(facts: dict[str, Any]) -> dict[str, Any]:
    """Each field remains declared; a referenced import does not authenticate its origin."""
    paths = ["/" + key for key in facts if key != "channels"]
    paths += [f"/channels/{i}/{key}" for i, c in enumerate(facts["channels"]) for key in c]
    return {
        path: {"kind": "operator_declared", "supporting_references": "/facts/source_refs"} for path in paths
    }


def normalize(quantity: str, unit: str, value: float) -> dict[str, Any]:
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError("Finite numeric sample required")
    if quantity not in UNITS or unit not in UNITS[quantity][1]:
        raise ValueError("Unsupported quantity/unit conversion")
    canonical, conversions = UNITS[quantity]
    gain, offset = conversions[unit]
    return {
        "value": value * gain + offset,
        "unit": canonical,
        "original_value": value,
        "original_unit": unit,
        "gain": gain,
        "offset": offset,
    }


class BenchSpecs:
    def __init__(self, platform: Any):
        self.p, self.s = platform, platform.store
        self.schema = json.loads(SCHEMA.read_text())

    def get(self, actor: Actor, identifier: str, *, edit: bool = False) -> dict[str, Any]:
        self.p.actor(actor)
        value = self.s.get("bench_spec", identifier, actor.org_id)
        if value["asset_id"]:
            self.p.asset(actor, value["asset_id"])
        elif value["owner_id"] != actor.user_id:
            raise PermissionError("Unlinked descriptions are private to their owner")
        if edit and value["owner_id"] != actor.user_id:
            raise PermissionError("Only the description owner may revise it")
        return value

    def listing(self, actor: Actor) -> list[dict[str, Any]]:
        self.p.actor(actor)
        result = []
        for value in self.s.listing("bench_spec", actor.org_id):
            try:
                result.append(self.get(actor, value["id"]))
            except (KeyError, PermissionError):
                continue
        return result

    def validate(self, facts: Any) -> dict[str, Any]:
        try:
            jsonschema.validate(facts, self.schema)
            if len(json.dumps(facts, allow_nan=False).encode()) > 64000:
                raise ValueError("Description exceeds 64 KiB")
        except (jsonschema.ValidationError, TypeError) as exc:
            raise ValueError("Invalid bounded bench description") from exc
        names = [c["channel_id"] for c in facts["channels"] if c.get("channel_id")]
        if len(names) != len(set(names)):
            raise ValueError("Contradictory duplicate channel identities")
        return json.loads(json.dumps(facts))

    def _bind(self, actor: Actor, asset_id: str | None, facts: dict[str, Any]) -> dict[str, Any]:
        asset = self.p.asset(actor, asset_id) if asset_id else None
        replay_id = facts.get("replay_id")
        if replay_id:
            replay = self.s.get("replay", replay_id, actor.org_id)
            self.p.asset(actor, replay["asset_id"])
            if not asset or replay["asset_id"] != asset_id:
                raise ValueError("Recorded data must belong to the linked bench")
            if replay["owner_id"] != actor.user_id:
                raise PermissionError("Use your own imported recording")
        return {
            "profile_hash": asset["profile_hash"] if asset else None,
            "profile_revision": asset.get("profile_revision", 1) if asset else None,
            "content_hash": fingerprint(
                {
                    "facts": facts,
                    "asset_id": asset_id,
                    "profile_hash": asset["profile_hash"] if asset else None,
                }
            ),
        }

    def create(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        self.p.actor(actor)
        if set(body) - {"facts", "asset_id"} or "facts" not in body:
            raise ValueError("Expected facts and optional linked asset only")
        facts = self.validate(body["facts"])
        asset_id = body.get("asset_id")
        if asset_id is not None and (not isinstance(asset_id, str) or not asset_id):
            raise ValueError("Linked asset must be an identifier or null")
        with self.s.atomic():
            value = {
                "id": uid("bsp"),
                "schema_version": 1,
                "org_id": actor.org_id,
                "owner_id": actor.user_id,
                "asset_id": asset_id,
                "revision": 1,
                "status": "draft",
                "facts": facts,
                "history": [],
                "provenance": provenance(facts),
                "created_at": self.s.clock(),
                **self._bind(actor, asset_id, facts),
            }
            self.s.put("bench_spec", value)
            self.s.audit(actor.org_id, "bench_description_created", actor.user_id, spec_id=value["id"])
            return value

    def revise(self, actor: Actor, identifier: str, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) - {"expected_revision", "facts", "asset_id"} or not {
            "expected_revision",
            "facts",
        } <= set(body):
            raise ValueError("Expected revision and complete description")
        with self.s.atomic():
            value = self.get(actor, identifier, edit=True)
            if type(body["expected_revision"]) is not int or value["revision"] != body["expected_revision"]:
                raise ValueError("Description changed; compare the current revision before saving")
            if value["revision"] >= 100:
                raise ValueError("Description history limit reached")
            facts = self.validate(body["facts"])
            asset_id = body.get("asset_id", value["asset_id"])
            if asset_id is not None and (not isinstance(asset_id, str) or not asset_id):
                raise ValueError("Linked asset must be an identifier or null")
            binding = self._bind(actor, asset_id, facts)
            value["history"].append(
                {
                    k: value[k]
                    for k in (
                        "revision",
                        "facts",
                        "content_hash",
                        "asset_id",
                        "status",
                        "profile_hash",
                        "profile_revision",
                        "provenance",
                        "review",
                        "proposal",
                    )
                    if k in value
                }
            )
            value.update(
                facts=facts,
                asset_id=asset_id,
                revision=value["revision"] + 1,
                status="draft",
                updated_at=self.s.clock(),
                **binding,
            )
            value["provenance"] = provenance(facts)
            value.pop("review", None)
            value.pop("proposal", None)
            self.s.put("bench_spec", value)
            self.s.audit(
                actor.org_id,
                "bench_description_revised",
                actor.user_id,
                spec_id=identifier,
                revision=value["revision"],
            )
            return value

    def assess(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.get(actor, identifier)
        facts, questions, transforms = value["facts"], [], []
        questions.extend(facts.get("unknowns", []))
        if not facts.get("source_refs"):
            questions.append("Supporting evidence references are missing")
        transport, procedure = facts.get("transport"), facts.get("procedure")
        if not facts.get("equipment"):
            questions.append("Equipment identity is missing")
        if not value["asset_id"]:
            questions.append("Link an operator-enrolled bench before review")
        else:
            asset = self.p.asset(actor, value["asset_id"])
            if (
                asset["profile_hash"] != value["profile_hash"]
                or asset.get("profile_revision", 1) != value["profile_revision"]
            ):
                questions.append("Reviewed bench profile changed; revise and reassess this description")
        if not facts["channels"]:
            questions.append("Signal identities are missing")
        quantities = set()
        for i, channel in enumerate(facts["channels"]):
            name = channel.get("channel_id") or f"channel {i + 1}"
            quantity, unit = channel.get("quantity"), channel.get("unit")
            quantities.add(quantity)
            for field in (
                "channel_id",
                "quantity",
                "unit",
                "calibration_id",
                "source",
                "scaling",
                "limits",
                "max_age_s",
            ):
                if channel.get(field) in (None, "", {}):
                    questions.append(f"{name}: missing {field}")
            if quantity not in UNITS or unit not in UNITS[quantity][1]:
                questions.append(f"{name}: unsupported quantity/unit pairing")
            else:
                conversion = normalize(quantity, unit, 0)
                transforms.append(
                    {
                        "channel_id": name,
                        **{k: conversion[k] for k in ("unit", "original_unit", "gain", "offset")},
                    }
                )
            if channel.get("scaling") and channel["scaling"]["gain"] == 0:
                questions.append(f"{name}: zero measurement scaling gain")
            if quantity == "pressure" and channel.get("reference") not in {
                "gauge",
                "absolute",
                "differential",
            }:
                questions.append(f"{name}: pressure reference is unknown")
            limits = channel.get("limits")
            if limits and not limits["min"] < limits["max"]:
                questions.append(f"{name}: contradictory operating limits")
        if procedure in TEMPLATES and not TEMPLATES[procedure] <= quantities:
            questions.append("Required procedure quantities are missing")
        unsupported = transport not in TRANSPORTS
        if unsupported:
            questions.append("Transport requires an operator-installed connector integration")
        if procedure not in TEMPLATES:
            questions.append("No trusted procedure/model/scenario pack exists for this experiment")
        status = (
            "unsupported_transport"
            if unsupported
            else "mapping_evidence_missing"
            if any(not q.startswith("No trusted") for q in questions)
            else "analysis_only"
            if procedure not in TEMPLATES
            else "procedure_qualification_required"
        )
        recording = None
        if facts.get("replay_id"):
            replay = self.s.get("replay", facts["replay_id"], actor.org_id)
            self.p.asset(actor, replay["asset_id"])
            recording = {
                "id": replay["id"],
                "sha256": replay["sha256"],
                "origin": replay["kind"],
                "samples": replay["samples"],
                "channels": sorted({r["channel_id"] for r in csv.DictReader(io.StringIO(replay["csv"]))}),
            }
        return {
            "spec_id": identifier,
            "revision": value["revision"],
            "content_hash": value["content_hash"],
            "status": status,
            "observation_supported": not unsupported,
            "procedure_supported": procedure in TEMPLATES,
            "qualified": False,
            "authority": "none",
            "questions": list(dict.fromkeys(questions)),
            "transforms": transforms,
            "source_refs": facts.get("source_refs", []),
            "provenance": value["provenance"],
            "recording": recording,
            "next_step": "Resolve missing evidence; qualify the exact profile and named procedure independently",
        }

    def propose(self, actor: Actor, identifier: str, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {"expected_revision"}:
            raise ValueError("Expected exact revision")
        with self.s.atomic():
            value = self.get(actor, identifier, edit=True)
            if type(body["expected_revision"]) is not int or value["revision"] != body["expected_revision"]:
                raise ValueError("Description changed")
            value.update(status="proposed", proposal=self.assess(actor, identifier))
            return self.s.put("bench_spec", value)

    def review(self, actor: Actor, identifier: str, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {"expected_revision", "content_hash"}:
            raise ValueError("Review requires exact revision and content hash")
        with self.s.atomic():
            self.p.reviewer(actor)
            value = self.get(actor, identifier)
            if value["owner_id"] == actor.user_id or not value["asset_id"]:
                raise PermissionError("Linked description requires an independent Reviewer")
            if (
                value["status"] != "proposed"
                or type(body["expected_revision"]) is not int
                or body["expected_revision"] != value["revision"]
                or body["content_hash"] != value["content_hash"]
            ):
                raise ValueError("Review belongs to another description revision")
            report = self.assess(actor, identifier)
            if report["status"] != "procedure_qualification_required" and report["status"] != "analysis_only":
                raise ValueError("Resolve description blockers before review")
            value.update(
                status="reviewed_description",
                review={
                    "reviewer_id": actor.user_id,
                    "at": self.s.clock(),
                    "content_hash": value["content_hash"],
                    "authority": "none",
                },
            )
            self.s.put("bench_spec", value)
            self.s.audit(
                actor.org_id,
                "bench_description_reviewed",
                actor.user_id,
                spec_id=identifier,
                revision=value["revision"],
                content_hash=value["content_hash"],
            )
            return value
