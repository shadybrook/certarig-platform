"""Customer lifecycle acceptance tests. Fake engines are never runtime qualification."""

import copy
import io
import json
import zipfile
from types import SimpleNamespace

import pytest

from certarig.agent.providers.base import ProviderResponse
from certarig.platform import evaluation, evidence, health
from certarig.platform.contracts import READ_TOOLS, verify_trace
from certarig.platform.evaluation import FixtureProvider
from certarig.platform.registry import FixtureRegistry, ScopedRegistry
from certarig.platform.runtime import Runtime
from certarig.platform.service import Platform
from certarig.platform.store import Actor, Store
from certarig.sandbox.broker import Broker
from certarig.sandbox.engine import policy_hash


class Client:
    profile = "profile-a"
    physical = False
    missing = False
    contract_hash = "test-contract"

    def __init__(self, url="", **kwargs):
        self.url = url

    def rig(self):
        return {
            "config_hash": self.profile,
            "rig": {"hardware": {"mode": "raspberry_pi" if self.physical else "simulator"}},
        }

    def capabilities(self):
        return {
            "agent_tools": [
                {
                    "name": t,
                    "description": t,
                    "policy": "allowed",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                }
                for t in READ_TOOLS
                if not (self.missing and t == "read_signals")
            ]
        }

    def refresh_contract(self):
        return None

    def signals(self):
        return FixtureRegistry("nominal").execute("read_signals", {}).result

    def state(self):
        return {"state": "safe"}

    def get(self, path):
        return {"fixture": True}


class Engine:
    image = current_image = "sha256:" + "1" * 64
    ready = True
    forge = False
    failed = False

    def preflight(self):
        return {"ready": self.ready, "blockers": [] if self.ready else ["unqualified test runtime"]}

    def run(self, job, kind, inputs, seconds, cancel):
        result = verify_trace(json.loads(inputs["trace.json"]))
        if self.forge:
            result["passed"] = not result["passed"]
        return {
            "status": "failed" if self.failed else "completed",
            "files": {"evaluation.json": json.dumps(result).encode()},
            "resource": {"fixture": True, "seconds": 0},
        }

    def cleanup(self, name):
        pass


@pytest.fixture
def lab(tmp_path):
    now = [1000.0]
    store = Store(tmp_path / "platform", clock=lambda: now[0])
    author = Actor(store.provision("issuer", "author", "org", "author"), "org", "author")
    reviewer = Actor(store.provision("issuer", "reviewer", "org", "reviewer"), "org", "reviewer")
    outsider = Actor(store.provision("issuer", "other", "other-org", "reviewer"), "other-org", "reviewer")
    configs = {
        "a": {"url": "http://127.0.0.1:18091", "auditor_key": "a-secret", "name": "Thermal", "org_id": "org"},
        "b": {
            "url": "http://127.0.0.1:18092",
            "auditor_key": "b-secret",
            "name": "Pressure",
            "org_id": "org",
        },
    }
    platform = Platform(store, configs, Client)
    a = platform.enroll(reviewer, platform.pair(reviewer, "a")["code"])
    b = platform.enroll(reviewer, platform.pair(reviewer, "b")["code"])
    platform.grant(reviewer, a["id"], author.user_id, True)
    connection = platform.connection(
        author, {"backend": "fixture", "model": "deterministic/1", "consent": True}
    )
    definition = {
        "name": "Observer",
        "instructions": "Check signals without acting.",
        "asset_id": a["id"],
        "connection_id": connection["id"],
        "tools": ["read_signals", "read_rig"],
    }
    version = platform.create_version(author, definition)
    engine = Engine()
    broker = Broker(tmp_path / "broker", engine, clock=lambda: now[0])
    runtime = Runtime(
        platform, lambda c: FixtureProvider(), lambda a, e: evaluation.validate(platform, a, e, broker)
    )
    context = SimpleNamespace(
        runtime=runtime,
        store=store,
        p=platform,
        author=author,
        reviewer=reviewer,
        outsider=outsider,
        a=a,
        b=b,
        c=connection,
        v=version,
        body=definition,
        engine=engine,
        broker=broker,
        now=now,
    )
    yield context
    runtime.close()
    broker.close()
    store.close()


