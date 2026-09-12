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

from .approvals import ApprovalError, ApprovalRegistry
from .capabilities import CapabilityError, CapabilityManifest, Policy, Principal
from .live import LiveBenchRuntime


class HttpError(Exception):
    def __init__(self, status: int, payload: dict[str, Any] | str) -> None:
        super().__init__(payload if isinstance(payload, str) else payload.get("error", "error"))
        self.status = status
        self.payload = {"error": payload} if isinstance(payload, str) else payload


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
    pattern: re.Pattern[str]
    handler: Handler
    tool: str | None
    mutating: bool


class Router:
    def __init__(self) -> None:
        self.routes: list[Route] = []

    def add(self, method: str, path: str, handler: Handler, tool: str | None = None) -> None:
        regex = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$"
        self.routes.append(Route(method.upper(), re.compile(regex), handler, tool, method.upper() != "GET"))

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
        static_root: str | Path | None = None,
        audit_size: int = 2000,
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
        self.static_root = Path(static_root).resolve() if static_root else None
        self.approvals = ApprovalRegistry(ttl_s=manifest.approval_ttl_s)
        self.router = Router()
        self.started_at = utc_now()
        self._audit: deque[dict[str, Any]] = deque(maxlen=audit_size)
        self._audit_lock = threading.Lock()
        self.extensions: dict[str, Any] = {}
        self._register_core_routes()

    # ------------------------------------------------------------------ contract
    @property
    def contract_hash(self) -> str:
        return self.manifest.contract_hash(self.config.config_hash)

    def health(self) -> dict[str, Any]:
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
        }

    def rig_document(self) -> dict[str, Any]:
        return {
            "rig": self.config.public_dict(),
            "signals": self.config.signals(),
            "actuators": self.config.actuators(),
            "config_hash": self.config.config_hash,
            "manifest_id": self.manifest.manifest_id,
            "manifest_hash": self.manifest.manifest_hash,
            "contract_hash": self.contract_hash,
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
        operator = headers.get("X-CertaRig-Operator-Key")
        if operator is not None and secrets.compare_digest(operator, self.operator_key):
            return Principal.OPERATOR, str(headers.get("X-CertaRig-Operator", "operator"))
        agent = headers.get("X-CertaRig-Agent-Key")
        if agent is not None and self.agent_key is not None and secrets.compare_digest(agent, self.agent_key):
            return Principal.AGENT, str(headers.get("X-CertaRig-Agent", "agent"))
        return Principal.ANONYMOUS, "anonymous"

    # --------------------------------------------------------------- enforcement
    def enforce(self, ctx: RequestContext, route: Route, headers: Any) -> None:
        if route.tool is None:
            if route.mutating and ctx.principal is Principal.ANONYMOUS:
                raise HttpError(401, "authentication required")
            return
        try:
            policy = self.manifest.authorize(route.tool, ctx.principal)
        except CapabilityError as exc:
            status = 401 if ctx.principal is Principal.ANONYMOUS else 403
            raise HttpError(status, exc.to_dict()) from exc
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
        add("GET", "/v1/rig", lambda ctx: (200, self.rig_document()), "read_rig")
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
    def start(self) -> None:
        self.runtime.start()

    def close(self) -> None:
        for extension in self.extensions.values():
            close = getattr(extension, "close", None)
            if callable(close):
                close()
        self.runtime.close()


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
