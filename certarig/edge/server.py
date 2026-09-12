"""The unified CertaRig Edge server.

One process, one lifecycle, one authentication path. Hosts:

* the live runtime (sampling loop, kernel, CSV recorder),
* the rig contract (config, signals, capability manifest, contract hash),
* human approvals,
* the procedure runtime (registered by :mod:`certarig.edge.procedures`),
* operational endpoints (registered by :mod:`certarig.edge.ops`),
* Studio static assets.

Every mutating route is bound to a tool name from the capability catalogue and is
enforced by :meth:`CapabilityManifest.authorize` before any handler code runs.
"""

from __future__ import annotations

import json
import mimetypes
import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from certarig import __version__

from .approvals import ApprovalError, ApprovalRegistry
from .capabilities import CapabilityError, CapabilityManifest, Policy, Principal
from .errors import catalog, enrich
from .live import LiveBenchRuntime
from .sessions import SessionRegistry


class HttpError(Exception):
    def __init__(self, status: int, payload: dict[str, Any] | str) -> None:
        super().__init__(payload if isinstance(payload, str) else payload.get("error", "error"))
        self.status = status
        if isinstance(payload, str):
            self.payload = {"error": payload}
        else:
            self.payload = enrich(payload)


@dataclass
class RequestContext:
    method: str
    path: str
    params: dict[str, str]
    query: dict[str, list[str]]
    body: dict[str, Any]
    principal: Principal
    principal_name: str
    tool: str | None
    policy: Policy | None
    approval_id: str | None = None


Handler = Callable[[RequestContext], tuple[int, dict[str, Any]] | tuple[int, bytes, str]]


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    pattern: re.Pattern[str]
    handler: Handler
    tool: str | None
    mutating: bool


