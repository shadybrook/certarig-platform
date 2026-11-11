"""Trusted CLI/worker protocol unit tests; submitted Python is always a mocked subprocess."""

from __future__ import annotations

import argparse
import base64
import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from certarig.sandbox import cli, worker
from certarig.sandbox.contracts import encoded


def test_cli_preflight_and_verify(tmp_path, monkeypatch, capsys):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "resource_preflight", lambda p: {"ready": True, "blockers": []})
    args = SimpleNamespace(root=str(tmp_path), sandbox_command="preflight")
    cli.main_action(args)
    assert "not been built" in capsys.readouterr().out
    monkeypatch.setattr(cli, "verify", lambda p: {"ok": True})
    args.sandbox_command = "verify"
    args.bundle = "not-read.zip"
    cli.main_action(args)
    monkeypatch.setattr(cli, "verify", lambda p: {"ok": False})
    with pytest.raises(SystemExit):
        cli.main_action(args)
    parser = argparse.ArgumentParser()
    cli.add_parser(parser.add_subparsers())
    assert parser.parse_args(["sandbox", "preflight"]).sandbox_command == "preflight"
    (tmp_path / "image.id").write_text("sha256:" + "a" * 64)
    monkeypatch.setattr(
        cli,
        "DockerEngine",
        lambda *a, **k: SimpleNamespace(preflight=lambda: {"ready": False, "blockers": ["test-double"]}),
    )
    args.sandbox_command = "preflight"
    cli.main_action(args)
    args.sandbox_command = "qualify"
    with pytest.raises(SystemExit):
        cli.main_action(args)
    monkeypatch.setattr(
        cli, "resource_preflight", lambda p: {"ready": False, "blockers": ["insufficient resources"]}
    )
    with pytest.raises(SystemExit):
        cli.prepare(args)


def test_prepare_build_protocol_only(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    # No Colima/Docker command is actually executed.
    monkeypatch.setattr(cli, "resource_preflight", lambda p: {"ready": True, "blockers": []})
    commands = []
    monkeypatch.setattr(
        cli,
        "command",
        lambda args, **k: commands.append(args) or subprocess.CompletedProcess(args, 0, b"", b""),
    )

    def build(args, **kwargs):
        assert ".venv" not in {p.name for p in Path(args[-1]).iterdir()}
        Path(args[args.index("--iidfile") + 1]).write_text("sha256:" + "a" * 64)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(cli.subprocess, "run", build)
    monkeypatch.setattr(
        cli,
        "DockerEngine",
        lambda *a, **k: SimpleNamespace(preflight=lambda: {"ready": True, "blockers": []}),
    )
    cli.prepare(SimpleNamespace(root=str(tmp_path / "private")))
    assert "--activate=false" in commands[0] and "--mount" in commands[0] and "none" in commands[0]
    assert (tmp_path / "private/image.id").stat().st_mode & 0o077 == 0


def test_broker_serve_cleanup(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    (tmp_path / "image.id").write_text("sha256:" + "a" * 64)
    closed = []
    monkeypatch.setattr(cli, "DockerEngine", lambda *a, **k: object())
    monkeypatch.setattr(cli, "Broker", lambda *a, **k: SimpleNamespace(close=lambda: closed.append("broker")))

    def interrupted(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        cli,
        "server",
        lambda *a, **k: SimpleNamespace(
            serve_forever=interrupted, server_close=lambda: closed.append("listener")
        ),
    )
    cli.main_action(
        SimpleNamespace(root=str(tmp_path), sandbox_command="serve", socket=str(tmp_path / "socket"))
    )
    assert closed == ["listener", "broker"]


@pytest.mark.parametrize("kind", ["python", "spice", "rehearsal", "unsupported", "failed"])
def test_worker_protocol_no_host_execution(tmp_path, monkeypatch, kind):  # type: ignore[no-untyped-def]
    out = tmp_path / "out"
    out.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    original = Path
    monkeypatch.setattr(
        worker, "Path", lambda p: out if p == "/out" else scratch if p == "/scratch" else original(p)
    )
    monkeypatch.setenv("CERTARIG_SANDBOX_WORKER", "1")
    payload = {
        "snapshot.json": encoded({}),
        "main.py": b"untrusted code is never executed by this test",
        "circuit.cir": b"untrusted deck is never executed by this test",
    }
    incoming = encoded({k: base64.b64encode(v).decode() for k, v in payload.items()})
    monkeypatch.setattr(worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(incoming)))
    monkeypatch.setattr(worker.sys, "argv", ["worker", kind, "1"])

    def terminate(_):
        raise SystemExit

    monkeypatch.setattr(worker.time, "sleep", terminate)

    def fake_run(args, **kwargs):
        if kind == "failed" and args[0] != "ngspice":
            raise RuntimeError("test failure")
        return SimpleNamespace(returncode=0, stdout=b"ngspice-47")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    monkeypatch.setattr(worker, "rehearse", lambda *a, **k: None)
    with pytest.raises(SystemExit):
        worker.main()
    meta = json.loads((out / "worker_record.json").read_text())
    assert meta["qualification_claim"] is False
    assert (scratch / "worker.done").exists()
    if kind == "unsupported":
        assert meta["exit_code"] == 1


def test_worker_host_refusal(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CERTARIG_SANDBOX_WORKER", raising=False)
    with pytest.raises(SystemExit, match="container-only"):
        worker.main()


@pytest.mark.parametrize("success", [True, False])
def test_qualify_requires_the_complete_unskipped_suite(tmp_path, monkeypatch, success):  # type: ignore[no-untyped-def]
    # Mocked report parsing only. No runtime/container is qualified by this test.
    (tmp_path / "image.id").write_text("sha256:" + "a" * 64)
    monkeypatch.setattr(
        cli,
        "DockerEngine",
        lambda *a, **k: SimpleNamespace(preflight=lambda: {"ready": True, "blockers": []}),
    )

    def fake_pytest(args, **kwargs):
        report = Path(args[args.index("--junitxml") + 1])
        report.write_text(
            "<testsuites><testsuite>"
            + "".join(
                f'<testcase name="{name}">' + ("" if success else "<skipped/>") + "</testcase>"
                for name in cli.RUNTIME_CASES
            )
            + "</testsuite></testsuites>"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_pytest)
    args = SimpleNamespace(root=str(tmp_path), sandbox_command="qualify")
    if success:
        cli.main_action(args)
    else:
        with pytest.raises(SystemExit, match="failed"):
            cli.main_action(args)
    assert json.loads((tmp_path / "qualification.json").read_text())["passed"] is success
