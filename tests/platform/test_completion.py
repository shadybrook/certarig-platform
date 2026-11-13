"""Remaining coding contracts; all providers and Sandbox engines here are explicit fixtures."""

import json
import threading
import time

import pytest

from certarig.platform import evidence, health, profiles
from certarig.platform.runtime import Runtime

from .test_lifecycle import Client, FixtureProvider, deployed, qualified


def changed_profile(lab, monkeypatch, name="profile-b"):
    monkeypatch.setattr(Client, "profile", name)
    return profiles.preview(lab.p, lab.reviewer, lab.a["id"])


def test_profile_recovery_requires_new_evaluation_and_preserves_old_bundle(lab, monkeypatch):
    d = deployed(lab)
    lab.runtime.tick(d["id"])
    old_eval = lab.store.get("evaluation", d["evaluation_id"], "org")
    assert evidence.verify(evidence.export(lab.p, lab.author, d["id"]))["valid"]
    preview = changed_profile(lab, monkeypatch)
    assert preview["changed"] and preview["diff"] and preview["revalidation"]["full_qualification"]
    assert lab.p.deployment(lab.author, d["id"])["status"] == "paused"
    assert profiles.history(lab.p, lab.author, lab.a["id"])[0]["revision"] == 1
    with pytest.raises(ValueError):
        lab.p.binding(lab.author, lab.v)
    result = profiles.accept(lab.p, lab.reviewer, lab.a["id"], preview["id"])
    assert result["asset"]["profile_revision"] == 2 and result["execution_authority"] is False
    assert lab.p.version(lab.author, lab.v["id"]) == lab.v
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, lab.v["id"], old_eval["id"])
    with pytest.raises(ValueError):
        lab.p.start(lab.reviewer, d["id"])
    # Historical exports use revision 1 even though the enrolled asset now has revision 2.
    raw = evidence.export(lab.p, lab.author, d["id"])
    assert evidence.verify(raw)["valid"]
    restored = qualified(lab)
    assert restored["binding"]["profile_revision"] == 2
    new = lab.p.review(lab.reviewer, lab.v["id"], restored["id"])
    new = lab.p.start(lab.reviewer, new["id"])
    lab.runtime.tick(new["id"])
    assert lab.p.deployment(lab.author, new["id"])["assessments"] == 1
    assert evidence.verify(evidence.export(lab.p, lab.author, new["id"]))["valid"]
    assert [p["revision"] for p in profiles.history(lab.p, lab.reviewer, lab.a["id"])] == [1, 2]
    # Returning to the original hash does not resurrect its old approval/evaluation.
    again = changed_profile(lab, monkeypatch, "profile-a")
    profiles.accept(lab.p, lab.reviewer, lab.a["id"], again["id"])
    with pytest.raises(ValueError):
        lab.p.review(lab.reviewer, lab.v["id"], old_eval["id"])


def test_profile_review_permissions_replay_expiry_and_races(lab, monkeypatch):
    with pytest.raises(PermissionError):
        profiles.preview(lab.p, lab.author, lab.a["id"])
    with pytest.raises(KeyError):
        profiles.preview(lab.p, lab.outsider, lab.a["id"])
    assert profiles.preview(lab.p, lab.reviewer, lab.a["id"])["status"] == "unchanged"
    first = changed_profile(lab, monkeypatch)
    with pytest.raises(PermissionError):
        profiles.accept(lab.p, lab.author, lab.a["id"], first["id"])
    with pytest.raises(PermissionError):
        profiles.accept(lab.p, lab.reviewer, lab.b["id"], first["id"])
    second = profiles.preview(lab.p, lab.reviewer, lab.a["id"])
    profiles.accept(lab.p, lab.reviewer, lab.a["id"], first["id"])
    for pending in (first, second):
        with pytest.raises(ValueError):
            profiles.accept(lab.p, lab.reviewer, lab.a["id"], pending["id"])
    third = changed_profile(lab, monkeypatch, "profile-c")
    monkeypatch.setattr(Client, "profile", "profile-d")
    with pytest.raises(ValueError):
        profiles.accept(lab.p, lab.reviewer, lab.a["id"], third["id"])
    expired = profiles.preview(lab.p, lab.reviewer, lab.a["id"])
    lab.now[0] += 301
    with pytest.raises(ValueError):
        profiles.accept(lab.p, lab.reviewer, lab.a["id"], expired["id"])
    monkeypatch.setattr(Client, "physical", True)
    with pytest.raises(ValueError):
        profiles.preview(lab.p, lab.reviewer, lab.a["id"])


