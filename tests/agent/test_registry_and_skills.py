from __future__ import annotations

import pytest

from certarig.agent.skills import SkillIndex
from certarig.agent.tools import LOCAL_TOOLS, ToolRegistry
from tests.support import SKILLS_DIR, edge_server


def test_skill_index_loads_front_matter_and_matches_intents() -> None:
    index = SkillIndex.load(SKILLS_DIR)
    names = {skill["name"] for skill in index.list()}
    assert {
        "pressure_guardrail",
        "estop_anti_restart",
        "relay_truth_table",
        "adc_validation",
        "safe_powerdown",
        "flow_guardrail",
        "dual_pot_guardrail",
    } <= names
    skill = index.get("pressure_guardrail")
    assert skill is not None
    assert skill.procedure_id == "pressure_guardrail"
    assert skill.domain == "process"
    best, score = index.match("please verify the pressure guardrail trips")[0]
    assert best.name == "pressure_guardrail"
    assert score >= 0.5
    assert "pressure_guardrail" in index.prompt_index()
    assert index.match("zzz qqq") == []


def test_registry_only_exposes_manifest_tools_and_never_forbidden_ones() -> None:
    with edge_server() as edge:
        registry = ToolRegistry(edge.agent(), SkillIndex.load(SKILLS_DIR))
        names = {spec.name for spec in registry.specs()}
        assert set(LOCAL_TOOLS) <= names
        assert {"read_state", "run_procedure", "force_safe", "reset_trip"} <= names
        # never-tools for the agent do not exist as far as the model is concerned
        assert "ack_operator_step" not in names
        assert "bypass_interlock" not in names
        assert "override_limits" not in names
        assert registry.policies["reset_trip"] == "human_approval"
        assert "approval_id" in registry.edge_tools["reset_trip"].parameters["properties"]

        # unknown tools return a structured refusal, never raise
        result = registry.execute("bypass_interlock", {})
        assert result.ok is False
        assert result.result["code"] == "tool_not_available"
        assert "bypass_interlock" not in result.result["available_tools"]

        # bad arguments are also structured
        bad = registry.execute("read_procedure_run", {})
        assert bad.ok is False and bad.result["code"] == "bad_arguments"

        # results are bounded in size
        state = registry.execute("read_state", {})
        assert state.ok and "history" not in state.result
        assert len(state.content()) < 12_500


def test_registry_reports_edge_refusals_with_hints() -> None:
    with edge_server() as edge:
        registry = ToolRegistry(edge.agent(), SkillIndex.load(SKILLS_DIR))
        # human approval required
        result = registry.execute("reset_trip", {})
        assert result.ok is False
        assert result.result["http_status"] == 428
        assert result.result["code"] == "approval_required"
        assert "request_approval" in result.result["hint"]
        # allowed
        safe = registry.execute("force_safe", {})
        assert safe.ok is True
        assert safe.result["guardrail"]["event"] == "operator_safe"
        # never for agent (route exists, manifest says never) -> 403 structured
        registry.edge_tools["ack_operator_step"] = LOCAL_TOOLS[
            "read_skill"
        ]  # pretend the model hallucinated it
        denied = registry.execute("ack_operator_step", {"run_id": "x", "step_id": "y"})
        assert denied.ok is False
        assert denied.result["http_status"] == 403


def test_read_skill_unknown_gives_suggestions() -> None:
    with edge_server() as edge:
        registry = ToolRegistry(edge.agent(), SkillIndex.load(SKILLS_DIR))
        result = registry.execute("read_skill", {"name": "pressure guard"})
        assert result.ok
        assert result.result["error"] == "skill not found"
        assert "pressure_guardrail" in result.result["suggestions"]
        full = registry.execute("read_skill", {"name": "relay_truth_table"})
        assert "guidance" in full.result and full.result["procedure_id"] == "relay_truth_table"


@pytest.mark.parametrize("name", sorted(LOCAL_TOOLS))
def test_local_tool_specs_are_valid_json_schema_objects(name: str) -> None:
    spec = LOCAL_TOOLS[name]
    assert spec.parameters["type"] == "object"
    assert spec.description