def qualified(lab):
    e = evaluation.collect(lab.p, lab.author, lab.v, lambda c: FixtureProvider())
    assert e["status"] == "awaiting_sandbox"
    e = evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    assert e["trusted"] and e["status"] == "passed"
    return e


def deployed(lab):
    e = qualified(lab)
    evaluation.validate(lab.p, lab.reviewer, e["id"], lab.broker)
    d = lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    return lab.p.start(lab.reviewer, d["id"])


def test_identity_grants_immutable_versions_and_enrollment(lab):
    p = lab.p
    assert len(p.assets(lab.author)) == 1
    assert len(p.assets(lab.reviewer)) == 2
    assert not p.assets(lab.outsider)
    with pytest.raises(PermissionError, match="organization"):
        p.pair(lab.outsider, "a")
    with pytest.raises(KeyError):
        p.asset(lab.author, lab.b["id"])
    with pytest.raises(KeyError):
        p.version(lab.outsider, lab.v["id"])
    with pytest.raises(PermissionError):
        p.pair(lab.author, "a")
    with pytest.raises(ValueError):
        p.pair(lab.reviewer, "unknown")
    tx = p.pair(lab.reviewer, "a")["code"]
    with pytest.raises(ValueError, match="already enrolled"):
        p.enroll(lab.reviewer, tx)
    with pytest.raises(ValueError, match="consumed"):
        p.enroll(lab.reviewer, tx)
    tx = p.pair(lab.reviewer, "a")["code"]
    with pytest.raises(PermissionError):
        p.enroll(lab.outsider, tx)
    v2 = p.create_version(lab.author, {**lab.body, "instructions": "Changed"}, lab.v["agent_id"])
    assert v2["revision"] == 2 and lab.v["hash"] != v2["hash"]
    assert p.version(lab.author, lab.v["id"])["instructions"] == lab.body["instructions"]
    with pytest.raises(PermissionError):
        p.create_version(lab.reviewer, {**lab.body, "connection_id": lab.c["id"]}, lab.v["agent_id"])
    assert len(p.versions(lab.author)) == 2
    assert p.read_asset(lab.author, lab.a["id"], "state")["state"] == "safe"
    with pytest.raises(ValueError):
        p.read_asset(lab.author, lab.a["id"], "actuate")
    with pytest.raises(PermissionError):
        p.reviewer(Actor(lab.author.user_id, "org", "reviewer"))
    p.grant(lab.reviewer, lab.a["id"], lab.author.user_id, False)
    assert not p.assets(lab.author) and not p.versions(lab.author)


@pytest.mark.parametrize(
    "change",
    [
        {"tools": ["apply_rig"]},
        {"tools": ["read_signals", "read_signals"]},
        {"tools": []},
        {"name": ""},
        {"instructions": "x" * 8001},
        {"forged_role": "reviewer"},
    ],
)
def test_invalid_definition_cannot_create_authority(lab, change):
    with pytest.raises(ValueError):
        lab.p.create_version(lab.author, {**lab.body, **change})


def test_auth_sessions_transactions_and_private_storage(lab, tmp_path):
    s = lab.store
    token, info = s.login("issuer", "author")
    actor, csrf = s.session(token)
    assert actor == lab.author and info["csrf"] == csrf
    with pytest.raises(PermissionError):
        s.session(token, "forged")
    lab.now[0] += 1800
    with pytest.raises(PermissionError):
        s.session(token)
    token, _ = s.login("issuer", "author")
    s.logout(token)
    with pytest.raises(PermissionError):
        s.session(token)
    with pytest.raises(PermissionError):
        s.login("issuer", "unknown")
    with pytest.raises(ValueError):
        s.provision("i", "s", "o", "admin")
    s.transaction("test", "code", {"source": "trusted"})
    assert s.consume("test", "code")["source"] == "trusted"
    with pytest.raises(ValueError):
        s.consume("test", "code")
    s.transaction("test", "expired", {}, 1)
    lab.now[0] += 2
    with pytest.raises(ValueError):
        s.consume("test", "expired")
    with pytest.raises(ValueError):
        s.secret("../escape")
    with pytest.raises(KeyError):
        s.get("asset", "unknown", "org")
    folder = tmp_path / "public"
    folder.mkdir(mode=0o755)
    with pytest.raises(ValueError):
        Store(folder)
    link = tmp_path / "symlink"
    link.symlink_to(s.root)
    with pytest.raises(ValueError):
        Store(link)
    with pytest.raises(ValueError):
        with s.atomic():
            s.put("test", {"id": "rollback", "org_id": "org"})
            raise ValueError("roll back")
    with pytest.raises(KeyError):
        s.get("test", "rollback", "org")


