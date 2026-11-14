"""Additive authenticated workbench routes. Identity is always server-derived."""

from __future__ import annotations

from typing import Any

from . import evidence, teams
from .store import Actor
from .workbench import TEMPLATES


def route(api: Any, actor: Actor, method: str, parts: list[str], body: dict[str, Any]) -> tuple[bool, Any]:
    p, w = api.platform, api.workbench
    if parts == ["bench-specs"]:
        return True, {"specs": api.bench_specs.listing(actor)} if method == "GET" else api.bench_specs.create(
            actor, body
        )
    if len(parts) >= 2 and parts[0] == "bench-specs":
        if len(parts) == 2 and method == "GET":
            return True, api.bench_specs.get(actor, parts[1])
        if method == "POST" and len(parts) == 3:
            if parts[2] == "revise":
                return True, api.bench_specs.revise(actor, parts[1], body)
            if parts[2] == "assess" and not body:
                return True, api.bench_specs.assess(actor, parts[1])
            if parts[2] == "propose":
                return True, api.bench_specs.propose(actor, parts[1], body)
            if parts[2] == "review":
                return True, api.bench_specs.review(actor, parts[1], body)
    if parts == ["connectors", "registered"] and method == "GET":
        from .connectors import registered

        return True, {"connectors": registered(p, actor)}
    if parts == ["workbench-tools"] and method == "GET":
        from .workbench_tools import WorkbenchRegistry

        return True, {
            "tools": [
                dict(name=t.name, description=t.description, parameters=t.parameters)
                for t in WorkbenchRegistry(api, actor).specs()
            ]
        }
    if parts == ["templates"] and method == "GET":
        return True, {
            "templates": [
                {"id": k, "instructions": v, "backend": "deterministic_drafting"}
                for k, v in TEMPLATES.items()
            ]
        }
    if parts == ["projects"]:
        return True, {"projects": w.listing(actor, "project")} if method == "GET" else w.project(actor, body)
    if parts == ["drafts"]:
        return True, {"drafts": w.listing(actor, "draft")} if method == "GET" else w.draft(actor, body)
    if len(parts) >= 2 and parts[0] == "drafts":
        if len(parts) == 2:
            return True, w.inspect(actor, parts[1]) if method == "GET" else w.update(actor, parts[1], body)
        if parts[2:] == ["commit"] and method == "POST":
            return True, w.commit(actor, parts[1], body["expected_revision"])
    if parts == ["tasks"]:
        return True, {"tasks": api.tasks.listing(actor)} if method == "GET" else api.tasks.submit(actor, body)
    if len(parts) >= 2 and parts[0] == "tasks":
        if len(parts) == 2 and method == "GET":
            return True, api.tasks.get(actor, parts[1])
        if parts[2:] == ["events"] and method == "POST":
            return True, api.tasks.events(actor, parts[1], body.get("after", 0))
        if parts[2:] == ["cancel"] and method == "POST":
            return True, api.tasks.cancel(actor, parts[1])
    if parts == ["teams"]:
        return True, {
            "teams": [v for v in p.versions(actor) if v.get("team_members")]
        } if method == "GET" else teams.create(p, actor, body)
    if parts == ["tools"]:
        return True, {
            "tools": api.analysis.listing(actor, "analysis_tool")
        } if method == "GET" else api.analysis.create(actor, body)
    if len(parts) >= 2 and parts[0] == "tools":
        if len(parts) == 2 and method == "GET":
            return True, api.analysis.get(actor, "analysis_tool", parts[1])
        if method == "GET" and parts[2:] == ["tests"]:
            api.analysis.get(actor, "analysis_tool", parts[1])
            return True, {
                "tests": [t for t in api.analysis.listing(actor, "tool_test") if t["tool_id"] == parts[1]]
            }
        if method == "POST":
            if parts[2:] == ["test"]:
                return True, api.analysis.test(actor, parts[1])
            if parts[2:] == ["review"]:
                return True, api.analysis.review(actor, parts[1], body["test_id"])
            if parts[2:] == ["run"]:
                return True, api.analysis.run(
                    actor, parts[1], body["inputs"], replay_id=body.get("replay_id")
                )
    if parts == ["analyses"] and method == "GET":
        return True, {"analyses": api.analysis.listing(actor, "analysis")}
    if len(parts) >= 2 and parts[0] == "analyses":
        if len(parts) == 2 and method == "GET":
            return True, api.analysis.inspect(actor, parts[1])
        if parts[2:] == ["artifact"] and method == "POST":
            return True, api.analysis.artifact(actor, parts[1], body["name"])
        if parts[2:] == ["cancel"] and method == "POST":
            return True, api.analysis.cancel(actor, parts[1])
    if parts == ["replays"]:
        return True, {
            "replays": api.analysis.listing(actor, "replay")
        } if method == "GET" else api.analysis.import_run(actor, body)
    if parts == ["connector-profiles"]:
        return True, {
            "profiles": w.listing(actor, "connector_profile")
        } if method == "GET" else api.connector_profiles.create(actor, body)
    if len(parts) >= 2 and parts[0] == "connector-profiles":
        if len(parts) == 2 and method == "GET":
            return True, api.connector_profiles.get(actor, parts[1])
        if parts[2:] == ["review"] and method == "POST":
            return True, api.connector_profiles.review(actor, parts[1])
    if parts == ["evidence"] and method == "GET":
        return True, {
            "evidence": [
                {
                    "id": d["id"],
                    "asset_id": d["asset_id"],
                    "version_id": d["version_id"],
                    "status": d["status"],
                    "observations": d["assessments"],
                    "backend": d["binding"]["backend"],
                    "verification": "verify_export_to_check_integrity",
                }
                for d in p.deployments(actor)
            ]
        }
    if len(parts) == 3 and parts[0] == "evidence" and parts[2] == "verify" and method == "POST":
        return True, evidence.verify(evidence.export(p, actor, parts[1]))
    return False, None
