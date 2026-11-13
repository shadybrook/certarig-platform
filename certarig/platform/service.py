"""Customer lifecycle with server-derived identity, immutable versions and exact review bindings."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlsplit

from certarig.edge.client import EdgeClient

from .contracts import OUTPUT, READ_TOOLS, SUITE, VERIFIER, fingerprint
from .store import Actor, Store, uid


class Platform:
    def __init__(
        self,
        store: Store,
        connectors: dict[str, dict[str, Any]],
        client_factory: Any = EdgeClient,
        *,
        recover: bool = True,
    ) -> None:
        self.store, self.connectors, self.client_factory = store, connectors, client_factory
        for config in connectors.values():
            p = urlsplit(config["url"])
            if (
                p.scheme != "http"
                or p.hostname != "127.0.0.1"
                or p.username
                or p.password
                or p.path not in {"", "/"}
                or p.query
                or p.fragment
            ):
                raise ValueError("Only administrator-registered loopback simulator connectors are supported")
        # Server startup restores history, never execution authority.
        for row in (
            store.db.execute("SELECT body FROM documents WHERE kind='deployment'").fetchall()
            if recover
            else []
        ):
            import json

            d = json.loads(row[0])
            if d["status"] in {"running", "approved"}:
                d.update(status="interrupted", reason="Control plane restarted; new review required")
                store.put("deployment", d)
                store.audit(d["org_id"], "interrupted", "system", deployment_id=d["id"])

    def actor(self, actor: Actor) -> Actor:
        return self.store.actor(actor.user_id, actor.org_id)

    def reviewer(self, actor: Actor) -> Actor:
        actual = self.actor(actor)
        if actual.role != "reviewer":
            raise PermissionError("Independent Reviewer permission required")
        return actual

    def grant(self, actor: Actor, asset_id: str, user_id: str, enabled: bool) -> dict[str, Any]:
        self.reviewer(actor)
        if not isinstance(enabled, bool):
            raise ValueError("Asset grant enabled must be a boolean")
        self.store.get("asset", asset_id, actor.org_id)
        self.store.actor(user_id, actor.org_id)
        with self.store.atomic():
            value = self.store.put(
                "grant",
                {
                    "id": asset_id + "_" + user_id,
                    "org_id": actor.org_id,
                    "asset_id": asset_id,
                    "user_id": user_id,
                    "enabled": bool(enabled),
                },
            )
            self.store.audit(
                actor.org_id,
                "asset_grant_changed",
                actor.user_id,
                asset_id=asset_id,
                user_id=user_id,
                enabled=enabled,
            )
            if not enabled:
                for d in self.store.listing("deployment", actor.org_id):
                    if (
                        d["asset_id"] == asset_id
                        and d["author_id"] == user_id
                        and d["status"] in {"approved", "running"}
                    ):
                        self.pause(d, "Asset permission removed")
        return value

    def asset(self, actor: Actor, asset_id: str) -> dict[str, Any]:
        self.actor(actor)
        asset = self.store.get("asset", asset_id, actor.org_id)
        grant = self.store.get("grant", asset_id + "_" + actor.user_id, actor.org_id)
        if not grant["enabled"]:
            raise PermissionError("Asset access revoked")
        return asset

    def assets(self, actor: Actor) -> list[dict[str, Any]]:
        result = []
        for value in self.store.listing("asset", actor.org_id):
            try:
                result.append(self.asset(actor, value["id"]))
            except (PermissionError, KeyError):
                continue
        return result

    def pair(self, actor: Actor, connector: str) -> dict[str, Any]:
        self.reviewer(actor)
        if connector not in self.connectors:
            raise ValueError("Unknown simulator connector")
        if self.connectors[connector].get("org_id") != actor.org_id:
            raise PermissionError("Connector is not registered to this organization")
        token = secrets.token_urlsafe(24)
        self.store.transaction("pair", token, {"org_id": actor.org_id, "connector": connector})
        return {"code": token, "expires_in": 300, "connector": connector}

    def enroll(self, actor: Actor, code: str) -> dict[str, Any]:
        self.reviewer(actor)
        tx = self.store.consume("pair", code)
        if tx["org_id"] != actor.org_id:
            raise PermissionError("Pairing belongs to another organization")
        config = self.connectors[tx["connector"]]
        if config.get("org_id") != actor.org_id:
            raise PermissionError("Connector organization registration changed")
        client = self.client_factory(config["url"], auditor_key=config["auditor_key"])
        rig = client.rig()
        if rig["rig"]["hardware"]["mode"] != "simulator":
            raise ValueError("Physical enrollment is not supported")
        with self.store.atomic():
            if self.store.one(
                "SELECT 1 FROM documents WHERE kind='asset' AND json_extract(body,'$.connector')=?",
                (tx["connector"],),
            ):
                raise ValueError("Connector is already enrolled")
            value = {
                "id": uid("ast"),
                "org_id": actor.org_id,
                "connector": tx["connector"],
                "name": config["name"],
                "profile_hash": rig["config_hash"],
                "mode": "simulator",
                "profile": rig,
            }
            self.store.secret(value["id"], {"url": config["url"], "auditor_key": config["auditor_key"]})
            self.store.put("asset", value)
            self.store.put(
                "grant",
                {
                    "id": value["id"] + "_" + actor.user_id,
                    "org_id": actor.org_id,
                    "asset_id": value["id"],
                    "user_id": actor.user_id,
                    "enabled": True,
                },
            )
            self.store.audit(actor.org_id, "asset_enrolled", actor.user_id, asset_id=value["id"])
        return value

    def client(self, asset: dict[str, Any]) -> Any:
        secret = self.store.secret(asset["id"])
        return self.client_factory(secret["url"], auditor_key=secret["auditor_key"])

    def read_asset(self, actor: Actor, asset_id: str, resource: str) -> dict[str, Any]:
        if resource not in {"rig", "signals", "state", "capabilities"}:
            raise ValueError("Unsupported read")
        asset = self.asset(actor, asset_id)
        return dict(getattr(self.client(asset), resource)())

    def connection(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        self.actor(actor)
        if set(body) - {"backend", "model", "consent"}:
            raise ValueError("Unsupported model connection fields")
        if (
            body.get("backend") not in {"codex", "fixture"}
            or not isinstance(body.get("model"), str)
            or not 0 < len(body["model"]) <= 120
        ):
            raise ValueError("Choose a supported backend and explicit model")
        c = {
            "id": uid("mdl"),
            "org_id": actor.org_id,
            "owner_id": actor.user_id,
            "backend": body["backend"],
            "model": body["model"],
            "consent": body.get("consent") is True,
            "enabled": True,
            "revision": 1,
            "status": "not_connected" if body["backend"] == "codex" else "deterministic_fixture",
        }
        return self.store.put("connection", c)

    def owned_connection(self, actor: Actor, identifier: str) -> dict[str, Any]:
        self.actor(actor)
        c = self.store.get("connection", identifier, actor.org_id)
        if c["owner_id"] != actor.user_id:
            raise PermissionError("Model connection belongs to another user")
        return c

    def disconnect(self, actor: Actor, identifier: str) -> dict[str, Any]:
        with self.store.atomic():
            c = self.owned_connection(actor, identifier)
            c.update(enabled=False, consent=False, revision=c["revision"] + 1, status="disconnected")
            self.store.put("connection", c)
            for d in self.store.listing("deployment", actor.org_id):
                if d["connection_id"] == identifier and d["status"] in {"approved", "running"}:
                    self.pause(d, "Model connection consent removed")
            return c

    def versions(self, actor: Actor) -> list[dict[str, Any]]:
        values = []
        for v in self.store.listing("version", actor.org_id):
            try:
                self.asset(actor, v["asset_id"])
                values.append(v)
            except (PermissionError, KeyError):
                continue
        return values

    def version(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.store.get("version", identifier, actor.org_id)
        self.asset(actor, value["asset_id"])
        return value

    def create_version(
        self, actor: Actor, body: dict[str, Any], agent_id: str | None = None
    ) -> dict[str, Any]:
        self.actor(actor)
        if set(body) != {"name", "instructions", "asset_id", "connection_id", "tools"}:
            raise ValueError("An agent requires name, instructions, asset, model connection and tools")
        if not all(
            isinstance(body[k], str) and 0 < len(body[k]) <= n
            for k, n in [("name", 120), ("instructions", 8000)]
        ):
            raise ValueError("Invalid agent name or instructions")
        asset = self.asset(actor, body["asset_id"])
        c = self.owned_connection(actor, body["connection_id"])
        if not c["enabled"]:
            raise ValueError("Model connection is disabled")
        tools = body["tools"]
        if (
            not isinstance(tools, list)
            or not tools
            or not all(isinstance(t, str) and t in READ_TOOLS for t in tools)
            or len(set(tools)) != len(tools)
        ):
            raise ValueError("Only distinct observation tools are allowed")
        caps = self.client(asset).capabilities()
        if not set(tools) <= {t["name"] for t in caps["agent_tools"]}:
            raise ValueError("Tool is not supported by this connector")
        with self.store.atomic():
            previous = (
                [v for v in self.store.listing("version", actor.org_id) if v["agent_id"] == agent_id]
                if agent_id
                else []
            )
            if agent_id and (not previous or any(v["author_id"] != actor.user_id for v in previous)):
                raise PermissionError("Only the author may create a new agent version")
            value = {
                "id": uid("ver"),
                "org_id": actor.org_id,
                "asset_id": body["asset_id"],
                "author_id": actor.user_id,
                "agent_id": agent_id or uid("agt"),
                "revision": len(previous) + 1,
                **body,
                "output_contract": OUTPUT,
                "limits": {"interval_s": 30, "max_assessments": 10, "lease_s": 900, "model_calls": 8},
            }
            value["hash"] = fingerprint(value)
            self.store.put("version", value)
            self.store.audit(actor.org_id, "agent_version_created", actor.user_id, version_id=value["id"])
            return value

    def binding(self, actor: Actor, version: dict[str, Any]) -> dict[str, Any]:
        asset = self.asset(actor, version["asset_id"])
        c = self.store.get("connection", version["connection_id"], actor.org_id)
        self.store.actor(version["author_id"], actor.org_id)
        self.asset(Actor(version["author_id"], actor.org_id, ""), asset["id"])
        if not c["enabled"] or c["owner_id"] != version["author_id"]:
            raise PermissionError("Model connection is no longer authorized")
        rig = self.client(asset).rig()
        if rig["config_hash"] != asset["profile_hash"] or rig["rig"]["hardware"]["mode"] != "simulator":
            raise ValueError("Asset profile changed; enroll/revalidate before review")
        caps = self.client(asset).capabilities()
        if not set(version["tools"]) <= {t["name"] for t in caps["agent_tools"]}:
            raise PermissionError("Connector capabilities changed")
        return {
            "version_hash": version["hash"],
            "connection_id": c["id"],
            "connection_revision": c["revision"],
            "backend": c["backend"],
            "model": c["model"],
            "asset_id": asset["id"],
            "profile_hash": asset["profile_hash"],
            "tools": sorted(version["tools"]),
            "capabilities_hash": fingerprint(caps),
            "suite": SUITE,
            "verifier": VERIFIER,
        }

    def review(self, actor: Actor, version_id: str, evaluation_id: str) -> dict[str, Any]:
        self.reviewer(actor)
        v = self.version(actor, version_id)
        if actor.user_id == v["author_id"]:
            raise PermissionError("An author cannot review their own version")
        e = self.store.get("evaluation", evaluation_id, actor.org_id)
        binding = self.binding(actor, v)
        if (
            e["version_id"] != v["id"]
            or e["binding"] != binding
            or e["status"] != "passed"
            or not e.get("trusted")
        ):
            raise ValueError("Matching trusted Sandbox evaluation required")
        c = self.store.get("connection", v["connection_id"], actor.org_id)
        if not c["consent"]:
            raise PermissionError("Model owner has not consented to deployment")
        # Runner/verifier policy is rechecked by the evaluation service, before this method.
        with self.store.atomic():
            d = {
                "id": uid("dep"),
                "org_id": actor.org_id,
                "asset_id": v["asset_id"],
                "version_id": v["id"],
                "evaluation_id": e["id"],
                "author_id": v["author_id"],
                "reviewer_id": actor.user_id,
                "connection_id": c["id"],
                "binding": binding,
                "runner_image": e["runner_image"],
                "policy_hash": e["policy_hash"],
                "mode": "observation",
                "status": "approved",
                "reviewed_at": self.store.clock(),
                "assessments": 0,
                "observations": [],
            }
            self.store.put("deployment", d)
            self.store.audit(
                actor.org_id,
                "reviewed_observation_only",
                actor.user_id,
                deployment_id=d["id"],
                binding=binding,
            )
            return d

    def deployment(self, actor: Actor, identifier: str) -> dict[str, Any]:
        d = self.store.get("deployment", identifier, actor.org_id)
        self.asset(actor, d["asset_id"])
        return d

    def start(self, actor: Actor, identifier: str) -> dict[str, Any]:
        self.reviewer(actor)
        with self.store.atomic():
            d = self.deployment(actor, identifier)
            if (
                d["reviewer_id"] != actor.user_id
                or d["status"] != "approved"
                or self.store.clock() - d["reviewed_at"] > 900
            ):
                raise ValueError("Fresh approval by this reviewer required")
            v = self.version(actor, d["version_id"])
            if self.binding(actor, v) != d["binding"]:
                raise ValueError("Review binding changed")
            if self.store.db.execute(
                "SELECT 1 FROM documents WHERE kind='deployment' AND json_extract(body,'$.status')='running'"
            ).fetchone():
                raise ValueError("Only one observation deployment may run")
            now = self.store.clock()
            d.update(status="running", started_at=now, expires_at=now + 900, next_at=now, runtime_id=None)
            self.store.put("deployment", d)
            self.store.audit(actor.org_id, "started", actor.user_id, deployment_id=d["id"])
            return d

    def pause(self, d: dict[str, Any], reason: str) -> None:
        d.update(status="paused", reason=reason)
        self.store.put("deployment", d)
        self.store.audit(d["org_id"], "paused", "system", deployment_id=d["id"], reason=reason)

    def revoke(self, actor: Actor, identifier: str) -> dict[str, Any]:
        with self.store.atomic():
            d = self.deployment(actor, identifier)
            if actor.user_id != d["author_id"]:
                self.reviewer(actor)
            d.update(status="revoked", reason="Access revoked by operator")
            self.store.put("deployment", d)
            self.store.audit(actor.org_id, "revoked", actor.user_id, deployment_id=d["id"])
            return d