def test_capability_policy_review_and_registry_tool_intersection(lab, monkeypatch):
    tools = lab.p.observation_tools(lab.author, lab.a["id"])
    assert len(tools) == 7 and "read_evidence" in {t["name"] for t in tools}
    with pytest.raises(KeyError):
        lab.p.observation_tools(lab.author, lab.b["id"])
    with pytest.raises(KeyError):
        lab.p.observation_tools(lab.outsider, lab.a["id"])
    original = Client.capabilities

    def changed(client):
        caps = original(client)
        caps["agent_tools"] += [
            {"name": "run_procedure", "policy": "allowed"},
            {"name": "apply_rig", "policy": "allowed"},
        ]
        for row in caps["agent_tools"]:
            if row["name"] == "read_evidence":
                row["policy"] = "human_approval"
        return caps

    monkeypatch.setattr(Client, "capabilities", changed)
    names = {t["name"] for t in lab.p.observation_tools(lab.author, lab.a["id"])}
    assert not names & {"read_evidence", "run_procedure", "apply_rig"}
    with pytest.raises(ValueError):
        lab.p.create_version(lab.author, {**lab.body, "tools": ["read_evidence"]})
    with pytest.raises(ValueError):
        lab.p.binding(lab.author, lab.v)
    preview = profiles.preview(lab.p, lab.reviewer, lab.a["id"])
    assert preview["changed"] and "~ connector_capabilities" in preview["diff"]
    profiles.accept(lab.p, lab.reviewer, lab.a["id"], preview["id"])
    assert qualified(lab)["binding"]["profile_revision"] == 2


def test_heartbeat_timeout_blocks_start_interrupts_and_never_resumes(lab):
    d = deployed(lab)
    lab.now[0] += health.TIMEOUT_S + 1
    result = lab.p.present_deployment(lab.author, d["id"])
    assert result["status"] == "interrupted" and result["runtime_health"]["state"] == "unresponsive"
    assert result["provider_status"] == "interrupted"
    with pytest.raises(PermissionError):
        health.pulse(lab.p, lab.runtime.id)
    lab.runtime.tick(d["id"])
    assert lab.p.deployment(lab.author, d["id"])["observations"] == []
    e = lab.store.get("evaluation", d["evaluation_id"], "org")
    approval = lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    with pytest.raises(ValueError, match="runtime"):
        lab.p.start(lab.reviewer, approval["id"])
    replacement = Runtime(lab.p, lambda c: FixtureProvider(), lambda a, e: None)
    assert lab.p.deployment(lab.author, approval["id"])["status"] == "interrupted"
    assert lab.p.deployment(lab.author, d["id"])["status"] == "interrupted"
    with pytest.raises(PermissionError):
        health.pulse(lab.p, lab.runtime.id)
    replacement.close()
    assert health.status(lab.store)["state"] == "offline"


def test_runtime_activity_provider_failure_close_and_independent_heartbeat(lab):
    d = deployed(lab)
    lab.runtime.activity(d["id"], "assessing", "model")
    assert lab.p.deployment(lab.author, d["id"])["provider_status"] == "assessing"
    lab.runtime.trace_activity(d["id"], {"kind": "tool_call", "name": "read_evidence"})
    assert lab.p.deployment(lab.author, d["id"])["activity"] == "read_evidence"
    lab.runtime.tick(d["id"])
    row = lab.p.deployment(lab.author, d["id"])
    assert row["provider_status"] == "idle" and row["last_assessment_at"] == lab.now[0]
    with pytest.raises(PermissionError):
        lab.runtime.activity("missing", "assessing", "model")
    lab.runtime.close()
    assert lab.p.deployment(lab.author, d["id"])["status"] == "interrupted"
    assert health.status(lab.store)["state"] == "offline"


