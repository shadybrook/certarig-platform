from __future__ import annotations

import copy
import io
import threading
import time
import zipfile
from pathlib import Path

import pytest

from certarig.sandbox.broker import Broker
from certarig.sandbox.contracts import LIMITS
from certarig.sandbox.evidence import verify
from certarig.sandbox.transport import BrokerClient, server
from tests.support import wait_until


class FakeEngine:
    """Unit-test double. Does not qualify container isolation or execute supplied code."""

    image = "sha256:" + "a" * 64

    def __init__(self):  # type: ignore[no-untyped-def]
        self.ready = True
        self.cancelled = False
        self.cleaned = []
        self.output = {"analysis.json": b'{"qualification":true}'}
        self.hold = False

    def preflight(self):  # type: ignore[no-untyped-def]
        return {"ready": self.ready, "blockers": [] if self.ready else ["unit-test runtime unavailable"]}

    def cleanup(self, name):  # type: ignore[no-untyped-def]
        self.cleaned.append(name)

    def run(self, jid, kind, inputs, seconds, cancel):  # type: ignore[no-untyped-def]
        if self.hold:
            assert cancel.wait(2)
            self.cancelled = True
        return {
            "status": "cancelled" if cancel.is_set() else "completed",
            "files": self.output,
            "resource": {"test_double": True},
        }


@pytest.fixture
def broker(tmp_path):  # type: ignore[no-untyped-def]
    engine = FakeEngine()
    broker = Broker(tmp_path / "broker", engine)
    yield broker, engine
    broker.close()


def create(broker, value, owner="agent:alice"):  # type: ignore[no-untyped-def]
    return broker.call(
        "create",
        owner,
        "agent",
        {"document": value["document"], "procedure": value["procedure"], "base_config_hash": "base"},
    )


def wait_job(broker, sid, owner="agent:alice"):  # type: ignore[no-untyped-def]
    assert wait_until(
        lambda: (
            broker.call("read", owner, "agent", {"sandbox_id": sid})["jobs"][-1]["status"]
            not in {"queued", "running"}
        ),
        timeout=5,
    )
    return broker.call("read", owner, "agent", {"sandbox_id": sid})


def test_lifecycle_and_forged_receipt(broker, value, tmp_path):  # type: ignore[no-untyped-def]
    b, e = broker
    w = create(b, value)
    sid = w["sandbox_id"]
    assert b.call("list", "agent:alice", "agent", {})["workspaces"]
    assert not b.call("list", "agent:bob", "agent", {})["workspaces"]
    with pytest.raises(PermissionError):
        b.call("read", "agent:bob", "agent", {"sandbox_id": sid})
    b.call(
        "run",
        "agent:alice",
        "agent",
        {"sandbox_id": sid, "kind": "python", "source": "arbitrary not executed on host"},
    )
    w = wait_job(b, sid)
    job = w["jobs"][0]
    assert not job["qualification"]
    with pytest.raises(ValueError, match="trusted"):
        b.call("propose", "agent:alice", "agent", {"sandbox_id": sid, "job_id": job["job_id"]})
    assert b.call(
        "artifact",
        "agent:alice",
        "agent",
        {"sandbox_id": sid, "job_id": job["job_id"], "name": "analysis.json"},
    )["data"]
    with pytest.raises(KeyError):
        b.call(
            "artifact",
            "agent:alice",
            "agent",
            {"sandbox_id": sid, "job_id": job["job_id"], "name": "missing.txt"},
        )
    zipped = b.export(w)
    p = tmp_path / "evidence.zip"
    p.write_bytes(zipped)
    assert verify(p)["ok"]
    with zipfile.ZipFile(io.BytesIO(zipped)) as z:
        files = {n: z.read(n) for n in z.namelist()}
    files.pop(job["job_id"] + "/artifacts/analysis.json")
    with zipfile.ZipFile(p, "w") as z:
        for n, data in files.items():
            z.writestr(n, data)
    assert not verify(p)["ok"]
    candidate = copy.deepcopy(value["document"])
    candidate["channels"][0]["safe_max"] = 84
    candidate["abort_limits"]["temperature"] = 84
    revised = b.call(
        "revise", "agent:alice", "agent", {"sandbox_id": sid, "expected_revision": 0, "document": candidate}
    )
    assert revised["revision"] == 1
    with pytest.raises(ValueError, match="stale"):
        b.call(
            "revise",
            "agent:alice",
            "agent",
            {"sandbox_id": sid, "expected_revision": 0, "document": candidate},
        )
    b.call("close", "agent:alice", "agent", {"sandbox_id": sid})
    with pytest.raises(PermissionError):
        b.call("run", "agent:alice", "agent", {"sandbox_id": sid, "kind": "python", "source": "x"})
    b.export(b.call("read", "agent:alice", "agent", {"sandbox_id": sid}))


