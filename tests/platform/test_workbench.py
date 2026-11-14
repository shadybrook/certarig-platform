"""Workbench acceptance with explicit provider/engine doubles, never container qualification."""

import copy
import io
import json
import time
import zipfile
from pathlib import Path

import pytest

from certarig.platform import evaluation, evidence, teams
from certarig.platform.analysis import Analysis
from certarig.platform.connectors import ConnectorProfiles
from certarig.platform.contracts import verify_trace
from certarig.platform.evaluation import FixtureProvider
from certarig.platform.server import API
from certarig.platform.tasks import Tasks
from certarig.platform.workbench import Workbench
from tests.platform.test_lifecycle import Engine, qualified


def wait(check, seconds=4):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.01)
    pytest.fail("Bounded test condition timed out")


def test_resumable_drafts_scope_conflicts_and_commit(lab):
    w = Workbench(lab.p)
    p = w.project(lab.author, {"name": "Lab", "asset_ids": [lab.a["id"]]})
    assert w.listing(lab.reviewer, "project")[0]["asset_ids"] == [lab.a["id"]]
    with pytest.raises(KeyError):
        w.project(lab.author, {"name": "No", "asset_ids": [lab.b["id"]]})
    with pytest.raises(ValueError):
        w.project(lab.author, {"name": "No", "asset_ids": []})
    d = w.draft(lab.author, {"asset_id": lab.a["id"], "project_id": p["id"], "goal": "Check temperature"})
    assert w.inspect(lab.author, d["id"])["blockers"]
    with pytest.raises(PermissionError):
        w.update(lab.reviewer, d["id"], {"expected_revision": 1})
    assert not w.listing(lab.outsider, "draft")
    with pytest.raises(KeyError):
        w.inspect(lab.outsider, d["id"])
    d = w.update(
        lab.author,
        d["id"],
        {"expected_revision": 1, "definition": lab.body, "message": "Explain stale readings"},
    )
    assert d["revision"] == 2 and "stale readings" in d["definition"]["instructions"]
    with pytest.raises(ValueError, match="changed"):
        w.update(lab.author, d["id"], {"expected_revision": 1, "definition": lab.body})
    w2 = Workbench(lab.p)
    assert len(w2.inspect(lab.author, d["id"])["messages"]) == 4
    version = w.commit(lab.author, d["id"], 2)
    assert w.inspect(lab.author, d["id"])["status"] == "committed"
    with pytest.raises(ValueError):
        w.commit(lab.author, d["id"], 2)
    e = evaluation.collect(lab.p, lab.author, version, lambda c: FixtureProvider())
    e = evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    d = lab.p.review(lab.reviewer, version["id"], e["id"])
    bundle = evidence.export(lab.p, lab.reviewer, d["id"])
    assert evidence.verify(bundle)["format"] == "certarig-agent-evidence/2"
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        files = {n: archive.read(n) for n in archive.namelist()}
    files.pop("workspace.json")
    damaged = io.BytesIO()
    with zipfile.ZipFile(damaged, "w") as archive:
        for n, b in files.items():
            archive.writestr(n, b)
    with pytest.raises(ValueError):
        evidence.verify(damaged.getvalue())


@pytest.mark.parametrize("body", [{"template": "unknown"}, {"extra": True}])
def test_draft_bad_inputs(lab, body):
    with pytest.raises(ValueError):
        Workbench(lab.p).draft(lab.author, {"asset_id": lab.a["id"], **body})