def test_missing_history_cannot_export_and_legacy_record_is_retained(lab, monkeypatch):
    d = deployed(lab)
    preview = changed_profile(lab, monkeypatch)
    profiles.accept(lab.p, lab.reviewer, lab.a["id"], preview["id"])
    historical = profiles.evidence_asset(lab.p, lab.author, d)
    assert historical["profile_hash"] == "profile-a"
    legacy = json.loads(json.dumps(d))
    legacy["binding"].pop("profile_revision")
    assert profiles.evidence_asset(lab.p, lab.author, legacy)["profile_hash"] == "profile-a"
    lab.store.db.execute(
        "DELETE FROM documents WHERE kind='asset_profile' AND id=?", (lab.a["id"] + "_profile_1",)
    )
    with pytest.raises(KeyError):
        evidence.export(lab.p, lab.author, d["id"])
    with pytest.raises(ValueError):
        profiles.evidence_asset(lab.p, lab.author, legacy)


def test_http_profile_recovery_tools_health_and_cross_scope(lab, http, monkeypatch):
    from urllib.error import HTTPError

    from certarig.platform.client import PlatformClient

    origin, _ = http
    token, info = lab.store.login("issuer", "author")
    author = PlatformClient(origin, token, info["csrf"])
    reviewer_token, reviewer_info = lab.store.login("issuer", "reviewer")
    reviewer = PlatformClient(origin, reviewer_token, reviewer_info["csrf"])
    assert len(author.observation_tools(lab.a["id"])) == 7
    assert author.runtime_health()["state"] == "online"
    with pytest.raises(HTTPError) as denied:
        author.preview_profile(lab.a["id"])
    assert denied.value.code == 403
    with pytest.raises(HTTPError):
        author.observation_tools(lab.b["id"])
    monkeypatch.setattr(Client, "profile", "http-profile-2")
    preview = reviewer.preview_profile(lab.a["id"])
    assert preview["changed"]
    result = reviewer.accept_profile(lab.a["id"], preview["id"])
    assert not result["execution_authority"] and result["asset"]["profile_revision"] == 2
    assert len(author.request("GET", "/v1/assets/" + lab.a["id"] + "/profiles")["profiles"]) == 2
    lab.runtime.close()
    assert author.runtime_health()["state"] == "offline"


