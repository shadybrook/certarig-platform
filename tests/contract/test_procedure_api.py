from __future__ import annotations

import pytest

from certarig.edge.client import EdgeApiError
from tests.support import edge_server, wait_until


def test_procedure_catalogue_and_detail() -> None:
    with edge_server() as edge:
        anon = edge.anonymous()
        listing = anon.procedures()
        ids = {row["id"] for row in listing["procedures"]}
        assert {"pressure_guardrail", "relay_truth_table", "safe_powerdown"} <= ids
        assert listing["skipped"] == []
        detail = anon.get("/v1/procedures/relay_truth_table")
        assert detail["procedure"]["steps"][0]["id"] == "boot_safe"
        with pytest.raises(EdgeApiError) as missing:
            anon.get("/v1/procedures/nope")
        assert missing.value.status == 404


def test_validate_endpoint_requires_auth_and_reports_errors() -> None:
    with edge_server() as edge:
        with pytest.raises(EdgeApiError) as anon:
            edge.anonymous().request("POST", "/v1/procedures/validate", {"procedure": {}}, contract=False)
        assert anon.value.status == 401
        op = edge.operator()
        bad = op.request("POST", "/v1/procedures/validate", {"procedure": {"id": "x"}}, contract=False)
        assert bad["valid"] is False and bad["errors"]
        good = op.request(
            "POST",
            "/v1/procedures/validate",
            {
                "procedure": {
                    "id": "tiny",
                    "version": 1,
                    "title": "tiny procedure",
                    "record": False,
                    "steps": [{"id": "safe", "type": "command", "command": "safe"}],
                }
            },
            contract=False,
        )
        assert good["valid"] is True and len(good["procedure_hash"]) == 64


def test_agent_drafts_engineer_approves_then_it_can_run() -> None:
    with edge_server(start_loop=True) as edge:
        agent = edge.agent()
        agent.refresh_contract()
        raw = {
            "id": "agent_drafted",
            "version": 1,
            "title": "Agent drafted safe check",
            "record": False,
            "steps": [
                {
                    "id": "safe",
                    "type": "command",
                    "command": "safe",
                    "expect": {"state": "output_high", "eq": False},
                }
            ],
        }
        with pytest.raises(EdgeApiError) as invalid:
            agent.post("/v1/procedures/drafts", {"procedure": {"id": "bad"}})
        assert invalid.value.status == 422 and invalid.value.payload["errors"]
        draft = agent.post("/v1/procedures/drafts", {"procedure": raw})
        assert draft["approved"] is False
        # cannot run an unapproved draft
        with pytest.raises(EdgeApiError) as not_runnable:
            agent.run_procedure("agent_drafted")
        assert not_runnable.value.status == 404
        # agent cannot approve
        with pytest.raises(EdgeApiError) as self_approve:
            agent.post(f"/v1/procedures/drafts/{draft['procedure_hash']}/approve", {})
        assert self_approve.value.status == 403
        op = edge.operator("engineer")
        assert op.get("/v1/procedures/drafts")["drafts"][0]["id"] == "agent_drafted"
        assert (
            op.get(f"/v1/procedures/drafts/{draft['procedure_hash']}")["procedure"]["id"] == "agent_drafted"
        )
        approved = op.post(f"/v1/procedures/drafts/{draft['procedure_hash']}/approve", {})
        assert approved["approved"] is True and approved["source"] == "approved:engineer"
        run = agent.run_procedure("agent_drafted", "drafted-run")
        assert run["status"] in {"pending", "preflight", "running", "passed"}
        assert wait_until(lambda: agent.procedure_run(run["run_id"])["terminal"])
        final = agent.procedure_run(run["run_id"])
        assert final["status"] == "passed"
        assert final["requested_by"] == "agent-under-test"
        with pytest.raises(EdgeApiError) as gone:
            op.post(f"/v1/procedures/drafts/{draft['procedure_hash']}/reject", {})
        assert gone.value.status == 404


def test_operator_runs_powerdown_and_acks_agent_cannot_ack() -> None:
    with edge_server(start_loop=True) as edge:
        op = edge.operator("chintan")
        agent = edge.agent()
        agent.refresh_contract()
        run = op.run_procedure("safe_powerdown")
        run_id = run["run_id"]
        assert wait_until(lambda: op.procedure_run(run_id)["status"] == "awaiting_operator")
        awaiting = op.procedure_run(run_id)
        assert awaiting["current_step"] == "confirm_bench"
        # a second run is refused while one is active
        with pytest.raises(EdgeApiError) as busy:
            op.run_procedure("relay_truth_table")
        assert busy.value.status == 409
        # the agent is 'never' allowed to acknowledge physical steps
        with pytest.raises(EdgeApiError) as denied:
            agent.ack(run_id, "confirm_bench")
        assert denied.value.status == 403 and denied.value.payload["policy"] == "never"
        # wrong step id is a conflict
        with pytest.raises(EdgeApiError) as wrong:
            op.ack(run_id, "final_safe")
        assert wrong.value.status == 409
        acked = op.ack(run_id, "confirm_bench")
        assert acked["run_id"] == run_id
        assert wait_until(lambda: op.procedure_run(run_id)["terminal"])
        final = op.procedure_run(run_id)
        assert final["status"] == "passed"
        step = next(s for s in final["steps"] if s["step_id"] == "confirm_bench")
        assert step["detail"]["acknowledged_by"] == "chintan"
        assert op.get("/v1/procedure_runs")["runs"][0]["status"] == "passed"
        with pytest.raises(EdgeApiError) as missing:
            op.procedure_run("run_missing")
        assert missing.value.status == 404
        with pytest.raises(EdgeApiError) as ack_missing:
            op.ack("run_missing", "x")
        assert ack_missing.value.status == 404


def test_agent_can_abort_its_run() -> None:
    with edge_server(start_loop=True) as edge:
        agent = edge.agent()
        agent.refresh_contract()
        run = agent.run_procedure("pressure_guardrail")
        run_id = run["run_id"]
        assert wait_until(lambda: agent.procedure_run(run_id)["current_step"] == "raise_pressure")
        assert edge.rig.output is True
        aborted = agent.abort(run_id, "simulated operator request")
        assert aborted["run_id"] == run_id
        assert wait_until(lambda: agent.procedure_run(run_id)["terminal"])
        final = agent.procedure_run(run_id)
        assert final["status"] == "aborted" and "simulated operator request" in final["outcome_reason"]
        assert edge.rig.output is False
        with pytest.raises(EdgeApiError) as again:
            agent.abort(run_id)
        assert again.value.status == 409
        with pytest.raises(EdgeApiError) as missing:
            agent.abort("run_missing")
        assert missing.value.status == 404
        audit = edge.operator().get("/v1/audit")["audit"]
        assert any(row["tool"] == "run_procedure" and row["status"] == 201 for row in audit)
        assert any(row["tool"] == "abort_procedure" and row["status"] == 200 for row in audit)