def test_fixture_evaluation_is_bound_and_never_codex_qualification(lab):
    e = qualified(lab)
    assert set(e["trace"]["cases"]) == {
        "nominal",
        "stale_data",
        "wrong_unit",
        "forbidden_action",
        "cross_asset",
    }
    assert e["binding"]["backend"] == "fixture"
    assert evaluation.validate(lab.p, lab.reviewer, e["id"], lab.broker) == e
    with pytest.raises(PermissionError):
        lab.p.review(lab.author, lab.v["id"], e["id"])
    with pytest.raises(PermissionError):
        evaluation.qualify(lab.p, lab.reviewer, e["id"], lab.broker)
    changed = lab.p.create_version(lab.author, {**lab.body, "instructions": "Changed"}, lab.v["agent_id"])
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, changed["id"], e["id"])
    c = lab.store.get("connection", lab.c["id"], "org")
    c["model"] = "codex-model"
    lab.store.put("connection", c)
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    e["receipt"]["verification"]["passed"] = False
    with pytest.raises(ValueError):
        lab.broker.call("agent_evaluation_validate", "org/" + e["id"], "agent", {"receipt": e["receipt"]})


def test_runtime_observes_without_write_authority_and_exports(lab):
    d = deployed(lab)
    runtime = lab.runtime
    runtime.tick(d["id"])
    current = lab.p.deployment(lab.author, d["id"])
    assert current["assessments"] == 1
    runtime.tick(d["id"])
    assert lab.p.deployment(lab.author, d["id"])["assessments"] == 1
    payload = evidence.export(lab.p, lab.author, d["id"])
    assert evidence.verify(payload)["observations"] == 1
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        text = "".join(z.read(n).decode() for n in z.namelist())
        assert "a-secret" not in text and "auditor_key" not in text
    lab.p.revoke(lab.author, d["id"])
    runtime.sweep()
    runtime.tick(d["id"])
    assert lab.p.deployment(lab.author, d["id"])["status"] == "revoked"
    runtime.close()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        files = {n: z.read(n) for n in z.namelist()}
    for missing in files:
        corrupt = io.BytesIO()
        with zipfile.ZipFile(corrupt, "w") as z:
            for n, v in files.items():
                if n != missing:
                    z.writestr(n, v)
        with pytest.raises(ValueError):
            evidence.verify(corrupt.getvalue())
    files["events.json"] = b"[]"
    corrupt = io.BytesIO()
    with zipfile.ZipFile(corrupt, "w") as z:
        for n, v in files.items():
            z.writestr(n, v)
    with pytest.raises(ValueError, match="Corrupt"):
        evidence.verify(corrupt.getvalue())


@pytest.mark.parametrize(
    "failure", ["permission", "model", "profile", "reviewer", "lease", "provider", "restart"]
)
def test_runtime_refusal_failure_and_restart_restore_no_authority(lab, monkeypatch, failure):
    d = deployed(lab)

    def factory(c):
        return FixtureProvider()

    runtime = lab.runtime
    runtime.factory = factory
    if failure == "permission":
        lab.p.grant(lab.reviewer, lab.a["id"], lab.author.user_id, False)
    if failure == "model":
        lab.p.disconnect(lab.author, lab.c["id"])
    if failure == "profile":
        monkeypatch.setattr(Client, "profile", "changed")
    if failure == "reviewer":
        lab.store.db.execute("UPDATE memberships SET enabled=0 WHERE user_id=?", (lab.reviewer.user_id,))
    if failure == "lease":
        lab.now[0] += 901
    if failure == "provider":
        runtime.factory = lambda c: (_ for _ in ()).throw(RuntimeError("provider offline"))
    if failure == "restart":
        Platform(lab.store, lab.p.connectors, Client)
    runtime.tick(d["id"])
    row = lab.store.get("deployment", d["id"], "org")
    assert row["status"] in {"paused", "interrupted"} and row["assessments"] == 0
    with pytest.raises((ValueError, PermissionError, KeyError)):
        lab.p.start(lab.reviewer, d["id"])
    runtime.close()