def test_heartbeat_thread_runs_during_inference_and_provider_errors_are_visible(lab):
    d = deployed(lab)
    entered, release = threading.Event(), threading.Event()

    class Waiting(FixtureProvider):
        def complete(self, *args):
            entered.set()
            assert release.wait(3)
            raise RuntimeError("Fixture provider disconnected")

        def cancel(self):
            release.set()

    lab.runtime.factory = lambda c: Waiting()
    task = threading.Thread(target=lab.runtime.serve)
    task.start()
    try:
        assert entered.wait(2)
        assert lab.p.deployment(lab.author, d["id"])["provider_status"] == "assessing"
        lab.now[0] += 1
        deadline = time.monotonic() + 2
        while health.status(lab.store)["heartbeat_at"] != lab.now[0] and time.monotonic() < deadline:
            time.sleep(0.02)
        assert health.status(lab.store)["heartbeat_at"] == lab.now[0]
        release.set()
        deadline = time.monotonic() + 2
        while lab.p.deployment(lab.author, d["id"])["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.02)
        row = lab.p.deployment(lab.author, d["id"])
        assert row["status"] == "paused" and row["provider_status"] == "error"
        assert row["last_provider_error"] == "RuntimeError"
    finally:
        release.set()
        lab.runtime.close()
        task.join(2)


def test_nested_transaction_rollback_does_not_commit_partial_profile_state(lab):
    with lab.store.atomic():
        lab.store.put("test", {"id": "kept", "org_id": "org"})
        with pytest.raises(ValueError):
            with lab.store.atomic():
                lab.store.put("test", {"id": "rolled-back", "org_id": "org"})
                raise ValueError("inner transaction refused")
        assert lab.store.get("test", "kept", "org")["id"] == "kept"
    with pytest.raises(KeyError):
        lab.store.get("test", "rolled-back", "org")


def test_all_read_tools_enforce_arguments_and_reject_run_path_traversal(lab):
    from certarig.platform.contracts import READ_TOOLS
    from certarig.platform.registry import FixtureRegistry, ScopedRegistry

    registry = ScopedRegistry(FixtureRegistry("nominal"), list(READ_TOOLS), lambda: None)
    assert len(registry.specs()) == 7
    for name in READ_TOOLS:
        args = {"run_id": "run_test-123"} if name == "read_procedure_run" else {}
        assert registry.execute(name, args).ok
        assert not registry.execute(name, {**args, "asset_id": "bench-b"}).ok
    for invalid in ["../rig", "run?asset=b", "run/other", "run\\other", ""]:
        assert not registry.execute("read_procedure_run", {"run_id": invalid}).ok


def test_provider_cleanup_failure_pauses_and_releases_assessment_slot(lab):
    d = deployed(lab)

    class CleanupFailure(FixtureProvider):
        def close(self):
            raise RuntimeError("fixture cleanup failure")

    lab.runtime.factory = lambda c: CleanupFailure()
    lab.runtime.tick(d["id"])
    row = lab.p.deployment(lab.author, d["id"])
    assert row["status"] == "paused" and row["provider_status"] == "error"
    assert not lab.runtime.slot.locked()


def test_start_connector_check_cannot_block_runtime_heartbeat_or_revocation(lab, monkeypatch):
    e = qualified(lab)
    d = lab.p.review(lab.reviewer, lab.v["id"], e["id"])
    entered, release = threading.Event(), threading.Event()
    original = Client.rig

    def waiting(client):
        entered.set()
        assert release.wait(2)
        return original(client)

    monkeypatch.setattr(Client, "rig", waiting)
    result = []
    task = threading.Thread(target=lambda: result.append(lab.p.start(lab.reviewer, d["id"])))
    task.start()
    try:
        assert entered.wait(1)
        acquired = lab.store.lock.acquire(blocking=False)
        assert acquired, "Connector I/O held the heartbeat/revocation database lock"
        try:
            health.pulse(lab.p, lab.runtime.id)
        finally:
            lab.store.lock.release()
    finally:
        release.set()
        task.join(3)
    assert result[0]["status"] == "running"


def test_model_status_poll_cannot_restore_disconnected_consent(lab):
    from certarig.platform.server import API

    c = lab.p.connection(lab.author, {"backend": "codex", "model": "test-model", "consent": True})

    class Managed:
        def account(self):
            lab.p.disconnect(lab.author, c["id"])
            return {"connected": True}

        def close(self):
            pass

    api = API(lab.p, None, None, lambda connection: Managed())
    with pytest.raises(PermissionError, match="disconnected"):
        api.route(lab.author, "POST", ["model-connections", c["id"], "status"], {})
    current = lab.p.owned_connection(lab.author, c["id"])
    assert not current["enabled"] and not current["consent"] and current["revision"] == 2
    with pytest.raises(PermissionError):
        api.route(lab.author, "POST", ["model-connections", c["id"], "login"], {})
    api.close()


def test_model_disconnect_is_persisted_before_provider_cleanup(lab):
    from certarig.platform.server import API

    c = lab.p.connection(lab.author, {"backend": "codex", "model": "test-model", "consent": True})

    class Managed:
        def close(self):
            assert not lab.p.owned_connection(lab.author, c["id"])["enabled"]
            raise RuntimeError("fixture transport already gone")

    api = API(lab.p, None, None, lambda connection: Managed())
    api.connections[c["id"]] = Managed()
    with pytest.raises(RuntimeError):
        api.route(lab.author, "POST", ["model-connections", c["id"], "disconnect"], {})
    assert not lab.p.owned_connection(lab.author, c["id"])["consent"]
    api.close()
