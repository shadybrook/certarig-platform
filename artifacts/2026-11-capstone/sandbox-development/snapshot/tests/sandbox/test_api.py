from __future__ import annotations

import shutil

import pytest

from certarig.agent.skills import SkillIndex
from certarig.agent.tools import ToolRegistry
from certarig.edge.bootstrap import NodeSettings, build_node
from certarig.edge.client import EdgeApiError, InProcessClient
from certarig.edge.openapi import generate_openapi
from certarig.edge.server import make_edge_server
from certarig.sandbox.broker import Broker
from tests.sandbox.test_broker import FakeEngine, wait_job
from tests.support import AGENT_KEY, AUDITOR_KEY, CONFIG_DIR, OPERATOR_KEY, SKILLS_DIR


@pytest.fixture
def node_fixture(tmp_path):  # type: ignore[no-untyped-def]
    path = tmp_path / "rig.json"
    shutil.copy2(CONFIG_DIR / "rig.thermal.capstone.json", path)
    settings = NodeSettings(
        path,
        CONFIG_DIR / "capabilities.sandbox.json",
        tmp_path / "evidence",
        None,
        OPERATOR_KEY,
        AGENT_KEY,
        AUDITOR_KEY,
        True,
        SKILLS_DIR,
    )
    node = build_node(settings)
    broker = Broker(tmp_path / "broker", FakeEngine())
    node.extensions["sandboxes"].client = broker
    op = InProcessClient(node, operator_key=OPERATOR_KEY, principal_name="operator")
    agent = InProcessClient(node, agent_key=AGENT_KEY, principal_name="alice")
    yield node, op, agent, broker
    node.close()
    broker.close()


def test_api_workspace_and_permissions(node_fixture):  # type: ignore[no-untyped-def]
    node, op, agent, b = node_fixture
    assert op.sandbox_preflight()["ready"]
    w = agent.create_sandbox()
    sid = w["sandbox_id"]
    assert agent.sandbox(sid)["authority"] == "none"
    assert op.get("/v1/sandboxes")["workspaces"]
    for source in ["thermal", "pressure_flow"]:
        assert agent.create_sandbox(source)["snapshot"]["provenance"]["calibration_kind"].startswith(
            "deterministic_fixture"
        )
    for payload in [{"source": "unsupported"}, {"procedure_id": "not-a-procedure"}]:
        with pytest.raises(EdgeApiError):
            agent.post("/v1/sandboxes", payload)
    anonymous = InProcessClient(node)
    for url in ["/v1/sandboxes", "/v1/sandboxes/preflight", f"/v1/sandboxes/{sid}"]:
        with pytest.raises(EdgeApiError) as exc:
            anonymous.get(url)
        assert exc.value.status == 401
    audit = InProcessClient(node)
    audit.auditor_key = AUDITOR_KEY
    assert audit.get(f"/v1/sandboxes/{sid}")
    with pytest.raises(EdgeApiError) as exc:
        audit.post("/v1/sandboxes", {})
    assert exc.value.status == 403
    with pytest.raises(EdgeApiError) as exc:
        agent.post(
            "/v1/rig/apply",
            {"document": w["snapshot"]["document"], "expected_current_hash": node.config.config_hash},
        )
    assert exc.value.status == 403
    with pytest.raises(EdgeApiError):
        agent.post(f"/v1/sandboxes/{sid}/jobs", {"kind": "python", "source": "not executed", "mounts": ["/"]})
    job = agent.run_sandbox(sid, "python", "not executed")
    wait_job(b, sid)
    assert agent.get(f"/v1/sandboxes/{sid}/jobs/{job['job_id']}")["status"] == "completed"
    assert agent.request("GET", f"/v1/sandboxes/{sid}/jobs/{job['job_id']}/artifacts/analysis.json", raw=True)
    assert agent.request("GET", f"/v1/sandboxes/{sid}/export", raw=True).startswith(b"PK")
    assert (
        agent.post(
            f"/v1/sandboxes/{sid}/revisions", {"expected_revision": 0, "document": w["snapshot"]["document"]}
        )["revision"]
        == 1
    )
    with pytest.raises(EdgeApiError):
        agent.post(f"/v1/sandboxes/{sid}/proposals", {"job_id": job["job_id"]})
    with pytest.raises(EdgeApiError):
        agent.get(f"/v1/sandboxes/{sid}/jobs/job_missing")
    agent.request("DELETE", f"/v1/sandboxes/{sid}", {})
    assert op.sandbox(sid)["status"] == "closed"
    node.flags["sandbox_local_only"] = True
    with pytest.raises(ValueError, match="loopback"):
        make_edge_server(node, "0.0.0.0")
    assert "/v1/sandboxes" in generate_openapi(node)["paths"]


