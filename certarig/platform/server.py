"""Loopback-only customer control plane. Edge role headers never authenticate users here."""

from __future__ import annotations

import json
import logging
import mimetypes
import traceback
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from . import evaluation, evidence, health, profiles
from .auth import OIDC
from .service import Platform


class API:
    def __init__(self, platform: Platform, oidc: OIDC, broker: Any, providers: Any):
        self.platform, self.oidc, self.broker, self.providers = platform, oidc, broker, providers
        self.connections: dict[str, Any] = {}
        from .analysis import Analysis
        from .connectors import ConnectorProfiles
        from .tasks import Tasks
        from .workbench import Workbench

        self.workbench = Workbench(platform)
        self.tasks = Tasks(platform, providers, broker)
        self.analysis = Analysis(platform, broker)
        self.connector_profiles = ConnectorProfiles(platform)

    def route(self, actor: Any, method: str, parts: list[str], body: dict[str, Any]) -> Any:
        p = self.platform
        from . import workbench_api

        handled, response = workbench_api.route(self, actor, method, parts, body)
        if handled:
            return response
        if parts == ["openapi.json"] and method == "GET":
            import yaml

            return yaml.safe_load(
                (Path(__file__).resolve().parents[1] / "schemas" / "platform.openapi.yaml").read_text()
            )
        if parts == ["auth", "members"] and method == "GET":
            p.reviewer(actor)
            return {
                "members": [
                    dict(r)
                    for r in p.store.rows(
                        "SELECT user_id,role FROM memberships WHERE org_id=? AND enabled=1", (actor.org_id,)
                    )
                ]
            }
        if parts == ["agents", "evaluations"] and method == "GET":
            accessible = {a["id"] for a in p.assets(actor)}
            return {
                "evaluations": [
                    e for e in p.store.listing("evaluation", actor.org_id) if e["asset_id"] in accessible
                ]
            }
        if parts == ["agents", "preflight"] and method == "GET":
            return self.broker.call("preflight", actor.org_id + "/" + actor.user_id, "agent", {})
        if parts == ["assets"] and method == "GET":
            return {"assets": p.assets(actor)}
        if parts == ["assets", "pair"] and method == "POST":
            return p.pair(actor, body["connector"])
        if parts == ["assets", "enroll"] and method == "POST":
            return p.enroll(actor, body["code"])
        if (
            len(parts) == 4
            and parts[0] == "assets"
            and parts[2:] == ["profile-review", "preview"]
            and method == "POST"
        ):
            return profiles.preview(p, actor, parts[1])
        if len(parts) == 3 and parts[0] == "assets":
            if parts[2] == "grants" and method == "POST":
                return p.grant(actor, parts[1], body["user_id"], body["enabled"])
            if parts[2] == "tools" and method == "GET":
                return {"tools": p.observation_tools(actor, parts[1])}
            if parts[2] == "profiles" and method == "GET":
                return {"profiles": profiles.history(p, actor, parts[1])}
            if parts[2] == "profile-review":
                if method == "POST" and set(body) == {"review_id"}:
                    return profiles.accept(p, actor, parts[1], body["review_id"])
                raise ValueError("Expected a reviewed profile preview identifier")
            if method == "GET":
                return p.read_asset(actor, parts[1], parts[2])
        if parts == ["model-connections"]:
            if method == "POST":
                return p.connection(actor, body)
            if method == "GET":
                return {
                    "connections": [
                        c
                        for c in p.store.listing("connection", actor.org_id)
                        if c["owner_id"] == actor.user_id
                    ]
                }
        if len(parts) == 3 and parts[0] == "model-connections" and method == "POST":
            c = p.owned_connection(actor, parts[1])
            if parts[2] == "disconnect":
                disconnected = p.disconnect(actor, c["id"])
                previous = self.connections.pop(c["id"], None)
                if previous:
                    previous.close()
                return disconnected
            if not c["enabled"]:
                raise PermissionError("Model connection is disconnected; create a new connection")
            provider = (
                self.connections.setdefault(c["id"], self.providers(c))
                if c["id"] not in self.connections
                else self.connections[c["id"]]
            )
            if parts[2] == "login":
                return provider.login()
            if parts[2] == "status":
                result = provider.account()
                with p.store.atomic():
                    current = p.owned_connection(actor, c["id"])
                    if not current["enabled"] or current["revision"] != c["revision"]:
                        raise PermissionError("Model status response belongs to a disconnected connection")
                    current["status"] = "connected" if result["connected"] else "not_connected"
                    p.store.put("connection", current)
                return result
        if parts == ["agents"]:
            if method == "GET":
                return {"versions": p.versions(actor)}
            if method == "POST":
                return p.create_version(actor, body)
        if len(parts) == 3 and parts[0] == "agents" and parts[2] == "versions" and method == "POST":
            return p.create_version(actor, body, parts[1])
        if len(parts) == 3 and parts[0] == "agents" and parts[2] == "evaluate" and method == "POST":
            v = p.version(actor, parts[1])
            if v["author_id"] != actor.user_id:
                raise PermissionError("Only the author may evaluate this version")
            # Provider calls run in this control-plane process, never in Edge or worker containers.
            return evaluation.collect(p, actor, v, self.providers)
        if len(parts) == 3 and parts[0] == "agents" and parts[1] == "evaluations":
            e = p.store.get("evaluation", parts[2], actor.org_id)
            p.version(actor, e["version_id"])
            if method == "GET":
                return e
            if method == "POST":
                return evaluation.qualify(p, actor, e["id"], self.broker)
        if parts == ["deployments", "runtime"] and method == "GET":
            return {
                "runtime": health.status(p.store)
                if p.assets(actor)
                else {"state": "unavailable", "heartbeat_at": None}
            }
        if parts == ["deployments"] and method == "GET":
            return {
                "deployments": [{**d, "runtime_health": health.status(p.store)} for d in p.deployments(actor)]
            }
        if parts == ["deployments", "review"] and method == "POST":
            p.reviewer(actor)
            evaluation.validate(p, actor, body["evaluation_id"], self.broker)
            return p.review(actor, body["version_id"], body["evaluation_id"])
        if len(parts) == 2 and parts[0] == "deployments" and method == "GET":
            return p.present_deployment(actor, parts[1])
        if len(parts) == 3 and parts[0] == "deployments":
            d = p.deployment(actor, parts[1])
            if parts[2] == "events" and method == "GET":
                return {"events": p.store.events(actor.org_id, d["id"])}
            if parts[2] == "export" and method == "GET":
                return evidence.export(p, actor, d["id"])
            if parts[2] == "start" and method == "POST":
                evaluation.validate(p, actor, d["evaluation_id"], self.broker)
                return p.start(actor, d["id"])
            if parts[2] == "revoke" and method == "POST":
                return p.revoke(actor, d["id"])
        raise KeyError("Endpoint not found")

    def close(self) -> None:
        self.tasks.close()
        for provider in self.connections.values():
            provider.close()