def test_late_revoked_inference_is_discarded(lab):
    d = deployed(lab)

    class Late(FixtureProvider):
        def complete(self, *args):
            lab.p.revoke(lab.author, d["id"])
            return ProviderResponse('{"status":"ready","reason":"late"}')

    runtime = lab.runtime
    runtime.factory = lambda c: Late()
    runtime.tick(d["id"])
    current = lab.p.deployment(lab.author, d["id"])
    assert current["status"] == "revoked" and current["observations"] == []
    runtime.close()


def test_scope_rejects_forbidden_tools_cross_asset_and_revocation():
    registry = ScopedRegistry(FixtureRegistry("nominal"), ["read_signals", "apply_rig"], lambda: None)
    assert {s.name for s in registry.specs()} == {"read_signals"}
    assert not registry.execute("apply_rig", {}).ok
    assert not registry.execute("read_signals", {"asset_id": "bench-b"}).ok
    assert registry.execute("read_signals", {}).ok
    registry.guard = lambda: (_ for _ in ()).throw(PermissionError("revoked"))
    assert not registry.execute("read_signals", {}).ok


def test_unavailable_or_forged_sandbox_cannot_qualify(lab):
    e = evaluation.collect(lab.p, lab.author, lab.v, lambda c: FixtureProvider())
    lab.engine.ready = False
    with pytest.raises(ValueError, match="unavailable"):
        evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    assert not lab.store.get("evaluation", e["id"], "org")["trusted"]
    lab.engine.ready = True
    lab.engine.forge = True
    with pytest.raises(ValueError, match="mismatch"):
        evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    lab.engine.forge = False
    lab.engine.failed = True
    with pytest.raises(ValueError, match="interrupted"):
        evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    e["trace"]["cases"].pop("nominal")
    with pytest.raises(ValueError):
        verify_trace(e["trace"])


def test_definition_and_model_rejections(lab, monkeypatch):
    for body in (
        {"backend": "paid", "model": "x"},
        {"backend": "codex", "model": ""},
        {"backend": "fixture", "model": "x", "role": "reviewer"},
    ):
        with pytest.raises(ValueError):
            lab.p.connection(lab.author, body)
    with pytest.raises(PermissionError):
        lab.p.owned_connection(lab.reviewer, lab.c["id"])
    monkeypatch.setattr(Client, "missing", True)
    with pytest.raises(ValueError):
        lab.p.create_version(lab.author, lab.body)
    with pytest.raises(PermissionError):
        lab.p.binding(lab.author, lab.v)
    monkeypatch.setattr(Client, "missing", False)
    monkeypatch.setattr(Client, "physical", True)
    with pytest.raises(ValueError):
        lab.p.binding(lab.author, lab.v)
    tx = lab.p.pair(lab.reviewer, "a")["code"]
    with pytest.raises(ValueError, match="Physical"):
        lab.p.enroll(lab.reviewer, tx)
    with pytest.raises(ValueError):
        Platform(lab.store, {"bad": {"url": "http://192.168.1.2"}})


def test_verifier_rejects_forged_actions_and_wrong_cases(lab):
    e = evaluation.collect(lab.p, lab.author, lab.v, lambda c: FixtureProvider())
    trace = copy.deepcopy(e["trace"])
    trace["cases"]["nominal"]["calls"].append({"name": "apply_rig", "ok": True})
    assert not verify_trace(trace)["passed"]
    trace["suite"] = "forged"
    with pytest.raises(ValueError):
        verify_trace(trace)
    e["status"] = "passed"
    e["trusted"] = False
    lab.store.put("evaluation", e)
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, lab.v["id"], e["id"])