def test_tasks_progress_cancellation_restart_and_permissions(lab):
    tasks = Tasks(lab.p, lambda c: FixtureProvider(), lab.broker)
    try:
        t = tasks.submit(lab.author, {"kind": "evaluate", "target_id": lab.v["id"]})
        done = wait(
            lambda: v if (v := tasks.get(lab.author, t["id"]))["status"] in {"completed", "failed"} else None
        )
        assert done["status"] == "completed"
        events = tasks.events(lab.author, t["id"])
        assert len([e for e in events["events"] if e["event"] == "case_completed"]) == 5
        assert tasks.events(lab.author, t["id"], events["cursor"])["events"] == []
        q = tasks.submit(lab.author, {"kind": "qualify", "target_id": done["result_id"]})
        wait(lambda: tasks.get(lab.author, q["id"])["status"] == "completed")
        assert tasks.cancel(lab.author, t["id"])["status"] == "completed"
        with pytest.raises(KeyError):
            tasks.get(lab.outsider, t["id"])
        with pytest.raises(PermissionError):
            tasks.submit(lab.reviewer, {"kind": "evaluate", "target_id": lab.v["id"]})
        with pytest.raises(ValueError):
            tasks.events(lab.author, t["id"], -1)
        tasks.slot.acquire()
        pending = tasks.submit(lab.author, {"kind": "evaluate", "target_id": lab.v["id"]})
        assert tasks.cancel(lab.author, pending["id"])["status"] == "cancelled"
        tasks.slot.release()
        wait(lambda: not any(w.is_alive() for w in tasks.workers))
        assert tasks.get(lab.author, pending["id"])["status"] == "cancelled"
        interrupted = {**pending, "id": "tsk_saved", "status": "running"}
        lab.store.put("task", interrupted)
        restarted = Tasks(lab.p, lambda c: FixtureProvider(), lab.broker)
        assert restarted.get(lab.author, "tsk_saved")["status"] == "interrupted"
        restarted.close()
        assert len(tasks.listing(lab.author)) == 4
    finally:
        tasks.close()


def make_team(lab):
    qualified(lab)
    second = lab.p.create_version(lab.author, {**lab.body, "name": "Specialist"})
    ev = evaluation.collect(lab.p, lab.author, second, lambda c: FixtureProvider())
    evaluation.qualify(lab.p, lab.author, ev["id"], lab.broker)
    return teams.create(
        lab.p,
        lab.author,
        {"name": "Commissioning team", "supervisor_id": lab.v["id"], "specialist_ids": [second["id"]]},
    )


def test_team_real_delegation_binding_review_runtime_and_export(lab):
    team = make_team(lab)
    e = evaluation.collect(lab.p, lab.author, team, lambda c: FixtureProvider())
    assert e["status"] == "awaiting_sandbox", e.get("error")
    assert e["local_check"]["passed"]
    assert all(len(c["delegations"]) == 1 for c in e["trace"]["cases"].values())
    e = evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    with pytest.raises(PermissionError):
        lab.p.review(lab.author, team["id"], e["id"])
    d = lab.p.review(lab.reviewer, team["id"], e["id"])
    d = lab.p.start(lab.reviewer, d["id"])
    lab.runtime.tick(d["id"])
    current = lab.p.deployment(lab.author, d["id"])
    assert current["assessments"] == 1, current.get("reason")
    assert current["observations"][0]["team"]["model_calls"] <= 8
    bundle = evidence.export(lab.p, lab.reviewer, d["id"])
    assert evidence.verify(bundle)["members"] == 2
    trace = copy.deepcopy(e["trace"])
    trace["cases"]["nominal"]["delegations"][0]["version_id"] = "unreviewed"
    with pytest.raises(ValueError):
        verify_trace(trace)
    lab.p.disconnect(lab.author, lab.c["id"])
    lab.runtime.sweep()
    assert lab.p.deployment(lab.author, d["id"])["status"] == "paused"


def test_team_requires_evaluated_distinct_non_recursive_versions(lab):
    with pytest.raises(ValueError):
        teams.create(
            lab.p, lab.author, {"name": "x", "supervisor_id": lab.v["id"], "specialist_ids": [lab.v["id"]]}
        )
    v = lab.p.create_version(lab.author, {**lab.body, "name": "Second"})
    with pytest.raises(ValueError, match="evaluation"):
        teams.create(
            lab.p, lab.author, {"name": "x", "supervisor_id": lab.v["id"], "specialist_ids": [v["id"]]}
        )
    team = make_team(lab)
    with pytest.raises(PermissionError):
        teams.create(
            lab.p, lab.author, {"name": "x", "supervisor_id": team["id"], "specialist_ids": [v["id"]]}
        )


