"""Schema, manifest and approval registry tests (no HTTP)."""

from __future__ import annotations

import copy
import json

import pytest

from certarig.edge.approvals import ApprovalError, ApprovalRegistry
from certarig.edge.capabilities import (
    ALWAYS_FORBIDDEN,
    TOOL_CATALOGUE,
    CapabilityError,
    CapabilityManifest,
    Policy,
    Principal,
)
from certarig.edge.config import ConfigurationError, load_config, load_config_dict
from certarig.edge.schemas import load_schema, schema_errors
from tests.support import CONFIG_DIR

WAVE1 = json.loads((CONFIG_DIR / "rig.wave1.json").read_text())
CAPS = json.loads((CONFIG_DIR / "capabilities.wave1.json").read_text())


# ----------------------------------------------------------------------------- rig schema
def test_shipped_configs_validate_and_hash_is_stable() -> None:
    for name in ("rig.example.json", "rig.wave1.json"):
        raw = json.loads((CONFIG_DIR / name).read_text())
        assert schema_errors(raw, "rig.schema.json") == []
        first = load_config(CONFIG_DIR / name)
        second = load_config(CONFIG_DIR / name)
        assert first.config_hash == second.config_hash
        assert len(first.config_hash) == 64


def test_concepts_are_derived_from_units_or_explicit() -> None:
    config = load_config_dict(WAVE1)
    by_id = {channel.channel_id: channel for channel in config.channels}
    assert by_id["pressure_emulator"].concept == "pressure"
    assert by_id["flow_emulator"].concept == "flow"
    raw = copy.deepcopy(WAVE1)
    raw["channels"][1]["concept"] = "coolant_flow"
    raw["channels"][1]["warning_max"] = 12.0
    config = load_config_dict(raw)
    flow = config.channel("flow_emulator")
    assert flow is not None and flow.concept == "coolant_flow" and flow.warning_max == 12.0
    signals = {row["channel_id"]: row for row in config.signals()}
    assert signals["flow_emulator"]["limits"]["warning"] == [None, 12.0]
    assert signals["pressure_emulator"]["limits"]["trip"] == [0.0, 4.2]
    assert signals["emergency_stop"]["source_id"] == "GPIO24"
    assert config.actuators()[0]["feedback_source_id"] is None


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda raw: raw.__setitem__("rig_id", "Bad Id!"), "rig_id"),
        (lambda raw: raw.__setitem__("sample_interval_ms", 5), "sample_interval_ms"),
        (lambda raw: raw.__setitem__("unexpected", 1), "unexpected"),
        (lambda raw: raw["hardware"].__setitem__("mode", "plc"), "mode"),
        (lambda raw: raw["channels"][0].__setitem__("channel_id", "0bad"), "channel_id"),
        (lambda raw: raw["channels"][0].pop("safe_max"), "safe_max"),
    ],
)
def test_rig_schema_rejects_bad_documents(mutate, fragment) -> None:  # type: ignore[no-untyped-def]
    raw = copy.deepcopy(WAVE1)
    mutate(raw)
    errors = schema_errors(raw, "rig.schema.json")
    assert errors, "expected schema errors"
    assert any(fragment in error for error in errors)
    with pytest.raises(ConfigurationError):
        load_config_dict(raw)


def test_semantic_checks_still_apply_after_schema() -> None:
    raw = copy.deepcopy(WAVE1)
    raw["channels"][0]["warning_max"] = 9.0  # outside safe range
    with pytest.raises(ConfigurationError, match="warning_max"):
        load_config_dict(raw)
    raw = copy.deepcopy(WAVE1)
    raw["pressure_abort_bar"] = 9.0
    with pytest.raises(ConfigurationError, match="pressure_abort_bar"):
        load_config_dict(raw)


def test_schema_files_are_valid_drafts() -> None:
    for name in ("rig.schema.json", "capabilities.schema.json"):
        schema = load_schema(name)
        assert schema["$schema"].endswith("2020-12/schema")


# ------------------------------------------------------------------- capability manifest
def test_manifest_loads_and_hashes() -> None:
    manifest = CapabilityManifest.from_dict(CAPS)
    assert manifest.policy("force_safe") is Policy.ALLOWED
    assert manifest.policy("bypass_interlock") is Policy.NEVER
    assert manifest.policy("reset_trip") is Policy.HUMAN_APPROVAL
    assert len(manifest.manifest_hash) == 64
    assert manifest.contract_hash("a" * 64) != manifest.contract_hash("b" * 64)
    assert set(manifest.policies) == set(TOOL_CATALOGUE)


