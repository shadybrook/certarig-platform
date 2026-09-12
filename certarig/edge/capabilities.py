"""Capability manifest: the contract that limits what the agent may do on a rig.

Two principals exist on an Edge node:

* ``operator``: a human holding the operator key (Studio, CLI). Operators may call
  every tool except those marked ``never``.
* ``agent``: an LLM-driven client holding the agent key. Agents are governed by
  the manifest policy for each tool.

The catalogue below is the single source of truth for tool names. The Edge router,
the agent tool registry and Studio all derive from it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import canonical_hash
from .schemas import validate_against_schema


class Policy(StrEnum):
    ALLOWED = "allowed"
    HUMAN_APPROVAL = "human_approval"
    CONTROLLER_APPROVAL = "controller_approval"
    NEVER = "never"


class Principal(StrEnum):
    ANONYMOUS = "anonymous"
    AGENT = "agent"
    OPERATOR = "operator"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    mutating: bool
    parameters: dict[str, Any]
    """JSON Schema for the tool arguments (agent-facing)."""


def _params(properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties or {},
        "required": required or [],
    }


TOOL_CATALOGUE: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in (
        ToolSpec("read_rig", "Read the public rig configuration, signals map and hashes.", False, _params()),
        ToolSpec(
            "read_capabilities", "Read this manifest: what the agent may do right now.", False, _params()
        ),
        ToolSpec(
            "read_signals",
            "Read the customer signal to CertaRig concept mapping and limits.",
            False,
            _params(),
        ),
        ToolSpec(
            "read_state",
            "Read the latest live state: samples, guardrail, outputs, recording and last event.",
            False,
            _params(),
        ),
        ToolSpec("read_procedures", "List the approved procedures available on this rig.", False, _params()),
        ToolSpec(
            "read_procedure_run",
            "Read the state of a procedure run.",
            False,
            _params({"run_id": {"type": "string"}}, ["run_id"]),
        ),
        ToolSpec("read_evidence", "List evidence bundles and their checksums.", False, _params()),
        ToolSpec(
            "force_safe",
            "Command the kernel to the safe state: output off, permit cleared, trip latched.",
            True,
            _params(),
        ),
        ToolSpec(
            "reset_trip",
            "Clear a latched trip after the process is healthy. Does not energise anything by itself.",
            True,
            _params(),
        ),
        ToolSpec(
            "request_permit",
            "Ask the kernel to energise the permit output. The kernel decides; it can refuse.",
            True,
            _params(),
        ),
        ToolSpec(
            "start_recording",
            "Start a CSV recording of live samples.",
            True,
            _params({"label": {"type": "string", "maxLength": 40}}),
        ),
        ToolSpec("stop_recording", "Stop the active CSV recording and return its checksum.", True, _params()),
        ToolSpec(
            "run_procedure",
            "Start an approved procedure by id. The runtime executes it deterministically.",
            True,
            _params(
                {"procedure_id": {"type": "string"}, "label": {"type": "string", "maxLength": 40}},
                ["procedure_id"],
            ),
        ),
        ToolSpec(
            "ack_operator_step",
            "Acknowledge that a physical operator instruction has been carried out.",
            True,
            _params({"run_id": {"type": "string"}, "step_id": {"type": "string"}}, ["run_id", "step_id"]),
        ),
        ToolSpec(
            "abort_procedure",
            "Abort a running procedure; the kernel is forced safe.",
            True,
            _params(
                {"run_id": {"type": "string"}, "reason": {"type": "string", "maxLength": 200}}, ["run_id"]
            ),
        ),
        ToolSpec(
            "draft_procedure",
            "Store an unapproved procedure draft for engineer review. Drafts cannot run.",
            True,
            _params({"procedure": {"type": "object"}}, ["procedure"]),
        ),
        ToolSpec(
            "export_evidence", "Package the latest evidence into a checksummed bundle.", True, _params()
        ),
        ToolSpec(
            "stop_recorder", "Stop any active recording and flush files (pre-shutdown).", True, _params()
        ),
        ToolSpec(
            "shutdown",
            "Gracefully close the runtime, force safe and power the edge node down.",
            True,
            _params({"reason": {"type": "string", "maxLength": 200}}),
        ),
        ToolSpec("bypass_interlock", "Never available. Present so a refusal is recorded.", True, _params()),
        ToolSpec("override_limits", "Never available. Present so a refusal is recorded.", True, _params()),
    )
}

ALWAYS_FORBIDDEN = frozenset({"bypass_interlock", "override_limits"})


class CapabilityError(PermissionError):
    def __init__(self, tool: str, policy: Policy, principal: Principal, detail: str) -> None:
        super().__init__(detail)
        self.tool = tool
        self.policy = policy
        self.principal = principal
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.detail,
            "tool": self.tool,
            "policy": self.policy.value,
            "principal": self.principal.value,
        }


@dataclass(frozen=True)
class CapabilityManifest:
    manifest_id: str
    revision: str
    description: str
    approval_ttl_s: int
    policies: dict[str, Policy]
    notes: dict[str, str]
    manifest_hash: str

    @classmethod
    def from_dict(cls, raw: Any) -> CapabilityManifest:
        validate_against_schema(raw, "capabilities.schema.json")
        tools_raw = raw["tools"]
        unknown = sorted(set(tools_raw) - set(TOOL_CATALOGUE))
        if unknown:
            raise ValueError(f"capability manifest lists unknown tools: {', '.join(unknown)}")
        policies: dict[str, Policy] = {}
        notes: dict[str, str] = {}
        for name, spec in TOOL_CATALOGUE.items():
            entry = tools_raw.get(name)
            policy = Policy(entry["policy"]) if entry else Policy.NEVER
            if name in ALWAYS_FORBIDDEN and policy is not Policy.NEVER:
                raise ValueError(f"{name} must have policy never")
            if not spec.mutating and policy is Policy.HUMAN_APPROVAL:
                raise ValueError(f"{name} is read-only and cannot require human approval")
            policies[name] = policy
            if entry and entry.get("note"):
                notes[name] = str(entry["note"])
        return cls(
            manifest_id=str(raw["manifest_id"]),
            revision=str(raw["revision"]),
            description=str(raw.get("description", "")),
            approval_ttl_s=int(raw.get("approval_ttl_s", 300)),
            policies=policies,
            notes=notes,
            manifest_hash=canonical_hash(raw),
        )

    @classmethod
    def load(cls, path: str | Path) -> CapabilityManifest:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def read_only(cls, manifest_id: str = "read-only") -> CapabilityManifest:
        """A manifest where the agent can only read. Used when no file is configured."""
        raw = {
            "manifest_id": manifest_id,
            "revision": "builtin",
            "tools": {
                name: {"policy": "allowed" if not spec.mutating else "never"}
                for name, spec in TOOL_CATALOGUE.items()
            },
        }
        return cls.from_dict(raw)

    def policy(self, tool: str) -> Policy:
        return self.policies.get(tool, Policy.NEVER)

    def contract_hash(self, config_hash: str) -> str:
        """Binds the rig config and the manifest. Presented on every mutating call."""
        return hashlib.sha256(f"{config_hash}:{self.manifest_hash}".encode()).hexdigest()

    def authorize(self, tool: str, principal: Principal) -> Policy:
        """Return the effective policy or raise ``CapabilityError``.

        Operators bypass ``human_approval`` (they are the human) but never ``never``.
        Anonymous callers may only read.
        """
        if tool not in TOOL_CATALOGUE:
            raise CapabilityError(tool, Policy.NEVER, principal, f"unknown tool {tool}")
        spec = TOOL_CATALOGUE[tool]
        policy = self.policy(tool)
        if tool in ALWAYS_FORBIDDEN:
            raise CapabilityError(tool, Policy.NEVER, principal, f"{tool} is never available on this rig")
        if principal is Principal.ANONYMOUS:
            if spec.mutating:
                raise CapabilityError(tool, policy, principal, "authentication required")
            return Policy.ALLOWED
        if principal is Principal.OPERATOR:
            # The manifest governs the agent. A human operator keeps every tool except the
            # always-forbidden ones; the deterministic kernel still has the final say.
            return Policy.ALLOWED if policy is not Policy.CONTROLLER_APPROVAL else policy
        # agent
        if policy is Policy.NEVER:
            raise CapabilityError(
                tool, policy, principal, f"{tool} is not available to the agent on this rig"
            )
        return policy

    def agent_tools(self) -> list[dict[str, Any]]:
        """Tool descriptors the agent is allowed to see, in provider-neutral form."""
        rows: list[dict[str, Any]] = []
        for name, spec in TOOL_CATALOGUE.items():
            policy = self.policy(name)
            if policy is Policy.NEVER:
                continue
            rows.append(
                {
                    "name": name,
                    "description": spec.description
                    + (" Requires a human approval id." if policy is Policy.HUMAN_APPROVAL else "")
                    + (
                        " The deterministic controller may refuse."
                        if policy is Policy.CONTROLLER_APPROVAL
                        else ""
                    ),
                    "parameters": spec.parameters
                    if policy is not Policy.HUMAN_APPROVAL
                    else {
                        **spec.parameters,
                        "properties": {**spec.parameters["properties"], "approval_id": {"type": "string"}},
                    },
                    "policy": policy.value,
                    "mutating": spec.mutating,
                }
            )
        return rows

    def to_dict(self, config_hash: str | None = None) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "revision": self.revision,
            "description": self.description,
            "approval_ttl_s": self.approval_ttl_s,
            "manifest_hash": self.manifest_hash,
            "contract_hash": self.contract_hash(config_hash) if config_hash else None,
            "tools": [
                {
                    "name": name,
                    "policy": self.policy(name).value,
                    "mutating": spec.mutating,
                    "description": spec.description,
                    "note": self.notes.get(name),
                }
                for name, spec in TOOL_CATALOGUE.items()
            ],
        }
