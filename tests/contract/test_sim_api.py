from __future__ import annotations

import tempfile
import threading
from pathlib import Path

import pytest

from certarig.edge.bootstrap import NodeSettings, build_node
from certarig.edge.client import EdgeApiError, EdgeClient
from certarig.edge.server import make_edge_server
from tests.support import AGENT_KEY, CONFIG_DIR, OPERATOR_KEY, SKILLS_DIR, wait_until


def test_simulator_routes_are_operator_only_and_drive_the_plant() -> None:
    with tempfile.TemporaryDirectory() as temp:
        node = build_node(
            NodeSettings(
                config_path=CONFIG_DIR / "rig.sim.json",
                capabilities_path=CONFIG_DIR / "capabilities.wave1.json",
                evidence_dir=Path(temp),
                static_root=None,
                operator_key=OPERATOR_KEY,
                agent_key=AGENT_KEY,
                allow_output=True,
                skills_root=SKILLS_DIR,
            )
        )
        assert "simulator" in node.extensions
        server = make_edge_server(node)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        node.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            op = EdgeClient(url, operator_key=OPERATOR_KEY)
            agent = EdgeClient(url, agent_key=AGENT_KEY)
            agent.refresh_contract()
            assert op.health()["hardware_mode"] == "simulator"
            assert "simulator" in op.health()["extensions"]
            state = op.get("/v1/sim/state")
            assert state["seed"] == 7 and state["estop_pressed"] is False
            with pytest.raises(EdgeApiError) as denied:
                agent.post("/v1/sim/set_target", {"channel": "pressure", "value": 5.0})
            assert denied.value.status == 403
            op.post("/v1/sim/set_target", {"channel": "pressure", "value": 5.0})
            assert wait_until(lambda: op.state()["samples"][0]["value"] > 4.5)
            assert op.state()["guardrail"]["reason"] == "pressure_high"
            op.post("/v1/sim/ramp", {"channel": "pressure", "to": 2.0, "over_s": 0.1})
            assert wait_until(lambda: op.state()["guardrail"]["reason"] == "reset_required")
            op.post("/v1/sim/estop", {"pressed": True})
            assert wait_until(lambda: op.state()["guardrail"]["estop_active"] is True)
            op.post("/v1/sim/estop", {"pressed": False})
            assert wait_until(lambda: op.state()["guardrail"]["estop_active"] is False)
            faulted = op.post("/v1/sim/fault", {"kind": "dropout", "channel": "flow"})
            assert faulted["faults"]["channels"]["flow_emulator"] == {"dropout": {}}
            assert wait_until(lambda: op.state()["guardrail"]["reason"] == "flow_invalid")
            cleared = op.post("/v1/sim/clear", {})
            assert cleared["faults"] == {"global": {}, "channels": {}}
            with pytest.raises(EdgeApiError) as bad:
                op.post("/v1/sim/fault", {})
            assert bad.value.status == 400
            with pytest.raises(EdgeApiError) as unknown:
                op.post("/v1/sim/set_target", {"channel": "chamber", "value": 1})
            assert unknown.value.status == 400
            with pytest.raises(EdgeApiError) as bad_params:
                op.post("/v1/sim/fault", {"kind": "stuck", "params": []})
            assert bad_params.value.status == 400
        finally:
            server.shutdown()
            server.server_close()
            node.close()
