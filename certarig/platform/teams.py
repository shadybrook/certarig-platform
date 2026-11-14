"""Reviewed exact-version teams using AgentSession and one shared model-call budget."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from certarig.agent.orchestrator import AgentSession
from certarig.agent.providers.base import ProviderResponse, ToolCall, ToolSpec
from certarig.agent.tools import ToolResult
from certarig.agent.transcript import Transcript

from .contracts import OUTPUT, fingerprint
from .evaluation import system_prompt
from .store import Actor, uid


class Budget:
    def __init__(self, guard: Any, limit: int = 8):
        self.remaining, self.guard = limit, guard

    def wrap(self, provider: Any) -> Any:
        budget = self

        class Bounded:
            name, model = provider.name, provider.model

            def complete(self, *args: Any) -> Any:
                budget.guard()
                if budget.remaining <= 0:
                    raise PermissionError("Shared team model-call budget exhausted")
                budget.remaining -= 1
                result = provider.complete(*args)
                budget.guard()
                return result

        return Bounded()


def create(platform: Any, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
    if (
        set(body) != {"name", "supervisor_id", "specialist_ids"}
        or not isinstance(body["specialist_ids"], list)
        or not 1 <= len(body["specialist_ids"]) <= 3
    ):
        raise ValueError("A team needs one supervisor and one to three specialists")
    identifiers = [body["supervisor_id"], *body["specialist_ids"]]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Team members must be distinct exact versions")
    members = [platform.version(actor, identifier) for identifier in identifiers]
    if (
        any(v.get("team_members") or v["author_id"] != actor.user_id for v in members)
        or len({v["asset_id"] for v in members}) != 1
    ):
        raise PermissionError("Use your own independent versions on one bench; nested teams are unavailable")
    evaluations = []
    for member in members:
        matches = [
            e
            for e in platform.store.listing("evaluation", actor.org_id)
            if e["version_id"] == member["id"]
            and e["status"] == "passed"
            and e.get("trusted")
            and e["binding"] == platform.binding(actor, member)
        ]
        if not matches:
            raise ValueError("Every member requires a matching trusted evaluation")
        evaluations.append(matches[-1]["id"])
    # Independent team review later covers these exact evaluated member definitions.
    supervisor = members[0]
    limits = {
        key: (max if key == "interval_s" else min)(v["limits"][key] for v in members)
        for key in supervisor["limits"]
    }
    value = platform.create_version(
        actor,
        {k: supervisor[k] for k in ("name", "instructions", "asset_id", "connection_id", "tools")}
        | {"name": body["name"], "limits": limits},
    )
    value.update(
        analysis_tools=supervisor.get("analysis_tools", []),
        team_members=identifiers,
        member_evaluations=evaluations,
        team_id=uid("team"),
    )
    value["tools"] = sorted({tool for member in members for tool in member["tools"]})
    value["hash"] = fingerprint({k: v for k, v in value.items() if k != "hash"})
    with platform.store.atomic():
        platform.store.put("version", value)
        platform.store.put(
            "team", {**value, "supervisor_id": identifiers[0], "specialist_ids": identifiers[1:]}
        )
        platform.store.audit(
            actor.org_id, "team_created", actor.user_id, version_id=value["id"], team_id=value["team_id"]
        )
    return value


class TeamFixture:
    """Explicit deterministic fixture that exercises real CertaRig delegation."""

    name, model = "fixture", "deterministic/1"

    def __init__(self, members: list[str], fallback: Any):
        self.members, self.fallback = members, fallback

    def complete(self, system: str, messages: Any, tools: Any) -> ProviderResponse:
        if messages[-1].role != "tool":
            return ProviderResponse(
                None,
                [
                    ToolCall("read", "read_signals", {}),
                    *[
                        ToolCall(
                            "delegate-" + str(i),
                            "delegate_specialist",
                            {"version_id": member, "task": messages[0].content},
                        )
                        for i, member in enumerate(self.members)
                    ],
                ],
                model=self.model,
            )
        return self.fallback.complete(system, messages, tools)

    def cancel(self) -> None:
        self.fallback.cancel()

    def close(self) -> None:
        self.fallback.close()


def run(
    platform: Any,
    actor: Actor,
    version: dict[str, Any],
    provider_factory: Any,
    registry_factory: Any,
    path: Path,
    request: str,
    guard: Any,
    active: Any = None,
) -> dict[str, Any]:
    budget = Budget(guard, version["limits"]["model_calls"])
    delegations: list[dict[str, Any]] = []
    proposed: list[dict[str, Any]] = []
    members = [platform.version(actor, identifier) for identifier in version["team_members"]]
    permitted = {v["id"]: v for v in members[1:]}
    base = registry_factory(members[0])
    providers: list[Any] = []

    class Group:
        def cancel(self) -> None:
            for current in list(providers):
                current.cancel()

        def close(self) -> None:
            pass

    group = Group()

    class Registry:
        def specs(self) -> list[ToolSpec]:
            return [
                *base.specs(),
                ToolSpec(
                    "delegate_specialist",
                    "Assign an observation task to an exact reviewed specialist version.",
                    {
                        "type": "object",
                        "properties": {
                            "version_id": {"enum": list(permitted)},
                            "task": {"type": "string", "minLength": 1, "maxLength": 2000},
                        },
                        "required": ["version_id", "task"],
                        "additionalProperties": False,
                    },
                ),
                ToolSpec(
                    "propose_specialist",
                    "Submit an inert specialist suggestion for human review; cannot run it.",
                    {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "maxLength": 120},
                            "instructions": {"type": "string", "maxLength": 2000},
                        },
                        "required": ["name", "instructions"],
                        "additionalProperties": False,
                    },
                ),
            ]

        def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
            import jsonschema

            try:
                guard()
                if name not in {"delegate_specialist", "propose_specialist"}:
                    return base.execute(name, args)
                spec = next(s for s in self.specs() if s.name == name)
                jsonschema.validate(args, spec.parameters)
                if name == "propose_specialist":
                    if len(proposed) >= 3:
                        raise ValueError("Specialist suggestion limit reached")
                    proposed.append({**args, "status": "draft_requires_human_review"})
                    return ToolResult(name, args, True, proposed[-1], 0)
                if len(delegations) >= 3 or any(d["version_id"] == args["version_id"] for d in delegations):
                    raise PermissionError("Each selected specialist may run once per assessment")
                member = permitted[args["version_id"]]
                output = invoke(
                    member,
                    registry_factory(member),
                    args["task"],
                    path.with_name(path.stem + "-" + str(len(delegations)) + ".jsonl"),
                )
                guard()
                delegations.append(
                    {"version_id": member["id"], "binding": platform.binding(actor, member), **output}
                )
                return ToolResult(
                    name,
                    args,
                    True,
                    {
                        "output": output["output"],
                        "fixture": platform.store.get("connection", member["connection_id"], actor.org_id)[
                            "backend"
                        ]
                        == "fixture",
                    },
                    0,
                )
            except (PermissionError, ValueError, KeyError, jsonschema.ValidationError) as exc:
                return ToolResult(name, args, False, {"error": str(exc)[:500]}, 0)

    def invoke(
        member: dict[str, Any], registry: Any, task: str, target: Path, *, supervisor: bool = False
    ) -> dict[str, Any]:
        import jsonschema

        connection = platform.store.get("connection", member["connection_id"], actor.org_id)
        provider = provider_factory(connection)
        if supervisor and connection["backend"] == "fixture":
            provider = TeamFixture(list(permitted), provider)
        providers.append(provider)
        if active:
            active(group)
        transcript = Transcript(target)
        session = AgentSession(
            budget.wrap(provider),
            registry,
            transcript,
            max_model_calls_per_turn=member["limits"]["model_calls"],
            system_prompt=system_prompt(member)
            + (
                "\nDelegate to selected specialists when useful; return readiness JSON. Suggestions never grant authority."
                if supervisor
                else ""
            ),
        )
        result = session.send(task)
        guard()
        if result.stopped_reason != "end_turn":
            raise ValueError("Team assessment did not complete")
        output = json.loads(result.text)
        jsonschema.validate(output, OUTPUT)
        return {
            "output": output,
            "calls": [
                {"name": r.name, "arguments": r.arguments, "ok": r.ok, "result": r.result}
                for r in result.tool_results
            ],
            "transcript": Transcript.read(target),
        }

    try:
        result = invoke(version, Registry(), request, path, supervisor=True)
        return {
            **result,
            "delegations": delegations,
            "proposals": proposed,
            "model_calls": version["limits"]["model_calls"] - budget.remaining,
        }
    finally:
        for provider in providers:
            provider.close()
