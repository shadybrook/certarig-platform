"""Manifest-driven tool registry.

The registry is built from ``GET /v1/capabilities`` on the Edge node, so the model only ever
sees the tools the manifest allows. Local helper tools (skills lookup, waiting for a run or an
approval) are added on top; they are read-only or produce approval *requests*, never actions.

Every execution returns a JSON-serialisable dict. Edge refusals (401/403/409/428) are returned
as structured results rather than raised, so the model can react (ask for approval, re-read
the contract, stop) and the transcript records the refusal.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from certarig.edge.client import EdgeApiError, EdgeClient

from .providers.base import ToolSpec
from .skills import SkillIndex

MAX_RESULT_CHARS = 12_000

LOCAL_TOOLS: dict[str, ToolSpec] = {
    "list_skills": ToolSpec(
        "list_skills",
        "List the skills (documented procedures) available on this rig with their intents.",
        {"type": "object", "properties": {}, "additionalProperties": False},
    ),
    "read_skill": ToolSpec(
        "read_skill",
        "Read the full SKILL.md guidance for a skill before running its procedure.",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    ),
    "wait_for_run": ToolSpec(
        "wait_for_run",
        "Wait until a procedure run finishes or needs the operator, then return its state.",
        {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "timeout_s": {"type": "number", "minimum": 1, "maximum": 900},
            },
            "required": ["run_id"],
            "additionalProperties": False,
        },
    ),
    "request_approval": ToolSpec(
        "request_approval",
        "Ask the human operator to approve a tool call that needs human approval. Returns an approval id.",
        {
            "type": "object",
            "properties": {
                "tool": {"type": "string"},
                "args": {"type": "object"},
                "reason": {"type": "string", "maxLength": 500},
            },
            "required": ["tool", "reason"],
            "additionalProperties": False,
        },
    ),
    "wait_for_approval": ToolSpec(
        "wait_for_approval",
        "Wait for the operator to grant or deny an approval request.",
        {
            "type": "object",
            "properties": {
                "approval_id": {"type": "string"},
                "timeout_s": {"type": "number", "minimum": 1, "maximum": 900},
            },
            "required": ["approval_id"],
            "additionalProperties": False,
        },
    ),
}


@dataclass
class ToolResult:
    name: str
    arguments: dict[str, Any]
    ok: bool
    result: dict[str, Any]
    elapsed_ms: float

    def content(self) -> str:
        text = json.dumps(self.result, sort_keys=True, default=str)
        if len(text) > MAX_RESULT_CHARS:
            text = text[: MAX_RESULT_CHARS - 40] + '... [truncated]"}'
        return text


class ToolRegistry:
    def __init__(
        self,
        client: EdgeClient,
        skills: SkillIndex | None = None,
        sleep: Callable[[float], None] = time.sleep,
        poll_s: float = 0.25,
    ) -> None:
        self.client = client
        self.skills = skills or SkillIndex([])
        self._sleep = sleep
        self.poll_s = poll_s
        self.capabilities: dict[str, Any] = {}
        self.edge_tools: dict[str, ToolSpec] = {}
        self.policies: dict[str, str] = {}
        self.refresh()

    # ------------------------------------------------------------ discovery
    def refresh(self) -> None:
        self.capabilities = self.client.capabilities()
        self.client.refresh_contract()
        self.edge_tools = {}
        self.policies = {}
        for row in self.capabilities.get("agent_tools", []):
            self.edge_tools[row["name"]] = ToolSpec(row["name"], row["description"], row["parameters"])
            self.policies[row["name"]] = row["policy"]

    def specs(self) -> list[ToolSpec]:
        specs = list(self.edge_tools.values())
        specs.extend(LOCAL_TOOLS.values())
        return specs

    def has(self, name: str) -> bool:
        return name in self.edge_tools or name in LOCAL_TOOLS

    # ------------------------------------------------------------ execution
    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        if not self.has(name):
            return ToolResult(
                name,
                arguments,
                False,
                {
                    "error": f"tool {name!r} is not available on this rig; it is not in the capability manifest",
                    "code": "tool_not_available",
                    "available_tools": sorted(self.edge_tools) + sorted(LOCAL_TOOLS),
                },
                _ms(started),
            )
        try:
            if name in LOCAL_TOOLS:
                result = self._local(name, arguments)
            else:
                result = self._edge(name, arguments)
            if name == "commissioning_interview":
                result = {
                    k: result[k]
                    for k in (
                        "interview_id",
                        "revision",
                        "status",
                        "blockers",
                        "unresolved",
                        "interpretation",
                    )
                    if k in result
                } | {
                    "answers": {
                        k: bool(v) if k in {"document", "calibration_records"} else v
                        for k, v in result.get("answers", {}).items()
                    },
                    "review_location": "Onboard: review complete source document and diff",
                }
            if name in {"sandbox_experiment", "read_sandbox"} and not result.get("artifact_name"):
                allowed = {"sandbox_id", "revision", "status", "snapshot_hash", "expires_at", "authority", "job_id", "kind", "qualification", "proposal_id", "error", "artifacts"}
                brief = {k:v for k,v in result.items() if k in allowed}
                if "jobs" in result:
                    brief["jobs"] = [{k:v for k,v in j.items() if k in allowed} for j in result["jobs"]]
                if result.get("receipt"):
                    brief["verification"] = result["receipt"]["verification"]
                result = brief
            return ToolResult(name, arguments, True, result, _ms(started))
        except EdgeApiError as exc:
            payload = dict(exc.payload)
            payload.setdefault("error", str(exc))
            payload["http_status"] = exc.status
            if exc.status == 428:
                payload["arguments"] = {k: v for k, v in arguments.items() if k != "approval_id"}
                payload["hint"] = (
                    "call request_approval with this tool and arguments, then wait_for_approval, then retry with approval_id"
                )
            elif exc.status == 409 and exc.code == "stale_contract":
                self.client.refresh_contract()
                payload["hint"] = "contract refreshed; retry once"
            return ToolResult(name, arguments, False, payload, _ms(started))
        except (KeyError, TypeError, ValueError) as exc:
            return ToolResult(
                name,
                arguments,
                False,
                {"error": f"bad arguments: {exc}", "code": "bad_arguments"},
                _ms(started),
            )

    def _edge(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        client = self.client
        approval = args.get("approval_id")
        if name == "read_sandbox":
            base = "/v1/sandboxes/" + str(args["sandbox_id"])
            if args.get("job_id"):
                base += "/jobs/" + str(args["job_id"])
                if args.get("artifact_name"):
                    from urllib.parse import quote
                    artifact = str(args["artifact_name"])
                    data = client.request("GET", base + "/artifacts/" + quote(artifact, safe=""), raw=True)
                    return {"artifact_name": artifact, "bytes": len(data), "preview": "PNG available in Studio" if artifact.endswith(".png") else data[:8000].decode(errors="replace"), "truncated": len(data)>8000, "evidence_kind": "untrusted_experiment_artifact_not_authority"}
            return client.get(base)
        if name == "sandbox_experiment":
            action = args["action"]
            sandbox_payload = {k:v for k,v in args.items() if k not in {"action", "sandbox_id"}}
            if action == "create":
                return client.post("/v1/sandboxes", sandbox_payload)
            base = "/v1/sandboxes/" + str(args["sandbox_id"])
            if action == "close":
                return client.request("DELETE", base, {})
            suffix = {"revise": "/revisions", "run": "/jobs", "propose": "/proposals"}[action]
            return client.post(base + suffix, sandbox_payload)
        if name == "commissioning_interview":
            action = args["action"]
            base = "/v1/commissioning/interviews"
            if action == "create":
                return client.post(base, {})
            base += "/" + str(args["interview_id"])
            if action == "read":
                return client.get(base)
            if action == "propose":
                return client.post(base + "/propose", {})
            if action == "update":
                return client.post(
                    base + "/answers", {k: v for k, v in args.items() if k not in {"action", "interview_id"}}
                )
            raise ValueError("unsupported interview action")
        if name == "read_rig":
            return client.rig()
        if name == "read_capabilities":
            return client.capabilities()
        if name == "read_signals":
            return client.signals()
        if name == "read_state":
            state = client.state()
            state.pop("history", None)
            return state
        if name == "read_procedures":
            return client.procedures()
        if name == "read_procedure_run":
            return client.procedure_run(str(args["run_id"]))
        if name == "read_evidence":
            return client.get("/v1/evidence")
        if name in {"force_safe", "reset_trip", "request_permit"}:
            command = {"force_safe": "safe", "reset_trip": "reset", "request_permit": "permit"}[name]
            state = client.command(command, approval_id=approval)
            state.pop("history", None)
            return state
        if name == "start_recording":
            return client.start_recording(str(args.get("label", "agent-run")))
        if name == "stop_recording":
            return client.stop_recording()
        if name == "run_procedure":
            return client.run_procedure(str(args["procedure_id"]), args.get("label"), approval_id=approval)
        if name == "ack_operator_step":
            return client.ack(str(args["run_id"]), str(args["step_id"]))
        if name == "abort_procedure":
            return client.abort(str(args["run_id"]), str(args.get("reason", "agent abort")))
        if name == "draft_procedure":
            return client.post("/v1/procedures/drafts", {"procedure": args["procedure"]})
        if name == "export_evidence":
            return client.post("/v1/ops/evidence/export", {})
        if name == "stop_recorder":
            return client.post("/v1/ops/recorder/stop", {})
        if name == "shutdown":
            payload: dict[str, Any] = {"reason": str(args.get("reason", "agent requested shutdown"))}
            if approval:
                payload["approval_id"] = approval
            return client.post("/v1/ops/shutdown", payload)
        raise KeyError(name)

    def _local(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "list_skills":
            return {"skills": self.skills.list()}
        if name == "read_skill":
            skill = self.skills.get(str(args["name"]))
            if skill is None:
                matches = self.skills.match(str(args["name"]))
                return {"error": "skill not found", "suggestions": [m[0].name for m in matches]}
            payload = {**skill.summary(), "guidance": skill.body}
            procedure_id = skill.procedure_id or skill.name
            try:
                ledger = self.client.get(f"/v1/ledger?procedure_id={procedure_id}")
                payload["recent_outcomes"] = (ledger.get("outcomes") or [])[-5:]
            except Exception:
                payload["recent_outcomes"] = []
            return payload
        if name == "wait_for_run":
            deadline = time.monotonic() + float(args.get("timeout_s", 120))
            while True:
                run = self.client.procedure_run(str(args["run_id"]))
                if run.get("terminal") or run.get("status") == "awaiting_operator":
                    return _compact_run(run)
                if time.monotonic() >= deadline:
                    return {**_compact_run(run), "timed_out": True}
                self._sleep(self.poll_s)
        if name == "request_approval":
            tool = str(args["tool"])
            return self.client.request_approval(tool, dict(args.get("args", {}) or {}), str(args["reason"]))
        if name == "wait_for_approval":
            deadline = time.monotonic() + float(args.get("timeout_s", 300))
            while True:
                approval = self.client.get(f"/v1/approvals/{args['approval_id']}")
                if approval["status"] != "pending":
                    return approval
                if time.monotonic() >= deadline:
                    return {**approval, "timed_out": True}
                self._sleep(self.poll_s)
        raise KeyError(name)


def _ms(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 3)


def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
    """Keep the model's context small: drop raw event lists, keep what it must reason about."""
    return {
        "run_id": run.get("run_id"),
        "procedure_id": run.get("procedure_id"),
        "status": run.get("status"),
        "terminal": run.get("terminal"),
        "current_step": run.get("current_step"),
        "outcome_reason": run.get("outcome_reason"),
        "steps": [
            {
                "step_id": step["step_id"],
                "type": step["type"],
                "status": step["status"],
                "elapsed_ms": step.get("elapsed_ms"),
                "instruction": step.get("instruction"),
                "reason": step.get("detail", {}).get("reason"),
            }
            for step in run.get("steps", [])
        ],
        "checks": [{"check": c["check"], "passed": c["passed"]} for c in run.get("checks", [])],
        "kernel_events": [e["event"] for e in run.get("kernel_events", [])][-20:],
        "peaks": run.get("peaks"),
        "recording": run.get("recording"),
        "recovery": run.get("recovery"),
        "evidence_dir": run.get("evidence_dir"),
    }
