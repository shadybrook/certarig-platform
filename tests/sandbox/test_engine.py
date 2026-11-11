"""Mocked Docker protocol tests: no container or submitted host code is executed."""

from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

import certarig.sandbox.engine as module
from certarig.sandbox.engine import DockerEngine, collect_archive, resource_preflight

IMAGE = "sha256:" + "1" * 64


def result(stdout=b"", code=0, stderr=b""):  # type: ignore[no-untyped-def]
    return subprocess.CompletedProcess([], code, stdout, stderr)


def output():  # type: ignore[no-untyped-def]
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        folder = tarfile.TarInfo("out")
        folder.type = tarfile.DIRTYPE
        tar.addfile(folder)
        raw = b'{"exit_code":0}'
        record = tarfile.TarInfo("out/worker_record.json")
        record.size = len(raw)
        tar.addfile(record, io.BytesIO(raw))
    return stream.getvalue()


def test_resource_probe_errors(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(module.shutil, "disk_usage", lambda _: SimpleNamespace(free=9 * 1024**3))
    monkeypatch.setattr(module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(module, "command", lambda *a, **k: result(b"2"))
    assert not resource_preflight(tmp_path)["ready"]
    monkeypatch.setattr(module, "command", lambda *a, **k: result(b"unknown"))
    assert not resource_preflight(tmp_path)["ready"]
    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    assert not resource_preflight(tmp_path)["ready"]
    monkeypatch.setattr(module, "command", lambda *a, **k: result())
    assert module.command([]).returncode == 0


def test_engine_preflight_and_cleanup(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    (tmp_path / "image.id").write_text(IMAGE)
    engine = DockerEngine(IMAGE, tmp_path)
    monkeypatch.setattr(module, "resource_preflight", lambda _: dict(ready=True, blockers=[]))

    def execute(args, timeout=10):
        if args[:3] == ["docker", "context", "inspect"]:
            return result(
                json.dumps(
                    [
                        {
                            "Endpoints": {
                                "docker": {
                                    "Host": "unix://"
                                    + str(Path.home() / ".colima/certarig-sandbox/docker.sock")
                                }
                            }
                        }
                    ]
                ).encode()
            )
        if args[0] == "colima":
            return result(code=1)
        if "info" in args:
            return result(
                json.dumps(
                    {
                        "SecurityOptions": ["name=seccomp"],
                        "MemoryLimit": True,
                        "PidsLimit": True,
                        "SwapLimit": True,
                    }
                ).encode()
            )
        return result(
            json.dumps(
                [
                    {
                        "Architecture": "arm64",
                        "Os": "linux",
                        "Config": {"Labels": {"org.certarig.sandbox": "v1"}},
                    }
                ]
            ).encode()
        )

    monkeypatch.setattr(module, "command", execute)
    assert not engine.preflight()["ready"]  # no real-container qualification record
    (tmp_path / "runtime-tests.xml").write_bytes(b"mocked unit-test report, not isolation qualification")
    (tmp_path / "qualification.json").write_text(
        json.dumps(
            {
                "image": IMAGE,
                "passed": True,
                "suite": "sandbox-runtime-v1",
                "cases": sorted(module.RUNTIME_CASES),
                "policy_sha256": module.policy_hash(),
                "report_sha256": module.hashlib.sha256(
                    (tmp_path / "runtime-tests.xml").read_bytes()
                ).hexdigest(),
            }
        )
    )
    assert engine.preflight()["ready"]
    (tmp_path / "image.id").write_text("different")
    assert not engine.preflight()["ready"]
    monkeypatch.setattr(module, "command", lambda *a, **k: result(b"not-json"))
    assert not engine.preflight()["ready"]
    with pytest.raises(ValueError):
        engine.cleanup("unrelated")
    monkeypatch.setattr(engine, "docker", lambda *a, **k: result(code=1))
    engine.cleanup("crsb-job_" + "1" * 16)
    monkeypatch.setattr(engine, "docker", lambda *a, **k: result(b'[{"Config":{"Labels":{}}}]'))
    with pytest.raises(ValueError, match="unrelated"):
        engine.cleanup("crsb-job_" + "1" * 16)
    calls = []

    def owned(*args, **kwargs):
        calls.append(args)
        return result(
            json.dumps(
                [
                    {
                        "Config": {
                            "Labels": {
                                "org.certarig.sandbox": "v1",
                                "org.certarig.root": str(tmp_path.resolve()),
                            }
                        }
                    }
                ]
            ).encode()
        )

    monkeypatch.setattr(engine, "docker", owned)
    engine.cleanup("crsb-job_" + "1" * 16)
    assert any(a[0] == "rm" for a in calls)


@pytest.mark.parametrize(
    "mode", ["complete", "cancel", "timeout", "exited", "create_failed", "pause_failed", "copy_failed"]
)
def test_engine_state_protocol(tmp_path, monkeypatch, mode):  # type: ignore[no-untyped-def]
    engine = DockerEngine(IMAGE, tmp_path)
    commands = []
    monkeypatch.setattr(engine, "preflight", lambda: {"ready": True})
    monkeypatch.setattr(engine, "cleanup", lambda name: commands.append(("cleanup", name)))
    fake_timer = SimpleNamespace(daemon=False, start=lambda: None, cancel=lambda: None)
    monkeypatch.setattr(module, "Timer", lambda *a, **k: fake_timer)

    class Process:
        stdin = io.BytesIO()

        def wait(self, timeout=5):
            return 0

        def kill(self):
            pass

    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: Process())

    def docker(*args, **kwargs):
        commands.append(args)
        if args[0] == "create":
            return result(code=1 if mode == "create_failed" else 0, stderr=b"creation refused")
        if args[0] == "inspect":
            return result(
                json.dumps({"Running": mode != "exited", "ExitCode": 0, "OOMKilled": False}).encode()
            )
        if args[0] == "pause":
            return result(code=1 if mode == "pause_failed" else 0)
        if args[0] == "cp":
            return result(output(), code=1 if mode == "copy_failed" else 0)
        if args[0] == "logs":
            return result(b"worker log", stderr=b"stderr retained")
        return result()

    monkeypatch.setattr(engine, "docker", docker)
    event = Event()
    if mode == "cancel":
        event.set()
    if mode == "timeout":
        moments = iter([0, 0.1, 2, 3])
        monkeypatch.setattr(module.time, "monotonic", lambda: next(moments))
    if mode.endswith("failed"):
        with pytest.raises(RuntimeError):
            engine.run("job_" + "2" * 16, "python", {"main.py": b"never run on host"}, 1, event)
    else:
        observed = engine.run("job_" + "2" * 16, "python", {"main.py": b"never run on host"}, 1, event)
        assert (
            observed["status"]
            == {"complete": "completed", "cancel": "cancelled", "timeout": "timed_out", "exited": "failed"}[
                mode
            ]
        )
        assert b"stderr retained" in observed["files"]["worker.log"]
    assert commands[-1][0] == "cleanup"
    assert any("timeout" in c for c in commands if c[0] == "create")


def test_refused_run_and_archives(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    engine = DockerEngine(IMAGE, tmp_path)
    monkeypatch.setattr(engine, "preflight", lambda: {"ready": False, "blockers": ["blocked"]})
    with pytest.raises(RuntimeError, match="blocked"):
        engine.run("job_" + "2" * 16, "python", {}, 1, Event())
    monkeypatch.setattr(engine, "preflight", lambda: {"ready": True})
    with pytest.raises(ValueError):
        engine.run("job_" + "2" * 16, "python", {"../bad": b""}, 1, Event())
    assert collect_archive(output())["worker_record.json"]
