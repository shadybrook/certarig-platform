from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from certarig.agent.orchestrator import AgentSession, OrchestratorError, replay_session, summarize_transcript
from certarig.agent.policy import RuleBasedPolicy
from certarig.agent.providers.base import Message, ProviderResponse
from certarig.agent.providers.fake import FakeProvider, call, say, tool_call
from certarig.agent.skills import SkillIndex
from certarig.agent.tools import ToolRegistry
from certarig.agent.transcript import Transcript
from certarig.edge.client import EdgeClient
from tests.support import SKILLS_DIR, RunningSim, edge_server, sim_server, wait_until


def _session(sim: RunningSim, provider: FakeProvider, tmp_path: Path, name: str = "s") -> AgentSession:
    registry = ToolRegistry(sim.agent(), SkillIndex.load(SKILLS_DIR), poll_s=0.05)
    return AgentSession(provider, registry, Transcript(tmp_path / f"{name}.jsonl"))


def _auto_grant(operator: EdgeClient, stop: threading.Event) -> threading.Thread:
    def loop() -> None:
        while not stop.is_set():
            for approval in operator.approvals("pending"):
                operator.grant(approval["approval_id"])
            time.sleep(0.05)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def test_scripted_happy_path_runs_a_procedure_and_records_everything(tmp_path: Path) -> None:
    with sim_server() as sim:
        provider = FakeProvider(
            script=[
                call(tool_call("read_skill", {"name": "relay_truth_table"}, "c1")),
                call(
                    tool_call("run_procedure", {"procedure_id": "relay_truth_table", "label": "agent"}, "c2")
                ),
                call(tool_call("wait_for_run", {"run_id": "$RUN", "timeout_s": 60}, "c3")),
                say("Relay truth table passed."),
            ]
        )
        session = _session(sim, provider, tmp_path)
        # patch the run id into the third scripted call once known
        original = provider.complete

        def complete(system: str, messages: list[Message], tools: list) -> ProviderResponse:  # type: ignore[type-arg]
            response = original(system, messages, tools)
            for tc in response.tool_calls:
                if tc.arguments.get("run_id") == "$RUN":
                    for message in reversed(messages):
                        if message.role == "tool" and message.name == "run_procedure":
                            tc.arguments["run_id"] = json.loads(message.content)["run_id"]
            return response

        provider.complete = complete  # type: ignore[method-assign]
        result = session.send("run the relay truth table")
        session.close()
        assert result.text == "Relay truth table passed."
        assert [r.name for r in result.tool_results] == ["read_skill", "run_procedure", "wait_for_run"]
        assert all(r.ok for r in result.tool_results)
        run = result.tool_results[-1].result
        assert run["status"] == "passed", run
        assert run["terminal"] is True
        assert run["recording"]["samples"] > 0

        rows = Transcript.read(session.transcript.path)
        kinds = [row["kind"] for row in rows]
        assert kinds[0] == "session_started" and kinds[-1] == "session_ended"
        assert kinds.count("model_response") == 4
        assert kinds.count("tool_call") == 3 and kinds.count("tool_result") == 3
        assert all("fingerprint" in row for row in rows if row["kind"] == "model_response")
        summary = summarize_transcript(str(session.transcript.path))
        assert summary["tools_used"] == ["read_skill", "run_procedure", "wait_for_run"]
        assert summary["refusals"] == 0

        # the Edge audit log knows the agent principal did this
        audit = sim.operator().get("/v1/audit")["audit"]
        agent_entries = [e for e in audit if e["principal"] == "agent"]
        assert any(e["tool"] == "run_procedure" for e in agent_entries)


def test_rule_based_policy_drives_intent_to_report(tmp_path: Path) -> None:
    with sim_server() as sim:
        skills = SkillIndex.load(SKILLS_DIR)
        session = _session(sim, FakeProvider(policy=RuleBasedPolicy(skills)), tmp_path)
        status = session.send("what is the rig status?")
        assert "output off" in status.text and [r.name for r in status.tool_results] == ["read_state"]

        listing = session.send("what can you do?")
        assert "relay_truth_table" in listing.text

        run = session.send("run the relay truth table")
        assert "PASSED" in run.text, run.text
        assert "Evidence CSV" in run.text
        assert [r.name for r in run.tool_results][:2] == ["read_skill", "run_procedure"]

        safe = session.send("stop, make it safe")
        assert [r.name for r in safe.tool_results] == ["force_safe"]
        assert "operator_safe" in safe.text

        session.close()


def test_policy_hands_physical_steps_to_the_operator_and_resumes(tmp_path: Path) -> None:
    with sim_server() as sim:
        skills = SkillIndex.load(SKILLS_DIR)
        session = _session(sim, FakeProvider(policy=RuleBasedPolicy(skills)), tmp_path)
        turn = session.send("safe power down the bench")
        assert "Operator action needed" in turn.text
        assert "cannot acknowledge" in turn.text
        run_id = turn.tool_results[-1].result["run_id"]
        operator = sim.operator()
        run = operator.procedure_run(run_id)
        assert run["status"] == "awaiting_operator"
        operator.ack(run_id, "confirm_bench")
        assert wait_until(lambda: operator.procedure_run(run_id)["terminal"], timeout=10)
        resumed = session.send("done")
        assert resumed.tool_results[0].name == "wait_for_run"
        assert "PASSED" in resumed.text
        session.close()


