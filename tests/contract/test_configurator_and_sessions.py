"""Configurator writes, sessions, auditor, ledger, ready-to-arm."""

from __future__ import annotations

import json

import pytest

from certarig.edge.client import EdgeApiError, EdgeClient
from certarig.sdk import CertaRig
from tests.support import AUDITOR_KEY, OPERATOR_KEY, edge_server


def test_health_exposes_ready_to_arm_and_error_catalog() -> None:
    with edge_server() as edge:
        health = edge.anonymous().health()
        assert "ready_to_arm" in health
        assert health["agent_provider"] == "fake"
        assert health["ready_to_arm"]["observe_only"] is False
        catalog = edge.anonymous().get("/v1/errors")
        assert "stale_contract" in catalog["errors"]
        assert catalog["errors"]["twin_gate"]["next"]


def test_rig_propose_and_apply_hot_reloads_limits() -> None:
    with edge_server() as edge:
        client = edge.operator()
        current = client.rig()
        document = json.loads(json.dumps(current["document"]))
        document["abort_limits"] = {"pressure": 4.1}
        document.pop("pressure_abort_bar", None)
        preview = client.post("/v1/rig/propose", {"document": document})
        assert preview["restart_required"] is False
        assert preview["diff"]
        applied = client.post(
            "/v1/rig/apply",
            {"document": document, "expected_current_hash": preview["current_hash"]},
        )
        assert applied["next_hash"] == edge.node.config.config_hash
        assert edge.node.config.abort_limits["pressure"] == 4.1


def test_hardware_mode_change_requires_restart() -> None:
    with edge_server() as edge:
        client = edge.operator()
        document = dict(client.rig()["document"])
        document["hardware"] = {**document["hardware"], "mode": "mqtt", "observe_only": True}
        preview = client.post("/v1/rig/propose", {"document": document})
        assert preview["restart_required"] is True
        with pytest.raises(EdgeApiError) as err:
            client.post(
                "/v1/rig/apply",
                {"document": document, "expected_current_hash": preview["current_hash"]},
            )
        assert err.value.status == 409
        assert err.value.code == "restart_required"
        assert err.value.payload.get("title")


def test_session_token_and_auditor_are_read_only() -> None:
    with edge_server() as edge:
        minted = edge.anonymous().post(
            "/v1/auth/session",
            {"operator_key": OPERATOR_KEY, "name": "session-op"},
        )
        session = EdgeClient(edge.url, session_token=minted["token"])
        assert session.health()["status"] == "ok"
        auditor = edge.auditor()
        assert auditor.health()["status"] == "ok"
        assert auditor.evidence()["runs"] == [] or "runs" in auditor.evidence()
        with pytest.raises(EdgeApiError) as err:
            auditor.command("safe")
        assert err.value.status == 403
        assert err.value.code == "observe_only"


def test_ledger_records_a_finished_run() -> None:
    with edge_server(start_loop=True) as edge:
        client = edge.operator()
        run = client.run_procedure("relay_truth_table")
        from tests.support import wait_until

        wait_until(lambda: client.procedure_run(run["run_id"])["terminal"], timeout=20)
        rows = client.get("/v1/ledger")["outcomes"]
        assert any(row["procedure_id"] == "relay_truth_table" for row in rows)


def test_sdk_happy_path_health_and_live() -> None:
    with edge_server() as edge:
        sdk = CertaRig(edge.url, OPERATOR_KEY)
        assert sdk.health()["ready_to_arm"]["contract_hash"]
        assert "guardrail" in sdk.live()


def test_auditor_key_header_is_not_the_demo_secret() -> None:
    assert AUDITOR_KEY.startswith("test-")