def test_refusals(broker, value):  # type: ignore[no-untyped-def]
    b, e = broker
    with pytest.raises(PermissionError):
        b.call("create", "x", "anonymous", {})
    with pytest.raises(PermissionError):
        b.call("create", "x", "auditor", {})
    with pytest.raises(ValueError):
        b.call(
            "create",
            "x",
            "agent",
            {
                "document": value["document"],
                "procedure": value["procedure"],
                "base_config_hash": "x",
                "seed": True,
            },
        )
    w = create(b, value)
    sid = w["sandbox_id"]
    base = {"sandbox_id": sid}
    assert b.call("preflight", "x", "operator", {})["ready"]
    for payload in [
        {"kind": "shell"},
        {"kind": "python", "source": ""},
        {"kind": "python", "source": "x" * 256001},
    ]:
        with pytest.raises(ValueError):
            b.call("run", "agent:alice", "agent", {**base, **payload})
    e.ready = False
    with pytest.raises(ValueError, match="preflight"):
        b.call("run", "agent:alice", "agent", {**base, "kind": "python", "source": "x"})
    with pytest.raises(PermissionError):
        b.call("close", "x", "auditor", base)
    with pytest.raises(ValueError):
        b.call("unknown", "agent:alice", "agent", base)


def test_cancellation_expiry_restart(broker, value):  # type: ignore[no-untyped-def]
    b, e = broker
    e.hold = True
    w = create(b, value)
    sid = w["sandbox_id"]
    b.call("run", "agent:alice", "agent", {"sandbox_id": sid, "kind": "python", "source": "not run"})
    assert wait_until(
        lambda: b.call("read", "agent:alice", "agent", {"sandbox_id": sid})["jobs"][0]["status"] == "running"
    )
    with pytest.raises(ValueError, match="finish"):
        b.export(b.call("read", "agent:alice", "agent", {"sandbox_id": sid}))
    b.call("close", "agent:alice", "agent", {"sandbox_id": sid})
    assert wait_job(b, sid)["jobs"][0]["status"] == "cancelled"
    assert e.cancelled
    w = create(b, value)
    sid = w["sandbox_id"]
    b.clock = lambda: w["expires_at"] + 1
    assert b.call("read", "agent:alice", "agent", {"sandbox_id": sid})["status"] == "expired"
    b.clock = time.time
    w = create(b, value)
    w["jobs"] = [{"job_id": "job_" + "1" * 16, "status": "running"}]
    b._save(w)
    b.close()
    new = Broker(b.root, e)
    try:
        restored = new.call("read", "agent:alice", "agent", {"sandbox_id": w["sandbox_id"]})
        assert restored["status"] == "expired" and restored["jobs"][0]["status"] == "interrupted"
        assert "crsb-job_" + "1" * 16 in e.cleaned
    finally:
        new.close()


def test_signing_and_quota(broker, value):  # type: ignore[no-untyped-def]
    b, e = broker
    w = create(b, value)
    w["jobs"] = [
        {
            "job_id": "job_" + "1" * 16,
            "status": "completed",
            "revision": w["revision"],
            "receipt": {"mac": "f" * 64, "binding": {}, "verification": {"passed": True}, "at": time.time()},
        }
    ]
    b._save(w)
    with pytest.raises(ValueError, match="stale or invalid"):
        b._receipt(w, w["jobs"][0])
    w["jobs"] = [{}] * LIMITS["jobs"]
    b._save(w)
    with pytest.raises(ValueError, match="quota"):
        b.call(
            "run", "agent:alice", "agent", {"sandbox_id": w["sandbox_id"], "kind": "python", "source": "x"}
        )


