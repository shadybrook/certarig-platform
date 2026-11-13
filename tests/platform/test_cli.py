"""CLI initialization and service-lifecycle cleanup with no real deployment."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from certarig.edge.cli import build_parser
from certarig.platform import cli, evidence
from certarig.platform.store import Store

from .test_lifecycle import deployed


def test_bootstrap_generates_distinct_private_credentials_and_preserves_existing(tmp_path):
    root = tmp_path / "proof"
    result = cli.initialize(root, Path(__file__).resolve().parents[2])
    assert result["qualification"] == "not_run"
    store = Store(root)
    try:
        configs = store.secret("settings")["connectors"]
        assert configs["thermal"]["auditor_key"] != configs["pressure"]["auditor_key"]
        assert not (root / "settings.json").stat().st_mode & 0o077
        assert (root / "dex.yaml").stat().st_mode & 0o077 == 0
        accounts = store.secret("demo_accounts")["accounts"]
        assert {a["role"] for a in accounts} == {"author", "reviewer"}
        assert accounts[0]["password"] != accounts[1]["password"]
        with pytest.raises(ValueError, match="preserved"):
            cli.initialize(root, Path("."))
    finally:
        store.close()
    parser = build_parser()
    assert parser.parse_args(["platform", "serve", "--root", str(root)]).func is cli.run
    with pytest.raises(ValueError):
        cli.providers(root)({"backend": "fixture", "model": "not-available"})
    assert cli.providers(root)({"backend": "fixture", "model": "deterministic/1"}).name == "fixture"


def test_cli_init_and_verify(lab, tmp_path, capsys):
    cli.run(argparse.Namespace(root=str(tmp_path / "initialized"), action="init-demo"))
    assert json.loads(capsys.readouterr().out)["qualification"] == "not_run"
    d = deployed(lab)
    bundle = tmp_path / "export.zip"
    bundle.write_bytes(evidence.export(lab.p, lab.author, d["id"]))
    cli.run(argparse.Namespace(root=str(tmp_path / "unused"), action="verify", bundle=str(bundle)))
    assert json.loads(capsys.readouterr().out)["valid"]


def test_local_control_plane_and_runtime_cleanup_without_execution(tmp_path, monkeypatch, capsys):
    root = tmp_path / "services"
    cli.initialize(root, Path("."))
    seen = []

    class Endpoint:
        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            seen.append("server_closed")

    monkeypatch.setattr(cli, "server", lambda *args: Endpoint())
    cli.run(argparse.Namespace(root=str(root), action="serve"))
    assert "server_closed" in seen

    class Managed:
        def __init__(self, *args):
            seen.append("runtime_created")

        def serve(self):
            raise KeyboardInterrupt

        def close(self):
            seen.append("runtime_closed")

    monkeypatch.setattr(cli, "Runtime", Managed)
    cli.run(argparse.Namespace(root=str(root), action="runtime"))
    assert "runtime_closed" in seen
    assert "no deployments resumed" in capsys.readouterr().out


def test_demo_edges_have_separate_settings_and_safe_cleanup(tmp_path, monkeypatch):
    root = tmp_path / "edges"
    cli.initialize(root, Path("."))
    seen = []

    class Node:
        config = SimpleNamespace(hardware=SimpleNamespace(mode="simulator"))

        def start(self):
            seen.append("started")

        def close(self):
            seen.append("closed")

    class Endpoint:
        def serve_forever(self):
            return None

        def shutdown(self):
            seen.append("shutdown")

        def server_close(self):
            return None

    def build(settings):
        assert settings.auditor_key and settings.agent_key is None and not settings.allow_output
        seen.append(settings.auditor_key)
        return Node()

    monkeypatch.setattr(cli, "build_node", build)
    monkeypatch.setattr(cli, "make_edge_server", lambda *args: Endpoint())

    class Stop:
        def wait(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(
        cli, "threading", SimpleNamespace(Event=Stop, Thread=lambda **kw: SimpleNamespace(start=lambda: None))
    )
    cli.run(argparse.Namespace(root=str(root), action="demo-edges"))
    assert seen.count("started") == 2 and seen.count("closed") == 2