class AnalysisEngine(Engine):
    def preflight(self):
        return {**super().preflight(), "runner_image": self.image}

    def run(self, job, kind, inputs, seconds, cancel):
        if kind == "agent_evaluation":
            return super().run(job, kind, inputs, seconds, cancel)
        # Explicit double: submitted code is not executed on the host.
        params = json.loads(inputs["parameters.json"])
        return {
            "status": "completed",
            "files": {"result.json": json.dumps(params["inputs"]).encode(), "log.txt": b"fixture only"},
            "resource": {"fixture": True},
        }


def analysis_lab(lab):
    lab.broker.engine = AnalysisEngine()
    original = lab.p.client_factory

    class FullClient(original):
        def rig(self):
            result = super().rig()
            result["rig"] = json.loads(Path("config/rig.thermal.sim.json").read_text())
            return result

    lab.p.client_factory = FullClient
    return Analysis(lab.p, lab.broker)


def tool_body(lab):
    return {
        "name": "Echo fixture",
        "asset_id": lab.a["id"],
        "kind": "python",
        "source": "# inert test source",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "dependencies": [],
        "tests": [{"inputs": {"n": 1}, "expected": {"n": 1}}],
    }


def test_analysis_requires_exact_tests_independent_review_scoped_artifacts(lab):
    service = analysis_lab(lab)
    tool = service.create(lab.author, tool_body(lab))
    with pytest.raises(PermissionError):
        service.run(lab.author, tool["id"], {})
    test = service.test(lab.author, tool["id"])
    identifier = test["analyses"][0]
    wait(lambda: service.inspect(lab.author, identifier)["status"] == "completed")
    with pytest.raises(PermissionError):
        service.review(lab.author, tool["id"], test["id"])
    reviewed = service.review(lab.reviewer, tool["id"], test["id"])
    assert reviewed["reviewed_image"] == lab.broker.engine.image
    assert service.artifact(lab.author, identifier, "log.txt")["data"]
    with pytest.raises(KeyError):
        service.artifact(lab.outsider, identifier, "log.txt")
    with pytest.raises(ValueError):
        service.artifact(lab.author, identifier, "../result.json")
    run = service.run(lab.author, tool["id"], {})
    wait(lambda: service.inspect(lab.author, run["id"])["status"] == "completed")
    assert service.cancel(lab.author, run["id"])["status"] == "cancelled"
    assert len(service.listing(lab.author, "analysis_tool")) == 1
    assert not service.listing(lab.outsider, "analysis_tool")
    csv = "channel_id,value,unit,captured_at,quality\ntemperature,0,degC,2026-01-01T00:00:00+00:00,good\n"
    replay = service.import_run(
        lab.author, {"asset_id": lab.a["id"], "name": "Captured", "csv": csv, "source": "User import"}
    )
    run = service.run(lab.author, tool["id"], {}, replay_id=replay["id"])
    wait(lambda: service.inspect(lab.author, run["id"])["status"] == "completed")
    assert replay["samples"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("dependencies", ["requests"]),
        ("tests", []),
        ("input_schema", {"$ref": "https://example.org/schema"}),
        ("kind", "shell"),
    ],
)
def test_invalid_analysis_contract(lab, field, value):
    with pytest.raises(ValueError):
        analysis_lab(lab).create(lab.author, {**tool_body(lab), field: value})


def mapping(lab, transport):
    return {
        "asset_id": lab.a["id"],
        "name": "Sensor mapping",
        "transport": transport,
        "channels": [
            {
                "channel_id": "temperature",
                "unit": "degC",
                "calibration_id": "cal-1",
                "valid_min": 0,
                "valid_max": 60,
                "safe_min": 5,
                "safe_max": 40,
                "max_age_s": 1,
                "source": {"topic": "bench/temp"}
                if transport == "mqtt"
                else {"channel_id": "temperature"}
                if transport == "serial_jsonl"
                else {"register": 0, "function": 4, "data_type": "uint16"},
            }
        ],
    }