def test_transport(broker, value, tmp_path):  # type: ignore[no-untyped-def]
    b, e = broker
    import tempfile

    temporary = tempfile.TemporaryDirectory(prefix="crsb-", dir="/tmp")
    endpoint = Path(temporary.name) / "socket"
    listener = server(endpoint, b)
    thread = threading.Thread(target=listener.serve_forever, daemon=True)
    thread.start()
    client = BrokerClient(endpoint)
    try:
        assert client.call("preflight", "agent:alice", "agent", {})["ready"]
        w = client.call(
            "create",
            "agent:alice",
            "agent",
            {"document": value["document"], "procedure": value["procedure"], "base_config_hash": "base"},
        )
        with pytest.raises(PermissionError):
            client.call("read", "agent:bob", "agent", {"sandbox_id": w["sandbox_id"]})
        with pytest.raises(KeyError):
            client.call("read", "agent:alice", "agent", {"sandbox_id": "sbx_" + "0" * 16})
        with pytest.raises(ValueError):
            client.call("read", "agent:alice", "agent", {"sandbox_id": "bad"})
    finally:
        listener.shutdown()
        listener.server_close()
        thread.join(timeout=2)
        temporary.cleanup()


def test_valid_receipts_revalidation_and_raw_tamper(broker, value, rehearsal_files, tmp_path):  # type: ignore[no-untyped-def]
    b, e = broker
    e.output = rehearsal_files
    w = create(b, value)
    sid = w["sandbox_id"]
    b.call("run", "agent:alice", "agent", {"sandbox_id": sid, "kind": "rehearsal"})
    w = wait_job(b, sid)
    job = w["jobs"][-1]
    assert job["qualification"], job
    proposal = b.call("propose", "agent:alice", "agent", {"sandbox_id": sid, "job_id": job["job_id"]})
    assert proposal["status"] == "needs_operator_review"
    with pytest.raises(ValueError):
        b.call(
            "propose", "agent:alice", "agent", {"sandbox_id": sid, "job_id": job["job_id"], "kind": "code"}
        )
    with pytest.raises(PermissionError):
        b.call(
            "validate_proposal",
            "agent:alice",
            "agent",
            {"sandbox_id": sid, "proposal_id": proposal["proposal_id"], "base_config_hash": "base"},
        )
    assert b.call(
        "validate_proposal",
        "operator",
        "operator",
        {"sandbox_id": sid, "proposal_id": proposal["proposal_id"], "base_config_hash": "base"},
    )
    with pytest.raises(ValueError):
        b.call(
            "validate_proposal",
            "operator",
            "operator",
            {"sandbox_id": sid, "proposal_id": proposal["proposal_id"], "base_config_hash": "different"},
        )
    w = b.call("read", "agent:alice", "agent", {"sandbox_id": sid})
    p = tmp_path / "rehearsal.zip"
    p.write_bytes(b.export(w))
    assert verify(p)["ok"]
    artifact = b.root / sid / job["job_id"] / "artifacts/stale_source.csv"
    artifact.write_text("damaged")
    with pytest.raises(ValueError):
        b.call(
            "validate_proposal",
            "operator",
            "operator",
            {"sandbox_id": sid, "proposal_id": proposal["proposal_id"], "base_config_hash": "base"},
        )
    with pytest.raises(ValueError):
        b.export(w)
    artifact.write_bytes(rehearsal_files["stale_source.csv"])
    b.call(
        "revise",
        "agent:alice",
        "agent",
        {"sandbox_id": sid, "expected_revision": 0, "document": value["document"]},
    )
    with pytest.raises(ValueError):
        b.call("propose", "agent:alice", "agent", {"sandbox_id": sid, "job_id": job["job_id"]})


def test_recording_copy_and_incomplete_draft(broker, value):  # type: ignore[no-untyped-def]
    import base64

    b, e = broker
    body = {
        "document": value["document"],
        "procedure": value["procedure"],
        "base_config_hash": "base",
        "recording": base64.b64encode(b"a,b\n1,2\n").decode(),
    }
    w = b.call("create", "agent:alice", "agent", body)
    sid = w["sandbox_id"]
    assert w["recording"]["bytes"] > 0
    b.call("run", "agent:alice", "agent", {"sandbox_id": sid, "kind": "python", "source": "not executed"})
    w = wait_job(b, sid)
    b.export(w)
    (b.root / sid / "recording.csv").write_bytes(b"changed")
    with pytest.raises(ValueError):
        b.export(w)
    value = copy.deepcopy(value)
    value["document"]["channels"][0]["calibration_id"] = ""
    w = create(b, value)
    with pytest.raises(ValueError):
        b.call("run", "agent:alice", "agent", {"sandbox_id": w["sandbox_id"], "kind": "rehearsal"})
    assert b.call(
        "run",
        "agent:alice",
        "agent",
        {"sandbox_id": w["sandbox_id"], "kind": "python", "source": "not executed"},
    )
    wait_job(b, w["sandbox_id"])
