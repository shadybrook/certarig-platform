"""Edge facade: authenticated local requests, inert proposals, no Docker access."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from certarig.edge.atomic import write_json_atomic
from certarig.edge.capabilities import Principal
from certarig.edge.config import canonical_hash, load_config_dict
from certarig.edge.configurator import propose_rig
from certarig.edge.server import EdgeNode, HttpError, RequestContext

from .contracts import LIMITS
from .transport import BrokerClient


class SandboxService:
    def __init__(self, node: EdgeNode, endpoint: Path | None) -> None:
        self.node = node
        self.client = BrokerClient(endpoint) if endpoint else None

    def call(self, ctx: RequestContext, method: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        if self.client is None:
            raise HttpError(
                503,
                {
                    "error": "Sandbox is disabled; configure a local broker socket",
                    "code": "sandbox_unavailable",
                },
            )
        try:
            return self.client.call(
                method, ctx.principal.value + ":" + ctx.principal_name, ctx.principal.value, body or {}
            )
        except PermissionError as exc:
            raise HttpError(403, str(exc)) from exc
        except (KeyError, StopIteration) as exc:
            raise HttpError(404, "sandbox resource not found") from exc
        except (ValueError, RuntimeError) as exc:
            raise HttpError(409, str(exc)) from exc
        except (TimeoutError, OSError) as exc:
            raise HttpError(
                503, {"error": "Local broker unavailable; no host fallback", "code": "sandbox_unavailable"}
            ) from exc

    def preflight(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        if self.client is None:
            return 200, {
                "ready": False,
                "enabled": False,
                "limits": LIMITS,
                "blockers": ["Local sandbox broker is not configured"],
            }
        try:
            return 200, {**self.call(ctx, "preflight"), "enabled": True, "limits": LIMITS}
        except HttpError as exc:
            return 200, {
                "enabled": True,
                "ready": False,
                "limits": LIMITS,
                "blockers": [exc.payload["error"]],
            }

    def create(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        source = ctx.body.get("source", "active")
        provenance: dict[str, Any] = {
            "source": source,
            "agent_kind": "deterministic_fixture_not_live_model_qualification",
        }
        with self.node.mutation_lock:
            base = self.node.config.config_hash
            if source == "active":
                document = self.node._current_rig_raw()
            elif source in {"thermal", "pressure_flow"}:
                filename = "rig.thermal.capstone.json" if source == "thermal" else "rig.sim.json"
                document = json.loads((Path(__file__).resolve().parents[2] / "config" / filename).read_text())
                provenance["calibration_kind"] = "deterministic_fixture_not_physical_calibration"
                for channel in document["channels"]:
                    channel.setdefault(
                        "source", {"kind": "virtual", "address": "fixture." + channel["channel_id"]}
                    )
            elif source == "interview":
                interview = self.node.extensions["interviews"].read(str(ctx.body.get("interview_id", "")))
                document = interview["answers"].get("document")
                provenance.update(
                    interview_id=interview["interview_id"],
                    interview_revision=interview["revision"],
                    blockers=interview.get("unresolved", []),
                )
                if not interview["answers"].get("calibration_records"):
                    provenance["blockers"].append("Missing interview calibration evidence")
            else:
                raise HttpError(400, "unsupported snapshot source")
            thermal = any(c.get("concept") == "temperature" for c in document.get("channels", []))
            pid = str(ctx.body.get("procedure_id", "thermal_soak" if thermal else "pressure_guardrail"))
            from certarig.edge.runtime import ProcedureLibrary
            from certarig.edge.runtime.model import Procedure

            proc = self.node.extensions["procedures"].library.get(pid)
            skills = self.node.extensions["procedures"].skills_root
            try:
                library = ProcedureLibrary(load_config_dict(document))
                if skills:
                    library.load_directory(skills)
                proc = library.get(pid) or proc
            except ValueError:
                # A draft can be analysed, but blocker validation prevents qualification.
                known = {
                    "thermal_soak": "reliability/thermal_soak/procedure.yaml",
                    "pressure_guardrail": "process/pressure_guardrail/procedure.yaml",
                }
                if proc is None and skills and pid in known:
                    import yaml

                    proc = Procedure.from_dict(yaml.safe_load((skills / known[pid]).read_text()))
            if proc is None:
                raise HttpError(404, "choose a supported approved procedure")
            payload = {
                "document": document,
                "procedure": proc.raw,
                "base_config_hash": base,
                "provenance": provenance,
                "seed": ctx.body.get("seed", 11),
            }
        if ctx.body.get("recording_id") is not None:
            if ctx.body["recording_id"] != "latest":
                raise HttpError(400, "Only the completed latest recording selector is supported")
            with self.node.runtime._lock:
                recording = self.node.runtime.latest_recording()
                if self.node.runtime.state()["recording"]["active"] or recording is None:
                    raise HttpError(
                        409, "Choose a completed recording; active/absent recordings cannot be snapshotted"
                    )
                if recording.stat().st_size > LIMITS["input_bytes"]:
                    raise HttpError(413, "Recording exceeds snapshot input quota")
                payload["recording"] = base64.b64encode(recording.read_bytes()).decode()
        return 201, self.call(ctx, "create", payload)

    def read(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, self.call(ctx, "read", {"sandbox_id": ctx.params["sandbox_id"]})

    def operation(self, ctx: RequestContext, method: str) -> tuple[int, dict[str, Any]]:
        payload = {**ctx.body, "sandbox_id": ctx.params["sandbox_id"]}
        if method == "run" and set(ctx.body) - {"kind", "source", "contract_hash"}:
            raise HttpError(400, "jobs accept only kind and source; engine settings are fixed")
        return (202 if method == "run" else 200), self.call(ctx, method, payload)

    def job(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        w = self.call(ctx, "read", {"sandbox_id": ctx.params["sandbox_id"]})
        for job in w["jobs"]:
            if job["job_id"] == ctx.params["job_id"]:
                return 200, job
        raise HttpError(404, "job not found")

    def propose(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        w = self.call(ctx, "read", {"sandbox_id": ctx.params["sandbox_id"]})
        if w["snapshot"]["base_config_hash"] != self.node.config.config_hash:
            raise HttpError(409, "base configuration changed; fork a new workspace")
        _, proposal = self.operation(ctx, "propose")
        proposal["preview"] = propose_rig(self.node._current_rig_raw(), proposal["document"])
        return 201, proposal

    def handoff(self, ctx: RequestContext, kind: str, document: dict[str, Any]) -> None:
        if not (ctx.body.get("sandbox_id") or ctx.body.get("sandbox_proposal_id")):
            return
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, "operator review is required")
        proposal = self.call(
            ctx,
            "validate_proposal",
            {
                "sandbox_id": ctx.body.get("sandbox_id"),
                "proposal_id": ctx.body.get("sandbox_proposal_id"),
                "base_config_hash": self.node.config.config_hash,
            },
        )
        if proposal["kind"] != kind:
            raise HttpError(409, "sandbox proposal type does not match review")
        try:
            match = (
                load_config_dict(document).config_hash == load_config_dict(proposal["document"]).config_hash
                if kind == "configuration"
                else canonical_hash(document) == canonical_hash(proposal["procedure"])
            )
        except ValueError as exc:
            raise HttpError(409, "review content is not a valid qualified document") from exc
        if not match:
            raise HttpError(409, "review content differs from qualified sandbox proposal")
        write_json_atomic(
            self.node.runtime.evidence_dir / "sandbox_reviews" / (proposal["proposal_id"] + ".json"),
            {
                "event": "operator_review_checked",
                "operator": ctx.principal_name,
                "proposal": proposal,
                "execution_authority": "none; existing apply/approval/physical gates still required",
            },
        )

    def artifact(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        result = self.call(
            ctx,
            "artifact",
            {
                "sandbox_id": ctx.params["sandbox_id"],
                "job_id": ctx.params["job_id"],
                "name": ctx.params["name"],
            },
        )
        data = base64.b64decode(result["data"], validate=True)
        mime = "text/plain; charset=utf-8"
        if result["name"].endswith(".png"):
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HttpError(409, "not a PNG artifact")
            mime = "image/png"
        elif result["name"].endswith(".gz"):
            mime = "application/gzip"
        return 200, data, mime

    def export(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        result = self.call(ctx, "export", {"sandbox_id": ctx.params["sandbox_id"]})
        return 200, base64.b64decode(result["data"], validate=True), "application/zip"


def install(node: EdgeNode, endpoint: Path | None) -> None:
    service = SandboxService(node, endpoint)
    node.extensions["sandboxes"] = service
    node.flags["sandbox_local_only"] = endpoint is not None
    node.add_route("GET", "/v1/sandboxes/preflight", service.preflight)
    node.add_route("GET", "/v1/sandboxes", lambda c: (200, service.call(c, "list")))
    node.add_route("POST", "/v1/sandboxes", service.create, "sandbox_experiment")
    base = "/v1/sandboxes/{sandbox_id}"
    node.add_route("GET", base, service.read, "read_sandbox")
    node.add_route("DELETE", base, lambda c: service.operation(c, "close"), "sandbox_experiment")
    node.add_route(
        "POST", base + "/revisions", lambda c: service.operation(c, "revise"), "sandbox_experiment"
    )
    node.add_route("POST", base + "/jobs", lambda c: service.operation(c, "run"), "sandbox_experiment")
    node.add_route("GET", base + "/jobs/{job_id}", service.job, "read_sandbox")
    node.add_route("GET", base + "/jobs/{job_id}/artifacts/{name}", service.artifact, "read_sandbox")
    node.add_route("POST", base + "/proposals", service.propose, "sandbox_experiment")
    node.add_route("GET", base + "/export", service.export, "read_sandbox")