def test_manifest_rejects_unknown_tools_and_forbidden_relaxation() -> None:
    raw = copy.deepcopy(CAPS)
    raw["tools"]["teleport"] = {"policy": "allowed"}
    with pytest.raises(ValueError, match="unknown tools"):
        CapabilityManifest.from_dict(raw)
    for tool in ALWAYS_FORBIDDEN:
        raw = copy.deepcopy(CAPS)
        raw["tools"][tool] = {"policy": "allowed"}
        with pytest.raises(ValueError, match="must have policy never"):
            CapabilityManifest.from_dict(raw)
    raw = copy.deepcopy(CAPS)
    raw["tools"]["read_state"] = {"policy": "human_approval"}
    with pytest.raises(ValueError, match="read-only"):
        CapabilityManifest.from_dict(raw)
    raw = copy.deepcopy(CAPS)
    raw["tools"]["read_state"] = {"policy": "sometimes"}
    with pytest.raises(ValueError):
        CapabilityManifest.from_dict(raw)


def test_unlisted_tools_default_to_never() -> None:
    raw = {"manifest_id": "tiny", "revision": "1", "tools": {"read_state": {"policy": "allowed"}}}
    manifest = CapabilityManifest.from_dict(raw)
    assert manifest.policy("force_safe") is Policy.NEVER
    assert [tool["name"] for tool in manifest.agent_tools()] == ["read_state"]


def test_authorize_matrix() -> None:
    manifest = CapabilityManifest.from_dict(CAPS)
    # anonymous: reads ok, mutations refused
    assert manifest.authorize("read_state", Principal.ANONYMOUS) is Policy.ALLOWED
    with pytest.raises(CapabilityError):
        manifest.authorize("force_safe", Principal.ANONYMOUS)
    # operator: everything except never
    assert manifest.authorize("reset_trip", Principal.OPERATOR) is Policy.ALLOWED
    assert manifest.authorize("request_permit", Principal.OPERATOR) is Policy.CONTROLLER_APPROVAL
    with pytest.raises(CapabilityError) as never:
        manifest.authorize("bypass_interlock", Principal.OPERATOR)
    assert never.value.to_dict()["policy"] == "never"
    with pytest.raises(CapabilityError):
        manifest.authorize("ack_operator_step", Principal.AGENT)
    # agent follows the manifest
    assert manifest.authorize("reset_trip", Principal.AGENT) is Policy.HUMAN_APPROVAL
    assert manifest.authorize("force_safe", Principal.AGENT) is Policy.ALLOWED
    with pytest.raises(CapabilityError, match="unknown tool"):
        manifest.authorize("nonexistent", Principal.AGENT)


def test_agent_tool_descriptors_add_approval_id_where_needed() -> None:
    manifest = CapabilityManifest.from_dict(CAPS)
    tools = {tool["name"]: tool for tool in manifest.agent_tools()}
    assert "approval_id" in tools["reset_trip"]["parameters"]["properties"]
    assert "approval_id" not in tools["force_safe"]["parameters"]["properties"]
    assert "human approval" in tools["reset_trip"]["description"]
    assert "ack_operator_step" not in tools


def test_read_only_manifest() -> None:
    manifest = CapabilityManifest.read_only()
    assert all(
        manifest.policy(name) is (Policy.ALLOWED if not spec.mutating else Policy.NEVER)
        for name, spec in TOOL_CATALOGUE.items()
    )


# ----------------------------------------------------------------------- approvals
def test_approval_registry_lifecycle_and_expiry() -> None:
    clock = {"now": 1000.0}
    registry = ApprovalRegistry(ttl_s=60, clock=lambda: clock["now"])
    approval = registry.request("reset_trip", {}, "why", "contract-a", requested_by="agent")
    assert approval.status == "pending"
    with pytest.raises(ApprovalError, match="pending"):
        registry.consume(approval.approval_id, "reset_trip", {}, "contract-a")
    registry.decide(approval.approval_id, True, "op")
    with pytest.raises(ApprovalError, match="different rig contract"):
        registry.consume(approval.approval_id, "reset_trip", {}, "contract-b")
    with pytest.raises(ApprovalError, match="different tool"):
        registry.consume(approval.approval_id, "shutdown", {}, "contract-a")
    clock["now"] += 61
    with pytest.raises(ApprovalError, match="expired"):
        registry.consume(approval.approval_id, "reset_trip", {}, "contract-a")
    assert registry.get(approval.approval_id) is not None
    assert registry.list("expired")[0]["approval_id"] == approval.approval_id
    with pytest.raises(ApprovalError, match="not pending"):
        registry.decide(approval.approval_id, False, "op")
    with pytest.raises(KeyError):
        registry.decide("apr_missing", True, "op")
    assert registry.get("apr_missing") is None
    with pytest.raises(ApprovalError, match="not found"):
        registry.consume("apr_missing", "reset_trip", {}, "contract-a")