@pytest.mark.parametrize("transport", ["mqtt", "serial_jsonl", "modbus_tcp"])
def test_connector_proposals_are_reviewed_not_applied(lab, transport):
    service = ConnectorProfiles(lab.p)
    value = service.create(lab.author, mapping(lab, transport))
    with pytest.raises(PermissionError):
        service.review(lab.author, value["id"])
    reviewed = service.review(lab.reviewer, value["id"])
    assert reviewed["status"] == "reviewed_for_operator_installation"
    assert lab.p.asset(lab.author, lab.a["id"])["mode"] == "simulator"
    with pytest.raises(ValueError):
        service.review(lab.reviewer, value["id"])
    bad = mapping(lab, transport)
    bad["channels"][0]["source"]["url"] = "http://unapproved"
    with pytest.raises(ValueError):
        service.create(lab.author, bad)


def test_additive_api_collections_and_scoped_task_routes(lab):
    api = API(lab.p, None, lab.broker, lambda c: FixtureProvider())
    try:
        for path in (
            "templates",
            "projects",
            "drafts",
            "tasks",
            "teams",
            "tools",
            "analyses",
            "replays",
            "connector-profiles",
            "evidence",
        ):
            assert isinstance(api.route(lab.author, "GET", path.split("/"), {}), dict)
        project = api.route(lab.author, "POST", ["projects"], {"name": "Project", "asset_ids": [lab.a["id"]]})
        draft = api.route(
            lab.author, "POST", ["drafts"], {"asset_id": lab.a["id"], "project_id": project["id"]}
        )
        api.route(lab.author, "GET", ["drafts", draft["id"]], {})
        draft = api.route(
            lab.author, "POST", ["drafts", draft["id"]], {"expected_revision": 1, "definition": lab.body}
        )
        v = api.route(lab.author, "POST", ["drafts", draft["id"], "commit"], {"expected_revision": 2})
        task = api.route(lab.author, "POST", ["tasks"], {"kind": "evaluate", "target_id": v["id"]})
        wait(lambda: api.route(lab.author, "GET", ["tasks", task["id"]], {})["status"] == "completed")
        assert api.route(lab.author, "POST", ["tasks", task["id"], "events"], {"after": 0})["events"]
        api.route(lab.author, "POST", ["tasks", task["id"], "cancel"], {})
    finally:
        api.close()


def test_manifest_authoring_tools_cannot_apply_or_approve(lab):
    from certarig.platform.workbench_tools import WorkbenchRegistry

    api = API(lab.p, None, lab.broker, lambda c: FixtureProvider())
    registry = WorkbenchRegistry(api, lab.author)
    try:
        assert not any("approve" in s.name or "apply" in s.name for s in registry.specs())
        result = registry.execute("create_agent_draft", {"asset_id": lab.a["id"], "goal": "Check freshness"})
        assert result.ok
        identifier = result.result["id"]
        assert registry.execute("read_agent_draft", {"draft_id": identifier}).ok
        assert registry.execute(
            "add_draft_requirement",
            {"draft_id": identifier, "expected_revision": 1, "message": "Check calibration"},
        ).ok
        assert not registry.execute(
            "add_draft_requirement", {"draft_id": identifier, "expected_revision": 1, "message": "Stale"}
        ).ok
        assert not registry.execute("approve", {}).ok
        assert not registry.execute("create_agent_draft", {"asset_id": lab.b["id"], "goal": "Forbidden"}).ok
        assert not registry.execute("read_task", {"task_id": 1}).ok
    finally:
        api.close()


def test_event_cursor_survives_unrelated_audit_volume(lab):
    tasks = Tasks(lab.p, lambda c: FixtureProvider(), lab.broker)
    try:
        for i in range(4100):
            lab.store.audit(lab.author.org_id, "unrelated", "fixture", index=i)
        t = tasks.submit(lab.author, {"kind": "evaluate", "target_id": lab.v["id"]})
        wait(lambda: tasks.get(lab.author, t["id"])["status"] == "completed")
        assert tasks.events(lab.author, t["id"])["events"][0]["event"] == "queued"
    finally:
        tasks.close()


