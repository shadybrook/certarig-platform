"""Procedure runtime API extension for the Edge node."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .capabilities import Principal
from .runtime import ProcedureLibrary, ProcedureRunner, ProcedureValidationError, validate_procedure
from .runtime.runner import RunnerError
from .server import EdgeNode, HttpError, RequestContext

DEFAULT_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


class ProcedureService:
    def __init__(self, node: EdgeNode) -> None:
        self.node = node
        self.library = ProcedureLibrary(
            node.config, drafts_dir=node.runtime.evidence_dir / "procedure_drafts"
        )
        self.runner = ProcedureRunner(
            node.runtime,
            node.config,
            node.runtime.evidence_dir,
            contract_hash=lambda: node.contract_hash,
        )

    def load_library(self, root: str | Path) -> list[str]:
        return [procedure.id for procedure in self.library.load_directory(root)]

    def close(self) -> None:
        self.runner.close()

    # ------------------------------------------------------------ routes
    def list_procedures(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, {"procedures": self.library.list(), "skipped": self.library.skipped}

    def get_procedure(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        procedure = self.library.get(ctx.params["procedure_id"])
        if procedure is None:
            raise HttpError(404, "procedure not found")
        return 200, {**procedure.summary(), "procedure": procedure.raw}

    def validate(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        raw = ctx.body.get("procedure")
        errors = validate_procedure(raw, self.node.config)
        payload: dict[str, Any] = {"valid": not errors, "errors": errors}
        if not errors and isinstance(raw, dict):
            from .config import canonical_hash

            payload["procedure_hash"] = canonical_hash(raw)
        return 200, payload

    def create_draft(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        raw = ctx.body.get("procedure")
        if not isinstance(raw, dict):
            raise HttpError(400, "procedure must be an object")
        try:
            draft = self.library.add_draft(raw, ctx.principal_name)
        except ProcedureValidationError as exc:
            raise HttpError(422, {"error": "procedure is invalid", "errors": exc.errors}) from exc
        return 201, draft.summary()

    def list_drafts(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        return 200, {"drafts": self.library.drafts()}

    def get_draft(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        draft = self.library.draft(ctx.params["procedure_hash"])
        if draft is None:
            raise HttpError(404, "draft not found")
        return 200, {**draft.summary(), "procedure": draft.raw}

    def approve_draft(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, "only an engineer (operator principal) can approve a procedure draft")
        try:
            procedure = self.library.approve_draft(ctx.params["procedure_hash"], ctx.principal_name)
        except KeyError as exc:
            raise HttpError(404, "draft not found") from exc
        return 200, procedure.summary()

    def reject_draft(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, "only an engineer (operator principal) can reject a procedure draft")
        try:
            self.library.reject_draft(ctx.params["procedure_hash"])
        except KeyError as exc:
            raise HttpError(404, "draft not found") from exc
        return 200, {"status": "rejected"}

    def start_run(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        procedure_id = str(ctx.body.get("procedure_id", ""))
        procedure = self.library.get(procedure_id)
        if procedure is None:
            raise HttpError(404, f"procedure {procedure_id!r} not found or not approved")
        label = str(ctx.body.get("label") or procedure_id)
        try:
            run = self.runner.start(procedure, label, ctx.principal_name)
        except RunnerError as exc:
            raise HttpError(409, str(exc)) from exc
        return 201, run.to_dict()

    def list_runs(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, {"runs": self.runner.list()}

    def get_run(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        run = self.runner.get(ctx.params["run_id"])
        if run is None:
            raise HttpError(404, "run not found")
        return 200, run.to_dict()

    def ack(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        try:
            run = self.runner.ack(ctx.params["run_id"], str(ctx.body.get("step_id", "")), ctx.principal_name)
        except KeyError as exc:
            raise HttpError(404, "run not found") from exc
        except RunnerError as exc:
            raise HttpError(409, str(exc)) from exc
        return 200, run.to_dict()

    def abort(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        try:
            run = self.runner.abort(
                ctx.params["run_id"], str(ctx.body.get("reason") or "aborted via API"), ctx.principal_name
            )
        except KeyError as exc:
            raise HttpError(404, "run not found") from exc
        except RunnerError as exc:
            raise HttpError(409, str(exc)) from exc
        return 200, run.to_dict()


def install_procedures(node: EdgeNode, skills_root: str | Path | None = None) -> ProcedureService:
    service = ProcedureService(node)
    if skills_root is not None:
        service.load_library(skills_root)
    node.extensions["procedures"] = service
    add = node.add_route
    add("GET", "/v1/procedures", service.list_procedures, "read_procedures")
    add("GET", "/v1/procedures/drafts", service.list_drafts)
    add("GET", "/v1/procedures/drafts/{procedure_hash}", service.get_draft)
    add("GET", "/v1/procedures/{procedure_id}", service.get_procedure, "read_procedures")
    add("POST", "/v1/procedures/validate", service.validate)
    add("POST", "/v1/procedures/drafts", service.create_draft, "draft_procedure")
    add("POST", "/v1/procedures/drafts/{procedure_hash}/approve", service.approve_draft)
    add("POST", "/v1/procedures/drafts/{procedure_hash}/reject", service.reject_draft)
    add("GET", "/v1/procedure_runs", service.list_runs, "read_procedure_run")
    add("POST", "/v1/procedure_runs", service.start_run, "run_procedure")
    add("GET", "/v1/procedure_runs/{run_id}", service.get_run, "read_procedure_run")
    add("POST", "/v1/procedure_runs/{run_id}/ack", service.ack, "ack_operator_step")
    add("POST", "/v1/procedure_runs/{run_id}/abort", service.abort, "abort_procedure")
    return service
