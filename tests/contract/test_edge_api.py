"""Contract tests for the unified Edge API: auth, capabilities, contract hash, approvals."""

from __future__ import annotations

import pytest

from certarig.edge.client import EdgeApiError
from tests.support import edge_server


def test_health_rig_signals_and_capabilities_are_public_reads() -> None:
    with edge_server() as edge:
        anon = edge.anonymous()
        health = anon.health()
        assert health["status"] == "ok"
        assert health["contract_hash"] == edge.node.contract_hash
        rig = anon.rig()
        assert rig["rig"]["rig_id"] == "certarig-wave1-dry-bench"
        concepts = {row["concept"] for row in rig["signals"]}
        assert {"pressure", "flow", "emergency_stop"} <= concepts
        pressure = next(row for row in rig["signals"] if row["concept"] == "pressure")
        assert pressure["limits"]["trip"] == [0.0, 4.2]
        assert rig["actuators"][0]["source_id"] == "GPIO23"
        caps = anon.capabilities()
        assert caps["principal"] == "anonymous"
        policies = {tool["name"]: tool["policy"] for tool in caps["tools"]}
        assert policies["bypass_interlock"] == "never"
        assert policies["reset_trip"] == "human_approval"
        assert "bypass_interlock" not in {tool["name"] for tool in caps["agent_tools"]}
        state = anon.state()
        assert state["guardrail"]["process_healthy"] is True


def test_studio_static_assets_are_served_and_traversal_is_blocked() -> None:
    with edge_server() as edge:
        page = edge.anonymous().request("GET", "/", raw=True)
        assert b"<html" in page.lower()
        with pytest.raises(EdgeApiError) as missing:
            edge.anonymous().request("GET", "/../pyproject.toml", raw=True)
        assert missing.value.status == 404


def test_unknown_route_and_wrong_method() -> None:
    with edge_server() as edge:
        with pytest.raises(EdgeApiError) as not_found:
            edge.anonymous().get("/v1/nope")
        assert not_found.value.status == 404
        with pytest.raises(EdgeApiError) as wrong_method:
            edge.operator().post("/v1/live/state", {})
        assert wrong_method.value.status == 405


def test_anonymous_cannot_mutate() -> None:
    with edge_server() as edge:
        anon = edge.anonymous()
        with pytest.raises(EdgeApiError) as denied:
            anon.request("POST", "/v1/live/commands/safe", {})
        assert denied.value.status == 401


def test_mutating_calls_need_the_current_contract_hash() -> None:
    with edge_server() as edge:
        op = edge.operator()
        with pytest.raises(EdgeApiError) as stale:
            op.request("POST", "/v1/live/commands/safe", {}, contract=False)
        assert stale.value.status == 409
        assert stale.value.code == "stale_contract"
        assert stale.value.payload["expected_contract_hash"] == edge.node.contract_hash
        with pytest.raises(EdgeApiError) as wrong:
            op.request("POST", "/v1/live/commands/safe", {"contract_hash": "0" * 64}, contract=False)
        assert wrong.value.status == 409
        # correct hash in body works too
        result = op.request(
            "POST", "/v1/live/commands/safe", {"contract_hash": edge.node.contract_hash}, contract=False
        )
        assert result["guardrail"]["reason"] == "operator_safe"


def test_operator_reset_then_permit_energises_output_and_records_csv() -> None:
    with edge_server() as edge:
        op = edge.operator()
        op.start_recording("contract-run")
        reset = op.command("reset")
        assert reset["guardrail"]["event"] == "trip_reset_output_safe"
        permit = op.command("permit")
        assert permit["guardrail"]["event"] == "permit_accepted"
        assert permit["outputs"]["gpio23_command_high"] is True
        assert edge.rig.output is True
        safe = op.command("safe")
        assert safe["outputs"]["gpio23_command_high"] is False
        stopped = op.stop_recording()
        assert stopped["completed_recording"]["samples"] >= 3
        assert len(stopped["completed_recording"]["sha256"]) == 64
        csv_bytes = op.latest_csv()
        assert csv_bytes.splitlines()[0].startswith(b"sample_index,timestamp_utc")


def test_agent_never_tools_are_refused_even_with_a_valid_key() -> None:
    with edge_server() as edge:
        agent = edge.agent()
        agent.refresh_contract()
        # ack_operator_step is 'never' for the agent on wave1
        with pytest.raises(EdgeApiError) as denied:
            agent.post("/v1/procedure_runs/run_x/ack", {"run_id": "run_x", "step_id": "s1"})
        assert denied.value.status in {403, 404}
        if denied.value.status == 403:
            assert denied.value.payload["policy"] == "never"
        # requesting approval for a never tool is also refused
        with pytest.raises(EdgeApiError) as never:
            agent.request_approval("bypass_interlock", {}, "trying it on")
        assert never.value.status == 403
        audit = edge.operator().get("/v1/audit")["audit"]
        assert any(row["tool"] == "bypass_interlock" or row["path"].endswith("/request") for row in audit)