class Router:
    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add(self, method: str, path: str, handler: Handler, tool: str | None = None) -> None:
        regex = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$"
        self.routes.append(
            Route(method.upper(), path, re.compile(regex), handler, tool, method.upper() != "GET")
        )

    def match(self, method: str, path: str) -> tuple[Route | None, dict[str, str], bool]:
        path_matched = False
        for route in self.routes:
            found = route.pattern.match(path)
            if found:
                path_matched = True
                if route.method == method.upper():
                    return route, found.groupdict(), True
        return None, {}, path_matched


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class EdgeNode:
    """Composition root for one Edge deployment."""

    def __init__(
        self,
        runtime: LiveBenchRuntime,
        manifest: CapabilityManifest,
        operator_key: str,
        agent_key: str | None = None,
        auditor_key: str | None = None,
        static_root: str | Path | None = None,
        audit_size: int = 2000,
        config_path: str | Path | None = None,
        capabilities_path: str | Path | None = None,
    ) -> None:
        if len(operator_key) < 12:
            raise ValueError("operator key must be at least 12 characters")
        if agent_key is not None and len(agent_key) < 12:
            raise ValueError("agent key must be at least 12 characters")
        if agent_key is not None and secrets.compare_digest(agent_key, operator_key):
            raise ValueError("agent key must differ from the operator key")
        self.runtime = runtime
        self.config = runtime.config
        self.manifest = manifest
        self.operator_key = operator_key
        self.agent_key = agent_key
        self.auditor_key = auditor_key
        self.config_path = Path(config_path) if config_path else None
        self.capabilities_path = Path(capabilities_path) if capabilities_path else None
        self.sessions = SessionRegistry()
        self.static_root = Path(static_root).resolve() if static_root else None
        self.approvals = ApprovalRegistry(ttl_s=manifest.approval_ttl_s)
        self.router = Router()
        self.started_at = utc_now()
        self._audit: deque[dict[str, Any]] = deque(maxlen=audit_size)
        self._audit_lock = threading.Lock()
        self.extensions: dict[str, Any] = {}
        self.flags: dict[str, Any] = {}
        self._register_core_routes()

    # ------------------------------------------------------------------ contract
    @property
    def contract_hash(self) -> str:
        return self.manifest.contract_hash(self.config.config_hash)

    def health(self) -> dict[str, Any]:
        import os

        observe_only = bool(self.config.hardware.observe_only)
        unclean = bool(self.flags.get("unclean_shutdown"))
        twin = self.flags.get("twin_gate_ready")
        ready = {
            "actuation_enabled": self.runtime.allow_output,
            "observe_only": observe_only,
            "unclean_shutdown": unclean,
            "contract_hash": self.contract_hash,
            "calibration_ids": [c.calibration_id for c in self.config.channels if c.calibration_id],
            "twin_gate": twin,
            "agent_provider": os.environ.get("CERTARIG_AGENT_PROVIDER", "fake"),
        }
        return {
            "status": "ok",
            "rig_id": self.config.rig_id,
            "hardware_mode": self.config.hardware.mode,
            "actuation_enabled": self.runtime.allow_output,
            "config_hash": self.config.config_hash,
            "manifest_hash": self.manifest.manifest_hash,
            "contract_hash": self.contract_hash,
            "started_at": self.started_at,
            "extensions": sorted(self.extensions),
            "version": __version__,
            "observe_only": observe_only,
            "ready_to_arm": ready,
            "agent_provider": ready["agent_provider"],
            **self.flags,
        }

    def rig_document(self) -> dict[str, Any]:
        document = None
        if self.config_path is not None and self.config_path.is_file():
            document = json.loads(self.config_path.read_text(encoding="utf-8"))
        return {
            "rig": self.config.public_dict(),
            "signals": self.config.signals(),
            "actuators": self.config.actuators(),
            "config_hash": self.config.config_hash,
            "manifest_id": self.manifest.manifest_id,
            "manifest_hash": self.manifest.manifest_hash,
            "contract_hash": self.contract_hash,
            "document": document,
        }

    # -------------------------------------------------------------------- audit
    def audit(self, ctx: RequestContext, status: int, detail: dict[str, Any] | None = None) -> None:
        with self._audit_lock:
            self._audit.append(
                {
                    "at": utc_now(),
                    "principal": ctx.principal.value,
                    "principal_name": ctx.principal_name,
                    "tool": ctx.tool,
                    "policy": ctx.policy.value if ctx.policy else None,
                    "method": ctx.method,
                    "path": ctx.path,
                    "status": status,
                    "approval_id": ctx.approval_id,
                    "detail": detail or {},
                }
            )

    def audit_log(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._audit_lock:
            rows = list(self._audit)
        return rows[-limit:]

    # ----------------------------------------------------------------- principal
    def resolve_principal(self, headers: Any) -> tuple[Principal, str]:
        token = headers.get("X-CertaRig-Session")
        if token:
            session = self.sessions.resolve(token)
            if session is not None:
                return session.role, session.name
        operator = headers.get("X-CertaRig-Operator-Key")
        if operator is not None and secrets.compare_digest(operator, self.operator_key):
            return Principal.OPERATOR, str(headers.get("X-CertaRig-Operator", "operator"))
        agent = headers.get("X-CertaRig-Agent-Key")
        if agent is not None and self.agent_key is not None and secrets.compare_digest(agent, self.agent_key):
            return Principal.AGENT, str(headers.get("X-CertaRig-Agent", "agent"))
        auditor = headers.get("X-CertaRig-Auditor-Key")
        if auditor is not None and self.auditor_key is not None and secrets.compare_digest(auditor, self.auditor_key):
            return Principal.AUDITOR, str(headers.get("X-CertaRig-Auditor", "auditor"))
        return Principal.ANONYMOUS, "anonymous"

    # --------------------------------------------------------------- enforcement
    def enforce(self, ctx: RequestContext, route: Route, headers: Any) -> None:
        if route.tool is None:
            if route.mutating and ctx.principal is Principal.ANONYMOUS and route.path != "/v1/auth/session":
                raise HttpError(401, "authentication required")
            if route.mutating and ctx.principal is Principal.AUDITOR:
                raise HttpError(403, {"error": "auditor is read-only", "code": "observe_only"})
            return
        try:
            policy = self.manifest.authorize(route.tool, ctx.principal)
        except CapabilityError as exc:
            status = 401 if ctx.principal is Principal.ANONYMOUS else 403
            payload = exc.to_dict()
            if ctx.principal is Principal.AUDITOR:
                payload["code"] = "observe_only"
            raise HttpError(status, payload) from exc
        ctx.policy = policy
        if not route.mutating:
            return
        presented = headers.get("X-CertaRig-Contract") or ctx.body.get("contract_hash")
        if presented != self.contract_hash:
            raise HttpError(
                409,
                {
                    "error": "stale or missing contract_hash; re-read /v1/rig before commanding",
                    "code": "stale_contract",
                    "expected_contract_hash": self.contract_hash,
                },
            )
        if policy is Policy.HUMAN_APPROVAL and ctx.principal is Principal.AGENT:
            approval_id = ctx.body.get("approval_id")
            if not approval_id:
                raise HttpError(
                    428,
                    {
                        "error": f"{route.tool} requires a human approval; request one at POST /v1/approvals/request",
                        "code": "approval_required",
                        "tool": route.tool,
                        "args": {
                            k: v for k, v in ctx.body.items() if k not in {"approval_id", "contract_hash"}
                        },
                    },
                )
            args = {k: v for k, v in ctx.body.items() if k not in {"approval_id", "contract_hash"}}
            try:
                self.approvals.consume(str(approval_id), route.tool, args, self.contract_hash)
            except ApprovalError as exc:
                raise HttpError(403, {"error": str(exc), "code": "approval_invalid"}) from exc
            ctx.approval_id = str(approval_id)

    # ------------------------------------------------------------------- routes
    def add_route(self, method: str, path: str, handler: Handler, tool: str | None = None) -> None:
        self.router.add(method, path, handler, tool)

    def _register_core_routes(self) -> None:
        add = self.add_route
        add("GET", "/health", lambda ctx: (200, self.health()))
        add("GET", "/v1/errors", lambda ctx: (200, catalog()))
        add("POST", "/v1/auth/session", self._mint_session)
        add("GET", "/v1/rig", lambda ctx: (200, self.rig_document()), "read_rig")
        add("POST", "/v1/rig/propose", self._propose_rig)
        add("POST", "/v1/rig/apply", self._apply_rig)
        add("POST", "/v1/capabilities/propose", self._propose_capabilities)
        add("POST", "/v1/capabilities/apply", self._apply_capabilities)
        add("GET", "/v1/ledger", self._ledger)
        add("GET", "/v1/authoring/templates", self._authoring_templates)
        add("POST", "/v1/authoring/build", self._authoring_build)
        add("POST", "/v1/ops/acknowledge_unclean", self._ack_unclean)
        add("GET", "/v1/signals", lambda ctx: (200, {"signals": self.config.signals()}), "read_signals")
        add(
            "GET",
            "/v1/capabilities",
            lambda ctx: (
                200,
                {
                    **self.manifest.to_dict(self.config.config_hash),
                    "principal": ctx.principal.value,
                    "agent_tools": self.manifest.agent_tools(),
                },
            ),
            "read_capabilities",
        )
        add("GET", "/v1/live/state", lambda ctx: (200, self.runtime.state()), "read_state")
        add("GET", "/v1/live/recordings/latest.csv", self._latest_csv, "read_evidence")
        add("GET", "/v1/audit", self._audit_route)
        add("POST", "/v1/live/commands/safe", lambda ctx: (200, self.runtime.command("safe")), "force_safe")
        add("POST", "/v1/live/commands/reset", lambda ctx: (200, self.runtime.command("reset")), "reset_trip")
        add(
            "POST",
            "/v1/live/commands/permit",
            lambda ctx: (200, self.runtime.command("permit")),
            "request_permit",
        )
        add(
            "POST",
            "/v1/live/recordings/start",
            lambda ctx: (201, self.runtime.start_recording(str(ctx.body.get("label", "bench-run")))),
            "start_recording",
        )
        add(
            "POST",
            "/v1/live/recordings/stop",
            lambda ctx: (200, self.runtime.stop_recording()),
            "stop_recording",
        )
        # approvals
        add("GET", "/v1/approvals", self._list_approvals)
        add("GET", "/v1/approvals/{approval_id}", self._get_approval)
        add("POST", "/v1/approvals/request", self._request_approval)
        add("POST", "/v1/approvals/{approval_id}/grant", self._grant_approval)
        add("POST", "/v1/approvals/{approval_id}/deny", self._deny_approval)

    def _require_operator(self, ctx: RequestContext) -> None:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, {"error": "operator authentication required", "code": "observe_only"})

    def _mint_session(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        principal, name = self.resolve_principal(
            {
                "X-CertaRig-Operator-Key": ctx.body.get("operator_key"),
                "X-CertaRig-Agent-Key": ctx.body.get("agent_key"),
                "X-CertaRig-Auditor-Key": ctx.body.get("auditor_key"),
                "X-CertaRig-Operator": ctx.body.get("name"),
            }
        )
        if principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        session = self.sessions.mint(principal, str(ctx.body.get("name") or name))
        return 200, session.public()

    def _current_rig_raw(self) -> dict[str, Any]:
        if self.config_path is None or not self.config_path.is_file():
            raise HttpError(409, {"error": "this node has no writable rig file", "code": "restart_required"})
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def _propose_rig(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self._require_operator(ctx)
        from .configurator import propose_rig

        return 200, propose_rig(self._current_rig_raw(), ctx.body.get("document") or ctx.body)

    def _apply_rig(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self._require_operator(ctx)
        from .commissioning import ProcessGuardrail
        from .config import load_config
        from .configurator import apply_rig

        expected = str(ctx.body.get("expected_current_hash") or "")
        incoming = ctx.body.get("document") or {}
        if not isinstance(incoming, dict):
            raise HttpError(400, "document must be an object")
        try:
            preview = apply_rig(self.config_path, self._current_rig_raw(), incoming, expected)  # type: ignore[arg-type]
        except ValueError as exc:
            raise HttpError(409, {"error": str(exc), "code": "stale_contract"}) from exc
        if preview["restart_required"]:
            raise HttpError(
                409,
                {
                    "error": "hardware identity changed; restart the Edge process",
                    "code": "restart_required",
                    **preview,
                },
            )
        self.runtime.command("safe")
        if self.config_path is None:
            raise HttpError(409, {"error": "this node has no writable rig file", "code": "restart_required"})
        self.config = load_config(self.config_path)
        self.runtime.config = self.config
        self.runtime.guardrail = ProcessGuardrail(self.config, allow_output=self.runtime.allow_output)
        self.runtime._csv_fields = __import__("certarig.edge.live", fromlist=["csv_fields_for"]).csv_fields_for(
            self.config
        )
        return 200, {**preview, "contract_hash": self.contract_hash}

    def _propose_capabilities(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self._require_operator(ctx)
        from .configurator import propose_capabilities

        if self.capabilities_path is None:
            raise HttpError(409, {"error": "no capabilities file", "code": "restart_required"})
        raw = json.loads(self.capabilities_path.read_text(encoding="utf-8"))
        return 200, propose_capabilities(raw, ctx.body.get("document") or ctx.body)

    def _apply_capabilities(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self._require_operator(ctx)
        from .capabilities import CapabilityManifest
        from .configurator import apply_capabilities

        if self.capabilities_path is None:
            raise HttpError(409, {"error": "no capabilities file", "code": "restart_required"})
        raw = json.loads(self.capabilities_path.read_text(encoding="utf-8"))
        try:
            preview = apply_capabilities(
                self.capabilities_path, raw, ctx.body.get("document") or {}, str(ctx.body.get("expected_current_hash") or "")
            )
        except ValueError as exc:
            raise HttpError(409, {"error": str(exc), "code": "stale_contract"}) from exc
        self.manifest = CapabilityManifest.load(self.capabilities_path)
        return 200, {**preview, "contract_hash": self.contract_hash}

    def _ledger(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        from .ledger import read_outcomes

        procedure_id = (ctx.query.get("procedure_id") or [""])[0] or None
        return 200, {"outcomes": read_outcomes(self.runtime.evidence_dir, procedure_id)}

    def _authoring_templates(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        from .authoring_templates import templates

        return 200, {"templates": templates()}

    def _authoring_build(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        from .authoring_templates import build_procedure

        procedure = build_procedure(
            str(ctx.body.get("template_id") or "blank"),
            signal=str(ctx.body.get("signal") or "pressure"),
            concept=str(ctx.body["concept"]) if ctx.body.get("concept") else None,
            trip=float(ctx.body.get("trip") or 4.2),
            hold_s=float(ctx.body.get("hold_s") or 2.0),
            title=ctx.body.get("title"),
        )
        return 200, {"procedure": procedure}

    def _ack_unclean(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self._require_operator(ctx)
        from .atomic import write_json_atomic
        from .live import utc_now

        path = self.runtime.evidence_dir / "boot" / "unclean_acknowledged.json"
        write_json_atomic(path, {"at": utc_now(), "by": ctx.principal_name})
        self.flags["unclean_shutdown"] = False
        self.flags["unclean_acknowledged"] = True
        return 200, {"status": "acknowledged"}

    def _latest_csv(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        recording = self.runtime.latest_recording()
        if recording is None:
            raise HttpError(404, "no CSV recording is available")
        return 200, recording.read_bytes(), "text/csv; charset=utf-8"

    def _audit_route(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(401, "operator authentication required")
        limit = int(ctx.query.get("limit", ["200"])[0])
        return 200, {"audit": self.audit_log(limit)}

    def _list_approvals(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        status = ctx.query.get("status", [None])[0]
        return 200, {"approvals": self.approvals.list(status)}

    def _get_approval(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        approval = self.approvals.get(ctx.params["approval_id"])
        if approval is None:
            raise HttpError(404, "approval not found")
        return 200, approval.to_dict()

    def _request_approval(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        tool = str(ctx.body.get("tool", ""))
        ctx.tool = tool
        try:
            policy = self.manifest.authorize(tool, Principal.AGENT)
        except CapabilityError as exc:
            raise HttpError(403, exc.to_dict()) from exc
        if policy is not Policy.HUMAN_APPROVAL:
            raise HttpError(400, {"error": f"{tool} does not require human approval", "policy": policy.value})
        args = ctx.body.get("args", {})
        if not isinstance(args, dict):
            raise HttpError(400, "args must be an object")
        approval = self.approvals.request(
            tool, args, str(ctx.body.get("reason", "")), self.contract_hash, requested_by=ctx.principal_name
        )
        return 201, approval.to_dict()

    def _decide(self, ctx: RequestContext, grant: bool) -> tuple[int, dict[str, Any]]:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, "only an operator can decide an approval")
        try:
            approval = self.approvals.decide(ctx.params["approval_id"], grant, ctx.principal_name)
        except KeyError as exc:
            raise HttpError(404, "approval not found") from exc
        except ApprovalError as exc:
            raise HttpError(409, str(exc)) from exc
        return 200, approval.to_dict()

    def _grant_approval(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return self._decide(ctx, True)

    def _deny_approval(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return self._decide(ctx, False)

    # ------------------------------------------------------------------ static
    def static_file(self, path: str) -> tuple[bytes, str] | None:
        if self.static_root is None:
            return None
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (self.static_root / relative).resolve()
        try:
            candidate.relative_to(self.static_root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        content_type, _ = mimetypes.guess_type(candidate.name)
        if candidate.suffix == ".mjs":
            content_type = "text/javascript"
        content_type = content_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/json", "image/svg+xml"}:
            content_type += "; charset=utf-8"
        return candidate.read_bytes(), content_type

    # ---------------------------------------------------------------- lifecycle
    def invoke(
        self,
        method: str,
        path: str,
        headers: Any = None,
        body: dict[str, Any] | None = None,
        query: dict[str, list[str]] | None = None,
    ) -> tuple[int, dict[str, Any] | bytes, str]:
        """Dispatch a request in-process (used by the Studio agent session)."""
        headers = headers or {}
        route, params, path_matched = self.router.match(method, path)
        if route is None:
            raise HttpError(
                405 if path_matched else 404,
                "method not allowed" if path_matched else "route not found",
            )
        principal, name = self.resolve_principal(headers)
        ctx = RequestContext(
            method=method.upper(),
            path=path,
            params=params,
            query=query or {},
            body=body or {},
            principal=principal,
            principal_name=name,
            tool=route.tool,
            policy=None,
        )
        try:
            self.enforce(ctx, route, headers)
            result = route.handler(ctx)
        except HttpError as exc:
            if route.mutating:
                self.audit(ctx, exc.status, exc.payload)
            raise
        if len(result) == 3:
            status, raw, content_type = result
            if route.mutating:
                self.audit(ctx, status)
            return status, raw, content_type
        status, payload = result
        if route.mutating:
            self.audit(ctx, status)
        return status, payload, "application/json"

    def start(self) -> None:
        self.runtime.start()

    def close(self) -> None:
        for extension in self.extensions.values():
            close = getattr(extension, "close", None)
            if callable(close):
                close()
        self.runtime.close()
        from .bootflag import mark_clean

        mark_clean(self.runtime.evidence_dir)


def make_edge_handler(node: EdgeNode) -> type[BaseHTTPRequestHandler]:
    class EdgeHandler(BaseHTTPRequestHandler):
        server_version = "CertaRigEdge/0.4"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            self._send_bytes(status, json.dumps(payload, sort_keys=True).encode("utf-8"), "application/json")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 512_000:
                raise HttpError(413, "request body is too large")
            if length == 0:
                return {}
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise HttpError(400, f"invalid JSON body: {exc.msg}") from exc
            if not isinstance(payload, dict):
                raise HttpError(400, "request body must be a JSON object")
            return payload

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            started = time.monotonic()
            ctx: RequestContext | None = None
            try:
                if method == "GET":
                    static = node.static_file(path)
                    if static is not None:
                        self._send_bytes(200, static[0], static[1])
                        return
                route, params, path_matched = node.router.match(method, path)
                if route is None:
                    raise HttpError(
                        405 if path_matched else 404,
                        "method not allowed" if path_matched else "route not found",
                    )
                body = self._read_json() if method != "GET" else {}
                principal, name = node.resolve_principal(self.headers)
                ctx = RequestContext(
                    method=method,
                    path=path,
                    params=params,
                    query=parse_qs(parsed.query),
                    body=body,
                    principal=principal,
                    principal_name=name,
                    tool=route.tool,
                    policy=None,
                )
                node.enforce(ctx, route, self.headers)
                result = route.handler(ctx)
                if len(result) == 3:
                    status, raw, content_type = result
                    self._send_bytes(status, raw, content_type)
                else:
                    status, payload = result
                    self._send_json(status, payload)
                if route.mutating:
                    node.audit(ctx, status, {"elapsed_ms": round((time.monotonic() - started) * 1000, 3)})
            except HttpError as exc:
                if ctx is not None and method != "GET":
                    node.audit(ctx, exc.status, exc.payload)
                self._send_json(exc.status, exc.payload)
            except KeyError as exc:
                self._send_json(404, {"error": f"resource not found: {exc}"})
            except (TypeError, ValueError) as exc:
                if ctx is not None and method != "GET":
                    node.audit(ctx, 400, {"error": str(exc)})
                self._send_json(400, {"error": str(exc)})
            except RuntimeError as exc:
                if ctx is not None and method != "GET":
                    node.audit(ctx, 409, {"error": str(exc)})
                self._send_json(409, {"error": str(exc)})

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def do_DELETE(self) -> None:
            self._dispatch("DELETE")

    return EdgeHandler


def make_edge_server(node: EdgeNode, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_edge_handler(node))
    server.daemon_threads = True
    return server
