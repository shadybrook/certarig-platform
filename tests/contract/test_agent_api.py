from __future__ import annotations

import pytest

from certarig.edge.client import EdgeApiError, EdgeClient, InProcessClient
from tests.support import sim_server


def test_in_process_client_and_studio_agent_chat() -> None:
    with sim_server() as sim:
        local = InProcessClient(sim.node, agent_key=sim.agent().agent_key, principal_name="local")
        local.refresh_contract()
        assert "samples" in local.state()
        operator = sim.operator()
        with pytest.raises(EdgeApiError) as exc:
            operator.post("/v1/agent/chat", {})
        assert exc.value.status == 400

        first = operator.post("/v1/agent/chat", {"text": "what is the rig status?"})
        assert first["session_id"].startswith("ses_")
        assert first["tool_calls"][0]["name"] == "read_state"

        second = operator.post(
            "/v1/agent/chat", {"text": "run the relay truth table", "session_id": first["session_id"]}
        )
        assert second["session_id"] == first["session_id"]
        assert any(c["name"] == "run_procedure" and c["ok"] for c in second["tool_calls"])
        assert "PASSED" in second["text"]

        summary = operator.get(f"/v1/agent/sessions/{first['session_id']}")
        assert summary["user_turns"] == 2
        assert "run_procedure" in summary["tools_used"]

        with pytest.raises(EdgeApiError) as denied:
            sim.agent().post("/v1/agent/chat", {"text": "hi"})
        assert denied.value.status == 403


def test_anonymous_cannot_chat() -> None:
    with sim_server() as sim:
        with pytest.raises(EdgeApiError) as exc:
            EdgeClient(sim.url).post("/v1/agent/chat", {"text": "hi"})
        assert exc.value.status == 401