def test_agent_registry(node_fixture):  # type: ignore[no-untyped-def]
    node, op, agent, b = node_fixture
    registry = ToolRegistry(agent, SkillIndex.load(SKILLS_DIR))
    result = registry.execute("sandbox_experiment", {"action": "create", "source": "thermal"})
    assert result.ok, result.result
    sid = result.result["sandbox_id"]
    assert registry.execute("read_sandbox", {"sandbox_id": sid}).ok
    assert registry.execute(
        "sandbox_experiment", {"action": "run", "sandbox_id": sid, "kind": "python", "source": "not executed"}
    ).ok
    wait_job(b, sid)
    assert registry.execute("sandbox_experiment", {"action": "close", "sandbox_id": sid}).ok
    before = node.config.config_hash
    assert not registry.execute("sandbox_experiment", {"action": "apply", "sandbox_id": sid}).ok
    assert node.config.config_hash == before


def test_disabled_and_unavailable(node_fixture, tmp_path):  # type: ignore[no-untyped-def]
    node, op, agent, b = node_fixture
    service = node.extensions["sandboxes"]
    service.client = None
    assert not op.sandbox_preflight()["enabled"]
    with pytest.raises(EdgeApiError) as exc:
        op.create_sandbox()
    assert exc.value.status == 503
    from certarig.sandbox.transport import BrokerClient

    service.client = BrokerClient(tmp_path / "no-such-socket")
    assert not op.sandbox_preflight()["ready"]


def test_operator_review_handoff_and_recording_continues(node_fixture, rehearsal_files):  # type: ignore[no-untyped-def]
    import time

    node, op, agent, b = node_fixture
    b.engine.output = rehearsal_files
    w = agent.create_sandbox()
    sid = w["sandbox_id"]
    job = agent.run_sandbox(sid, "rehearsal")
    wait_job(b, sid)
    proposal = agent.propose_sandbox(sid, job["job_id"])
    reference = {"sandbox_id": sid, "sandbox_proposal_id": proposal["proposal_id"]}
    with pytest.raises(EdgeApiError):
        op.post(
            "/v1/rig/apply", {**reference, "document": {}, "expected_current_hash": node.config.config_hash}
        )
    assert op.post(
        "/v1/rig/apply",
        {**reference, "document": proposal["document"], "expected_current_hash": node.config.config_hash},
    )
    assert not node.approvals.list("granted")
    node.start()
    op.start_recording("independent-sampling")
    assert not op.sandbox_preflight().get("physical_qualified", False)
    w = agent.create_sandbox("thermal")
    sid = w["sandbox_id"]
    b.engine.hold = True
    agent.run_sandbox(sid, "python", "never executed on host")
    assert __import__("tests.support", fromlist=["wait_until"]).wait_until(
        lambda: agent.sandbox(sid)["jobs"][0]["status"] == "running"
    )
    before = node.runtime.state()["sample_index"]
    agent.close_sandbox(sid)
    wait_job(b, sid)
    time.sleep(0.1)
    assert node.runtime.state()["recording"]["active"] and node.runtime.state()["sample_index"] > before
    with pytest.raises(EdgeApiError):
        op.post("/v1/sandboxes", {"recording_id": "latest"})
    op.stop_recording()
    copied = op.post("/v1/sandboxes", {"recording_id": "latest"})
    assert copied["recording"]["bytes"] > 0