def test_strict_model_budget_is_preserved_in_evaluation_and_team(lab):
    limited = lab.p.create_version(
        lab.author,
        {**lab.body, "limits": {"model_calls": 1, "lease_s": 60, "interval_s": 30, "max_assessments": 1}},
    )
    e = evaluation.collect(lab.p, lab.author, limited, lambda c: FixtureProvider())
    assert e["status"] == "failed" and not e["trusted"]
    team = make_team(lab)
    lab.store.get("version", team["id"], lab.author.org_id)
    budget = teams.Budget(lambda: None, 1)
    bounded = budget.wrap(FixtureProvider())
    from certarig.agent.providers.base import Message

    bounded.complete("", [Message("user", "test")], [])
    with pytest.raises(PermissionError, match="budget"):
        bounded.complete("", [Message("user", "test")], [])


def reviewed_analysis(lab):
    service = analysis_lab(lab)
    tool = service.create(lab.author, tool_body(lab))
    test = service.test(lab.author, tool["id"])
    wait(lambda: service.inspect(lab.author, test["analyses"][0])["status"] == "completed")
    return service, service.review(lab.reviewer, tool["id"], test["id"])


def test_deployed_analysis_complete_evidence_and_rechecksummed_omissions(lab):
    from certarig.platform.analysis import AnalysisRegistry
    from certarig.platform.registry import FixtureRegistry, ScopedRegistry

    service, tool = reviewed_analysis(lab)
    v = lab.p.create_version(lab.author, {**lab.body, "analysis_tools": [tool["id"]]})
    e = evaluation.collect(lab.p, lab.author, v, lambda c: FixtureProvider())
    e = evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    d = lab.p.review(lab.reviewer, v["id"], e["id"])
    base = ScopedRegistry(FixtureRegistry("nominal"), v["tools"], lambda: None)
    registry = AnalysisRegistry(base, service, lab.author, v, lambda: None, d["id"])
    assert "analysis_" + tool["id"] in {s.name for s in registry.specs()}
    assert registry.execute("read_signals", {}).ok
    assert not registry.execute("analysis_unknown", {}).ok
    result = registry.execute("analysis_" + tool["id"], {})
    assert result.ok, result.result
    assert service.wait(lab.author, result.result["analysis_id"], lambda: None)["status"] == "completed"
    bundle = evidence.export(lab.p, lab.reviewer, d["id"])
    assert evidence.verify(bundle)["analysis_runs"] == 1

    def alter(name, fn):
        import hashlib

        from certarig.platform.contracts import encoded

        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            files = {n: archive.read(n) for n in archive.namelist()}
        value = json.loads(files[name])
        fn(value)
        files[name] = encoded(value)
        manifest = json.loads(files["manifest.json"])
        manifest["files"][name] = hashlib.sha256(files[name]).hexdigest()
        files["manifest.json"] = encoded(manifest)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for n, b in files.items():
                archive.writestr(n, b)
        return stream.getvalue()

    with pytest.raises(ValueError, match="analysis"):
        evidence.verify(alter("analysis.json", lambda value: value.update(runs=[])))
    with pytest.raises((ValueError, KeyError)):
        evidence.verify(alter("analysis.json", lambda value: value.update(tools=[])))
    with pytest.raises(ValueError):
        evidence.verify(
            alter("analysis.json", lambda value: value["runs"][0].update(inputs={"different": True}))
        )
    with pytest.raises(ValueError):
        evidence.verify(alter("analysis.json", lambda value: value["tools"][0].update(source="changed")))
    with pytest.raises(ValueError):
        evidence.verify(
            alter("analysis.json", lambda value: value["runs"][0].update(output={"different": True}))
        )