def test_agent_human_approval_flow_end_to_end() -> None:
    with edge_server() as edge:
        agent = edge.agent()
        op = edge.operator("chintan")
        agent.refresh_contract()

        # 1. agent tries without approval
        with pytest.raises(EdgeApiError) as needs:
            agent.command("reset")
        assert needs.value.status == 428
        assert needs.value.code == "approval_required"

        # 2. agent requests, operator sees it pending
        request = agent.request_approval("reset_trip", {}, "trip cause understood: startup latch")
        assert request["status"] == "pending"
        pending = op.approvals("pending")
        assert [row["approval_id"] for row in pending] == [request["approval_id"]]

        # 3. agent cannot grant its own request
        with pytest.raises(EdgeApiError) as self_grant:
            agent.grant(request["approval_id"])
        assert self_grant.value.status == 403

        # 4. operator grants, agent proceeds
        granted = op.grant(request["approval_id"])
        assert granted["status"] == "granted" and granted["decided_by"] == "chintan"
        result = agent.command("reset", approval_id=request["approval_id"])
        assert result["guardrail"]["event"] == "trip_reset_output_safe"

        # 5. single use
        with pytest.raises(EdgeApiError) as reused:
            agent.command("reset", approval_id=request["approval_id"])
        assert reused.value.status == 403 and reused.value.code == "approval_invalid"

        # 6. approval bound to tool: passing it to an 'allowed' tool neither consumes nor is needed
        other = agent.request_approval("reset_trip", {}, "second")
        op.grant(other["approval_id"])
        agent.command("safe", approval_id=other["approval_id"])
        assert op.get(f"/v1/approvals/{other['approval_id']}")["status"] == "granted"
        # and binding to args: an approval for {} cannot authorise different arguments
        with pytest.raises(EdgeApiError) as wrong_args:
            agent.post("/v1/live/commands/reset", {"approval_id": other["approval_id"], "extra": 1})
        assert wrong_args.value.status == 403 and "different arguments" in wrong_args.value.payload["error"]
        assert agent.command("reset", approval_id=other["approval_id"])["guardrail"]["event"] in {
            "trip_reset_output_safe",
            "reset_rejected_process_unsafe",
        }

        # 7. denied approvals cannot be used
        denied = agent.request_approval("reset_trip", {}, "third")
        op.deny(denied["approval_id"])
        with pytest.raises(EdgeApiError) as used_denied:
            agent.command("reset", approval_id=denied["approval_id"])
        assert used_denied.value.status == 403

        audit = op.get("/v1/audit")["audit"]
        agent_rows = [row for row in audit if row["principal"] == "agent"]
        assert any(row["status"] == 428 for row in agent_rows)
        assert any(
            row["status"] == 200 and row["approval_id"] == request["approval_id"] for row in agent_rows
        )


def test_agent_allowed_and_controller_tools() -> None:
    with edge_server() as edge:
        agent = edge.agent()
        agent.refresh_contract()
        # allowed: force_safe, recording
        assert agent.command("safe")["guardrail"]["reason"] == "operator_safe"
        started = agent.start_recording("agent-run")
        assert started["recording"]["active"] is True
        # controller_approval: permit is decided by the kernel, which refuses without reset
        refused = agent.command("permit")
        assert refused["guardrail"]["event"] == "permit_rejected_reset_required"
        assert refused["outputs"]["gpio23_command_high"] is False
        stopped = agent.stop_recording()
        assert stopped["completed_recording"]["samples"] >= 1


def test_read_only_manifest_when_no_capabilities_file() -> None:
    with edge_server(capabilities_name=None) as edge:
        agent = edge.agent()
        agent.refresh_contract()
        with pytest.raises(EdgeApiError) as denied:
            agent.command("safe")
        assert denied.value.status == 403
        assert edge.operator().command("safe")["guardrail"]["reason"] == "operator_safe"


def test_node_without_agent_key_treats_agent_header_as_anonymous() -> None:
    with edge_server(agent_key=None) as edge:
        agent = edge.agent()
        with pytest.raises(EdgeApiError) as denied:
            agent.request("POST", "/v1/live/commands/safe", {}, contract=False)
        assert denied.value.status == 401