def test_runner_or_policy_change_invalidates_evaluation(lab):
    e = qualified(lab)
    lab.engine.current_image = "sha256:" + "2" * 64
    with pytest.raises(ValueError):
        evaluation.validate(lab.p, lab.author, e["id"], lab.broker)
    assert e["policy_hash"] == policy_hash()


def test_no_self_review_even_if_user_role_changes(lab):
    e = qualified(lab)
    lab.store.provision("issuer", "author", "org", "reviewer")
    with pytest.raises(PermissionError, match="own"):
        lab.p.review(lab.author, lab.v["id"], e["id"])


def test_real_edge_recording_continues_when_agent_provider_fails(lab):
    import time

    from certarig.edge.client import EdgeClient
    from tests.support import AUDITOR_KEY, edge_server

    with edge_server("rig.sim.json", "capabilities.observe.json", start_loop=True) as edge:
        from certarig.edge.client import EdgeApiError

        edge.node.private_reads = True
        with pytest.raises(EdgeApiError) as denied:
            edge.anonymous().signals()
        assert denied.value.status == 401
        p = Platform(
            lab.store,
            {
                "real": {
                    "name": "Independent simulator",
                    "org_id": "org",
                    "url": edge.url,
                    "auditor_key": AUDITOR_KEY,
                }
            },
            EdgeClient,
            recover=False,
        )
        asset = p.enroll(lab.reviewer, p.pair(lab.reviewer, "real")["code"])
        p.grant(lab.reviewer, asset["id"], lab.author.user_id, True)
        version = p.create_version(lab.author, {**lab.body, "asset_id": asset["id"]})
        e = evaluation.collect(p, lab.author, version, lambda c: FixtureProvider())
        e = evaluation.qualify(p, lab.author, e["id"], lab.broker)
        d = p.review(lab.reviewer, version["id"], e["id"])
        d = p.start(lab.reviewer, d["id"])
        edge.operator().start_recording("independent-acquisition")
        before = edge.node.runtime.state()["recording"]["samples"]

        def failing(c):
            raise RuntimeError("Provider disconnected")

        runtime = lab.runtime
        runtime.platform = p
        runtime.factory = failing
        runtime.validate_receipt = lambda a, e: None
        runtime.tick(d["id"])
        assert p.deployment(lab.author, d["id"])["status"] == "paused"
        deadline = time.monotonic() + 2
        while edge.node.runtime.state()["recording"]["samples"] <= before and time.monotonic() < deadline:
            time.sleep(0.02)
        assert edge.node.runtime.state()["recording"]["active"]
        assert edge.node.runtime.state()["recording"]["samples"] > before
        result = edge.operator().stop_recording()
        assert result["completed_recording"]["samples"] > 0
        runtime.close()


def test_scheduler_limit_cancellation_and_runtime_restart(lab):
    import threading
    import time

    d = deployed(lab)
    runtime = lab.runtime
    entered, cancelled = threading.Event(), threading.Event()

    class Pending(FixtureProvider):
        def complete(self, *args):
            entered.set()
            assert cancelled.wait(2)
            return ProviderResponse('{"status":"ready","reason":"late"}')

        def cancel(self):
            cancelled.set()

    runtime.factory = lambda c: Pending()
    task = threading.Thread(target=runtime.tick, args=(d["id"],))
    task.start()
    assert entered.wait(2)
    lab.p.revoke(lab.author, d["id"])
    runtime.sweep()
    task.join(3)
    assert cancelled.is_set() and lab.p.deployment(lab.author, d["id"])["observations"] == []
    runtime.close()
    # A new reviewed lease completes after ten spaced assessments, never a catch-up burst.
    e = lab.store.get("evaluation", d["evaluation_id"], "org")
    runtime = Runtime(lab.p, lambda c: FixtureProvider(), lambda a, e: None)
    lab.runtime = runtime
    new = lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    new = lab.p.start(lab.reviewer, new["id"])
    for _ in range(10):
        runtime.tick(new["id"])
        for _heartbeat in range(30):
            lab.now[0] += 1
            health.pulse(lab.p, runtime.id)
    assert lab.p.deployment(lab.author, new["id"])["status"] == "completed"
    runtime.close()
    runtime = Runtime(lab.p, lambda c: FixtureProvider(), lambda a, e: None)
    lab.runtime = runtime
    new = lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    new = lab.p.start(lab.reviewer, new["id"])
    row = lab.p.deployment(lab.author, new["id"])
    row["runtime_id"] = "previous-runtime"
    lab.store.put("deployment", row)
    runtime = lab.runtime
    task = threading.Thread(target=runtime.serve)
    task.start()
    deadline = time.monotonic() + 2
    while (
        lab.store.get("deployment", row["id"], "org")["status"] == "running" and time.monotonic() < deadline
    ):
        time.sleep(0.02)
    runtime.close()
    task.join(2)
    assert lab.p.deployment(lab.author, row["id"])["status"] == "interrupted"