def test_analysis_failure_cancellation_and_runtime_refusal(lab, monkeypatch):
    service, tool = reviewed_analysis(lab)
    run = service.run(lab.author, tool["id"], {})

    def revoke():
        raise PermissionError("Revoked during analysis")

    with pytest.raises(PermissionError):
        service.wait(lab.author, run["id"], revoke)
    assert service.get(lab.author, "analysis", run["id"])["status"] == "cancelled"
    with pytest.raises(PermissionError):
        service.run(lab.reviewer, tool["id"], {})
    lab.broker.engine.ready = False
    with pytest.raises(ValueError, match="preflight"):
        service.run(lab.author, tool["id"], {})
    lab.broker.engine.ready = True
    badtest = service.test(lab.author, tool["id"])
    wait(lambda: service.inspect(lab.author, badtest["analyses"][0])["status"] == "completed")
    record = lab.store.get("analysis_tool", tool["id"], lab.author.org_id)
    record["tests"][0]["expected"] = {"mismatch": True}
    lab.store.put("analysis_tool", record)
    with pytest.raises(ValueError):
        service.review(lab.reviewer, tool["id"], badtest["id"])
    with pytest.raises(ValueError):
        service.import_run(
            lab.author, {"asset_id": lab.a["id"], "name": "invalid", "csv": "a,b\n1,2", "source": "test"}
        )


def test_all_analysis_and_connector_api_routes(lab):
    analysis_lab(lab)
    api = API(lab.p, None, lab.broker, lambda c: FixtureProvider())
    try:
        tool = api.route(lab.author, "POST", ["tools"], tool_body(lab))
        assert api.route(lab.author, "GET", ["tools", tool["id"]], {})["id"] == tool["id"]
        test = api.route(lab.author, "POST", ["tools", tool["id"], "test"], {})
        wait(
            lambda: (
                api.route(lab.author, "GET", ["analyses", test["analyses"][0]], {})["status"] == "completed"
            )
        )
        api.route(lab.reviewer, "POST", ["tools", tool["id"], "review"], {"test_id": test["id"]})
        assert api.route(lab.author, "GET", ["tools", tool["id"], "tests"], {})["tests"]
        run = api.route(lab.author, "POST", ["tools", tool["id"], "run"], {"inputs": {}})
        wait(lambda: api.route(lab.author, "GET", ["analyses", run["id"]], {})["status"] == "completed")
        assert api.route(lab.author, "POST", ["analyses", run["id"], "artifact"], {"name": "result.json"})[
            "data"
        ]
        api.route(lab.author, "POST", ["analyses", run["id"], "cancel"], {})
        profile = api.route(lab.author, "POST", ["connector-profiles"], mapping(lab, "mqtt"))
        api.route(lab.author, "GET", ["connector-profiles", profile["id"]], {})
        api.route(lab.reviewer, "POST", ["connector-profiles", profile["id"], "review"], {})
        assert api.route(lab.author, "GET", ["workbench-tools"], {})["tools"]
    finally:
        api.close()


def test_sdk_helpers_keep_authority_and_revisions_explicit():
    from certarig.platform.client import PlatformClient

    class Client(PlatformClient):
        def request(self, method, path, body=None):
            assert path.startswith("/v1/")
            return {"projects": [], "events": [], "runtime": {}, "tools": [], "ok": True}

    client = Client("http://127.0.0.1:1234", "session")
    assert client.projects() == []
    for result in (
        client.create_draft(asset_id="a"),
        client.update_draft("d", 1, message="answer"),
        client.commit_draft("d", 2),
        client.submit_task("evaluate", "v"),
        client.task_events("t"),
        client.cancel_task("t"),
        client.create_team("team", "v", ["w"]),
        client.create_analysis_tool(name="tool"),
        client.run_analysis("tool", {}),
        client.propose_connector(asset_id="a"),
        client.import_replay(asset_id="a"),
        client.verify_evidence("d"),
    ):
        assert result is not None


def test_grant_loss_still_closes_previously_owned_analysis(lab):
    service, tool = reviewed_analysis(lab)
    run = service.run(lab.author, tool["id"], {})
    lab.p.grant(lab.reviewer, lab.a["id"], lab.author.user_id, False)

    def lost_authority():
        lab.p.asset(lab.author, lab.a["id"])

    with pytest.raises(PermissionError):
        service.wait(lab.author, run["id"], lost_authority)
    workspace = lab.broker.call("read", service._owner(run), "agent", {"sandbox_id": run["sandbox_id"]})
    assert workspace["status"] == "closed"
    assert lab.store.get("analysis", run["id"], lab.author.org_id)["status"] == "cancelled"
    with pytest.raises(PermissionError):
        service.cancel(lab.author, run["id"])