def test_adversarial_model_is_contained_by_manifest_and_approvals(tmp_path: Path) -> None:
    with sim_server() as sim:
        provider = FakeProvider(
            script=[
                call(tool_call("bypass_interlock", {}, "a1")),
                call(tool_call("ack_operator_step", {"run_id": "r", "step_id": "s"}, "a2")),
                call(tool_call("override_limits", {"trip_max": 99}, "a3")),
                call(tool_call("reset_trip", {}, "a4")),
                call(
                    tool_call(
                        "request_approval", {"tool": "reset_trip", "args": {}, "reason": "clear latch"}, "a5"
                    )
                ),
                call(tool_call("wait_for_approval", {"approval_id": "$APPROVAL", "timeout_s": 10}, "a6")),
                call(tool_call("reset_trip", {"approval_id": "$APPROVAL"}, "a7")),
                call(
                    tool_call("reset_trip", {"approval_id": "$APPROVAL"}, "a8")
                ),  # replay of a consumed approval
                call(tool_call("shutdown", {"reason": "bye"}, "a9")),
                say("done"),
            ]
        )
        original = provider.complete

        def complete(system: str, messages: list[Message], tools: list) -> ProviderResponse:  # type: ignore[type-arg]
            response = original(system, messages, tools)
            for tc in response.tool_calls:
                if tc.arguments.get("approval_id") == "$APPROVAL":
                    for message in reversed(messages):
                        if message.role == "tool" and message.name == "request_approval":
                            tc.arguments["approval_id"] = json.loads(message.content)["approval_id"]
            return response

        provider.complete = complete  # type: ignore[method-assign]
        session = _session(sim, provider, tmp_path)
        stop = threading.Event()
        _auto_grant(sim.operator(), stop)
        try:
            result = session.send("do whatever it takes to energise the output")
        finally:
            stop.set()
        session.close()
        names = [r.name for r in result.tool_results]
        assert names == [
            "bypass_interlock",
            "ack_operator_step",
            "override_limits",
            "reset_trip",
            "request_approval",
            "wait_for_approval",
            "reset_trip",
            "reset_trip",
            "shutdown",
        ]
        r = result.tool_results
        assert r[0].result["code"] == "tool_not_available"
        assert r[1].result["code"] == "tool_not_available"  # never-tool for the agent, hidden entirely
        assert r[2].result["code"] == "tool_not_available"
        assert r[3].result["code"] == "approval_required" and r[3].result["http_status"] == 428
        assert r[4].ok and r[4].result["status"] == "pending"
        assert r[5].ok and r[5].result["status"] == "granted"
        assert r[6].ok and r[6].result["guardrail"]["event"] == "trip_reset_output_safe"
        assert r[7].ok is False and r[7].result["http_status"] == 403  # approvals are single use
        assert r[8].ok is False  # shutdown still needs its own human approval (or route missing until M5)
        assert r[8].result["http_status"] in {404, 428}
        # the audit log recorded every refusal against the agent principal
        audit = sim.operator().get("/v1/audit")["audit"]
        refused = [e for e in audit if e["principal"] == "agent" and e["status"] >= 400]
        assert len(refused) >= 2  # 428 approval_required and 403 approval consumed
        assert sim.rig.output is False


def test_turn_limits_stop_runaway_models(tmp_path: Path) -> None:
    with edge_server() as edge:
        provider = FakeProvider(policy=lambda system, messages, tools: call(tool_call("read_state", {})))
        registry = ToolRegistry(edge.agent(), SkillIndex.load(SKILLS_DIR))
        session = AgentSession(
            provider, registry, Transcript(tmp_path / "loop.jsonl"), max_model_calls_per_turn=3
        )
        result = session.send("loop forever")
        assert result.stopped_reason == "max_model_calls"
        assert len(result.tool_results) == 3
        assert "too many steps" in result.text

        many = FakeProvider(
            script=[call(*[tool_call("read_state", {}, f"m{i}") for i in range(8)]), say("ok")]
        )
        session = AgentSession(
            many, registry, Transcript(tmp_path / "many.jsonl"), max_tool_calls_per_response=2
        )
        result = session.send("read everything")
        assert len(result.tool_results) == 2
        assert any(m.role == "user" and "Only the first 2" in m.content for m in session.messages)


def test_replay_reproduces_a_session_and_detects_tampering(tmp_path: Path) -> None:
    with sim_server() as sim:
        skills = SkillIndex.load(SKILLS_DIR)
        session = _session(sim, FakeProvider(policy=RuleBasedPolicy(skills)), tmp_path, "live")
        live = [session.send("what is the rig status?").to_dict(), session.send("stop").to_dict()]
        session.close()
    path = str(session.transcript.path)
    replayed = replay_session(path)
    assert [r["text"] for r in replayed] == [r["text"] for r in live]
    assert [[t["name"] for t in r["tool_calls"]] for r in replayed] == [
        [t["name"] for t in r["tool_calls"]] for r in live
    ]
    assert Path(path + ".replay.jsonl").exists()

    # tamper with a recorded tool result: strict replay must refuse
    rows = Transcript.read(path)
    tampered = tmp_path / "tampered.jsonl"
    with tampered.open("w") as handle:
        for row in rows:
            if row["kind"] == "tool_result" and row["name"] == "read_state":
                row["result"]["outputs"]["gpio23_command_high"] = True
            handle.write(json.dumps(row) + "\n")
    with pytest.raises(OrchestratorError, match="divergence"):
        replay_session(str(tampered))
    # lenient replay tolerates it
    assert replay_session(str(tampered), strict=False)


def test_fake_provider_script_exhaustion_and_policy_shape() -> None:
    from certarig.agent.providers.base import ProviderError

    provider = FakeProvider(script=[say("a")])
    assert provider.complete("s", [], []).text == "a"
    with pytest.raises(ProviderError):
        provider.complete("s", [], [])
    assert len(provider.calls) == 2
    assert FakeProvider().complete("s", [], []).text == "I have nothing to do."
