"""CLI wiring tests: every sub-command parses and its handler runs in-process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from certarig.edge.cli import build_parser, main
from tests.support import AGENT_KEY, OPERATOR_KEY, SKILLS_DIR, sim_server

RELAY_HAPPY = SKILLS_DIR / "electronics" / "relay_truth_table" / "scenarios" / "happy_path.yaml"


class _OneShotServer:
    """Stands in for ThreadingHTTPServer: serve_forever returns immediately."""

    def __init__(self, real: Any) -> None:
        self.real = real
        self.server_port = real.server_port
        self.closed = False

    def serve_forever(self) -> None:
        raise KeyboardInterrupt

    def server_close(self) -> None:
        self.closed = True
        self.real.server_close()


def test_parser_covers_every_subcommand() -> None:
    parser = build_parser()
    edge = parser.parse_args(["edge", "serve", "--port", "0", "--no-studio"])
    assert edge.command == "edge" and edge.edge_command == "serve" and edge.no_studio
    legacy = parser.parse_args(["edge", "legacy-plan-api"])
    assert legacy.port == 8081
    sim = parser.parse_args(["sim", "run", str(RELAY_HAPPY), "--verbose"])
    assert sim.sim_command == "run" and sim.verbose
    lib = parser.parse_args(["sim", "run-library", "--out", "/tmp/x", "--filter", "relay"])
    assert lib.filter == "relay"
    agent = parser.parse_args(["agent", "run", "--url", "http://x", "hello"])
    assert agent.provider == "fake" and agent.intent == "hello"
    replay = parser.parse_args(["agent", "replay", "t.jsonl", "--lenient"])
    assert replay.lenient
    with pytest.raises(SystemExit):
        parser.parse_args(["nope"])


def test_sim_run_and_run_library(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["sim", "run", str(RELAY_HAPPY), "--out", str(tmp_path / "one")])
    brief = json.loads(capsys.readouterr().out)
    assert brief["passed"] is True and brief["outcome"] == "passed"
    main(["sim", "run", str(RELAY_HAPPY), "--verbose"])
    assert json.loads(capsys.readouterr().out)["name"]
    main(
        [
            "sim",
            "run-library",
            "--out",
            str(tmp_path / "lib"),
            "--filter",
            "relay_truth_table/scenarios/happy",
        ]
    )
    out = capsys.readouterr().out
    assert "[PASS]" in out and "1/1 scenarios passed" in out
    summary = json.loads((tmp_path / "lib" / "library_summary.json").read_text())
    assert summary[0]["passed"] is True


def test_sim_run_exits_nonzero_on_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scenario = tmp_path / "doomed.yaml"
    scenario.write_text(
        "name: doomed\nseed: 1\nprocedure: relay_truth_table\nduration_s: 30\nevents: []\n"
        "expect:\n  outcome: failed\n  invariants: [ends_safe]\n"
    )
    with pytest.raises(SystemExit) as exc:
        main(["sim", "run", str(scenario)])
    assert exc.value.code == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False


def test_agent_run_chat_and_replay(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    with sim_server() as sim:
        common = [
            "--url", sim.url, "--agent-key", AGENT_KEY, "--skills-root", str(SKILLS_DIR),
            "--transcript-dir", str(tmp_path), "--verbose",
        ]  # fmt: skip
        main(["agent", "run", *common, "what is the status?"])
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["tool_calls"][0]["name"] == "read_state"
        assert "→ read_state" in captured.err
        transcript = result["transcript"]

        prompts = iter(["run the relay truth table", "", EOFError()])

        def fake_input(_: str) -> str:
            item = next(prompts)
            if isinstance(item, BaseException):
                raise item
            return item

        monkeypatch.setattr("builtins.input", fake_input)
        main(["agent", "chat", *common])
        out = capsys.readouterr().out
        assert "agent> Procedure relay_truth_table PASSED" in out

    main(["agent", "replay", transcript])
    replayed = json.loads(capsys.readouterr().out)
    assert replayed["summary"]["tools_used"] == ["read_state"]
    assert replayed["replayed_turns"][0]["tool_calls"][0]["name"] == "read_state"


def test_agent_requires_key_and_author_needs_real_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CERTARIG_AGENT_KEY", raising=False)
    with pytest.raises(SystemExit, match="CERTARIG_AGENT_KEY"):
        main(["agent", "run", "--url", "http://127.0.0.1:1", "hi"])
    with sim_server() as sim:
        with pytest.raises(SystemExit, match="real model provider"):
            main(["agent", "author", "--url", sim.url, "--agent-key", AGENT_KEY, "make a thing"])
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit, match="ANTHROPIC_API_KEY"):
            main(
                ["agent", "run", "--url", sim.url, "--agent-key", AGENT_KEY, "--provider", "anthropic", "hi"]
            )


def test_edge_serve_and_sim_serve_boot_and_shut_down(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import certarig.edge.cli as edge_cli

    real = edge_cli.make_edge_server
    monkeypatch.setattr(
        edge_cli, "make_edge_server", lambda node, host, port: _OneShotServer(real(node, host, port))
    )
    monkeypatch.setenv("CERTARIG_OPERATOR_KEY", OPERATOR_KEY)
    monkeypatch.setenv("CERTARIG_AGENT_KEY", AGENT_KEY)
    main(
        [
            "edge",
            "serve",
            "--config",
            "config/rig.example.json",
            "--port",
            "0",
            "--evidence-dir",
            str(tmp_path / "e"),
        ]
    )
    started = json.loads(capsys.readouterr().out)
    assert started["event"] == "certarig_edge_started"
    assert started["hardware_mode"] == "mock" and "relay_truth_table" in started["procedures"]

    main(["sim", "serve", "--port", "0", "--evidence-dir", str(tmp_path / "s")])
    started = json.loads(capsys.readouterr().out)
    assert started["hardware_mode"] == "simulator" and started["agent_principal_enabled"] is True


def test_legacy_plan_api_boots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import certarig.edge.cli as edge_cli

    real = edge_cli.make_server
    monkeypatch.setattr(
        edge_cli, "make_server", lambda app, host, port: _OneShotServer(real(app, host, port))
    )
    monkeypatch.delenv("CERTARIG_OPERATOR_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["edge", "legacy-plan-api"])
    monkeypatch.setenv("CERTARIG_OPERATOR_KEY", OPERATOR_KEY)
    main(["edge", "legacy-plan-api", "--port", "0", "--database", str(tmp_path / "e.sqlite3")])
    assert json.loads(capsys.readouterr().out)["event"] == "certarig_legacy_plan_api_started"


def test_namespace_shape_for_sim_serve_matches_serve() -> None:
    import inspect

    from certarig.sim.cli import sim_serve

    assert "func" not in inspect.signature(sim_serve).parameters
    assert isinstance(argparse.Namespace(), argparse.Namespace)