@pytest.mark.parametrize(
    "mutation", ["review", "org", "binding", "version", "events", "observations", "transcript", "manifest"]
)
def test_offline_consistency_rejects_rehashed_forged_or_incomplete_evidence(lab, mutation):
    import hashlib

    d = deployed(lab)
    runtime = lab.runtime
    runtime.tick(d["id"])
    runtime.close()
    payload = evidence.export(lab.p, lab.author, d["id"])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        values = {name: json.loads(archive.read(name)) for name in archive.namelist()}
    if mutation == "review":
        values["deployment.json"]["reviewer_id"] = values["version.json"]["author_id"]
    if mutation == "org":
        values["asset.json"]["org_id"] = "other-org"
    if mutation == "binding":
        values["evaluation.json"]["binding"]["profile_hash"] = "different"
    if mutation == "version":
        values["version.json"]["instructions"] = "different"
    if mutation == "events":
        values["events.json"] = []
    if mutation == "observations":
        values["deployment.json"]["assessments"] = 2
    if mutation == "transcript":
        values["deployment.json"]["observations"][0]["transcript"] = []
    files = {name: json.dumps(value).encode() for name, value in values.items() if name != "manifest.json"}
    values["manifest.json"]["files"] = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    if mutation == "manifest":
        values["manifest.json"]["files"].pop("asset.json")
    files["manifest.json"] = json.dumps(values["manifest.json"]).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    with pytest.raises(ValueError):
        evidence.verify(output.getvalue())


def test_failed_provider_evaluation_never_becomes_trusted(lab):
    class Failed(FixtureProvider):
        def complete(self, *args):
            return ProviderResponse("not JSON")

    e = evaluation.collect(lab.p, lab.author, lab.v, lambda c: Failed())
    assert e["status"] == "failed" and not e["trusted"]
    with pytest.raises(PermissionError):
        evaluation.qualify(lab.p, lab.author, e["id"], lab.broker)
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, lab.v["id"], e["id"])


def test_broker_evidence_required_artifacts_and_restart_interrupt(lab):
    from certarig.edge.atomic import write_json_atomic

    e = qualified(lab)
    path = lab.broker.root / "agent-evaluations" / e["receipt"]["job_id"] / "evaluation.json"
    path.unlink()
    with pytest.raises(ValueError, match="Missing or corrupt"):
        evaluation.validate(lab.p, lab.author, e["id"], lab.broker)
    with pytest.raises(PermissionError):
        lab.broker.call("agent_evaluation", "org/test", "auditor", {"trace": e["trace"]})
    with pytest.raises(ValueError):
        lab.broker.call(
            "agent_evaluation_validate", "org/test", "agent", {"receipt": {"job_id": "../unsafe"}}
        )
    pending = lab.broker.root / "agent-evaluations" / "job_1234567890abcdef.json"
    write_json_atomic(pending, {"owner": "org/eval", "job_id": "job_1234567890abcdef", "status": "running"})
    lab.broker.close()
    broker = Broker(lab.broker.root, lab.engine)
    try:
        assert json.loads(pending.read_text())["status"] == "interrupted"
    finally:
        broker.close()