def server(api: API, port: int = 18090, studio: Path | None = None) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass  # Login codes and callback query strings must never reach access logs.

        def reply(self, status: int, value: Any, headers: dict[str, str] | None = None) -> None:
            raw = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            if "Content-Type" not in (headers or {}):
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            for key, val in (headers or {}).items():
                self.send_header(key, val)
            self.end_headers()
            self.wfile.write(raw)

        def handle_request(self) -> None:
            try:
                token = ""
                host = self.headers.get("Host", "")
                expected = "127.0.0.1:" + str(cast(ThreadingHTTPServer, self.server).server_port)
                if host != expected:
                    raise PermissionError("Use the configured loopback origin")
                parsed = urlsplit(self.path)
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))
                token = cookies["certarig_session"].value if "certarig_session" in cookies else ""
                method = self.command
                if method == "POST":
                    if self.headers.get("Origin") != "http://" + expected:
                        raise PermissionError("Same-origin request required")
                    n = int(self.headers.get("Content-Length", "0"))
                    if (
                        not 0 < n <= 1024 * 1024
                        or self.headers.get("Content-Type", "").split(";")[0] != "application/json"
                    ):
                        raise ValueError("Expected bounded JSON request")
                    body = json.loads(self.rfile.read(n))
                    if not isinstance(body, dict):
                        raise ValueError("JSON object required")
                else:
                    body = {}
                if parsed.path == "/v1/auth/login" and method == "GET":
                    url, browser = api.oidc.start()
                    self.reply(
                        302,
                        {},
                        {
                            "Location": url,
                            "Set-Cookie": "certarig_login="
                            + browser
                            + "; Path=/v1/auth; HttpOnly; SameSite=Lax; Max-Age=300",
                        },
                    )
                    return
                if parsed.path == "/v1/auth/callback" and method == "GET":
                    query = parse_qs(parsed.query)
                    session, _ = api.oidc.finish(
                        query["state"][0],
                        query["code"][0],
                        cookies["certarig_login"].value if "certarig_login" in cookies else "",
                    )
                    self.reply(
                        302,
                        {},
                        {
                            "Location": "/",
                            "Set-Cookie": "certarig_session="
                            + session
                            + "; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800",
                        },
                    )
                    return
                if not parsed.path.startswith("/v1/") and method == "GET" and studio:
                    relative = "platform.html" if parsed.path == "/" else parsed.path.lstrip("/")
                    # Only the new product shell and its static dependencies, never arbitrary repository paths.
                    if relative not in {
                        "platform.html",
                        "styles.css",
                        "platform.css",
                        "src/platform.mjs",
                        "src/workbench.mjs",
                    }:
                        raise KeyError("Static file not found")
                    path = studio / relative
                    self.reply(
                        200,
                        path.read_bytes(),
                        {"Content-Type": mimetypes.guess_type(str(path))[0] or "text/javascript"},
                    )
                    return
                actor, csrf = api.platform.store.session(
                    token, self.headers.get("X-CSRF-Token", "") if method == "POST" else None
                )
                if parsed.path == "/v1/auth/me" and method == "GET":
                    self.reply(
                        200,
                        {"user_id": actor.user_id, "org_id": actor.org_id, "role": actor.role, "csrf": csrf},
                    )
                    return
                if parsed.path == "/v1/auth/logout" and method == "POST":
                    api.platform.store.logout(token)
                    self.reply(
                        200,
                        {"logged_out": True},
                        {"Set-Cookie": "certarig_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"},
                    )
                    return
                result = api.route(actor, method, parsed.path.removeprefix("/v1/").split("/"), body)
                self.reply(
                    200,
                    result,
                    {
                        "Content-Type": "application/zip",
                        "Content-Disposition": 'attachment; filename="certarig-agent-evidence.zip"',
                    }
                    if isinstance(result, bytes)
                    else None,
                )
            except PermissionError as exc:
                self.reply(403 if token else 401, {"error": str(exc)})
            except KeyError:
                self.reply(404, {"error": "Resource not found or unavailable"})
            except (ValueError, TypeError) as exc:
                self.reply(409, {"error": str(exc)[:500]})
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "Local dependency %s\n%s",
                    type(exc).__name__,
                    "".join(traceback.format_tb(exc.__traceback__)),
                )
                self.reply(
                    503,
                    {
                        "error": "Local dependency unavailable; inspect server configuration and resource preflight"
                    },
                )

        do_GET = handle_request
        do_POST = handle_request

    value = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    value.daemon_threads = True
    return value
