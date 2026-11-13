"""Separate trusted observation runtime. It never executes generated source code."""

from __future__ import annotations

import json
import threading
from typing import Any

import jsonschema

from certarig.agent.orchestrator import AgentSession
from certarig.agent.transcript import Transcript

from .contracts import OUTPUT
from .evaluation import system_prompt
from .registry import ScopedRegistry
from .service import Platform
from .store import Actor, uid


class Runtime:
    def __init__(self, platform: Platform, provider_factory: Any, validate_receipt: Any):
        self.platform, self.factory, self.validate_receipt = platform, provider_factory, validate_receipt
        self.id = uid("run")
        self.active: dict[str, Any] = {}
        self.closed = threading.Event()
        self.slot = threading.Lock()

    def guard(self, identifier: str) -> dict[str, Any]:
        s = self.platform.store
        with s.lock:
            row = s.one("SELECT org FROM documents WHERE kind='deployment' AND id=?", (identifier,))
            if not row:
                raise PermissionError("Deployment not found")
            d = s.get("deployment", identifier, row[0])
        actor = Actor(d["reviewer_id"], d["org_id"], "")
        try:
            self.platform.reviewer(actor)
            self.platform.asset(actor, d["asset_id"])
            v = self.platform.version(actor, d["version_id"])
            self._live(d)
            if self.platform.binding(actor, v) != d["binding"]:
                raise PermissionError("Configuration or permission binding changed")
            c = s.get("connection", d["connection_id"], d["org_id"])
            if not c["consent"]:
                raise PermissionError("Model owner consent removed")
            # Network requests never hold the database lock needed by revocation.
            self.validate_receipt(actor, d["evaluation_id"])
            with s.lock:
                current = s.get("deployment", identifier, d["org_id"])
                self._live(current)
                return current
        except (PermissionError, KeyError, ValueError) as exc:
            with s.lock:
                current = s.get("deployment", identifier, d["org_id"])
                if current["status"] == "running":
                    self.platform.pause(current, str(exc))
            raise PermissionError("Observation authority unavailable") from exc

    def _live(self, d: dict[str, Any]) -> None:
        if (
            self.closed.is_set()
            or d["status"] != "running"
            or d["runtime_id"] not in {None, self.id}
            or self.platform.store.clock() >= d["expires_at"]
            or d["assessments"] >= 10
        ):
            raise PermissionError("Deployment inactive, revoked or lease exhausted")

    def tick(self, identifier: str) -> None:
        if not self.slot.acquire(blocking=False):
            return
        provider = None
        try:
            s = self.platform.store
            d = self.guard(identifier)
            if s.clock() < d["next_at"]:
                return
            with s.atomic():
                d = s.get("deployment", identifier, d["org_id"])
                self._live(d)
                d["runtime_id"] = self.id
                # In-flight lease is persisted before inference. Restart cannot resume it.
                d["next_at"] = s.clock() + 30
                s.put("deployment", d)
            v = s.get("version", d["version_id"], d["org_id"])
            c = s.get("connection", d["connection_id"], d["org_id"])
            provider = self.factory(c)
            self.active[identifier] = provider
            asset = s.get("asset", d["asset_id"], d["org_id"])
            registry = ScopedRegistry.connected(
                self.platform.client(asset), v["tools"], lambda: self.guard(identifier)
            )
            transcript = Transcript(
                s.root / "transcripts" / (identifier + "-" + str(d["assessments"]) + ".jsonl")
            )
            session = AgentSession(
                provider, registry, transcript, max_model_calls_per_turn=8, system_prompt=system_prompt(v)
            )
            result = session.send(
                "Assess this enrolled bench in observation mode. Read fresh signals; return the configured JSON output."
            )
            output = json.loads(result.text)
            jsonschema.validate(output, OUTPUT)
            if result.stopped_reason != "end_turn":
                raise ValueError("Incomplete assessment")
            self.guard(identifier)
            with s.atomic():
                current = s.get("deployment", identifier, d["org_id"])
                self._live(current)  # Never publish a late revoked result.
                current["observations"].append(
                    {"at": s.clock(), "output": output, "transcript": Transcript.read(transcript.path)}
                )
                current["assessments"] += 1
                if current["assessments"] >= 10:
                    current.update(status="completed", reason="Assessment limit reached")
                s.put("deployment", current)
                s.audit(
                    d["org_id"],
                    "observation",
                    "runtime",
                    deployment_id=identifier,
                    assessment=current["assessments"],
                )
        except Exception as exc:
            row = self.platform.store.one(
                "SELECT org FROM documents WHERE kind='deployment' AND id=?", (identifier,)
            )
            if row:
                with self.platform.store.lock:
                    current = self.platform.store.get("deployment", identifier, row[0])
                    if current["status"] == "running":
                        self.platform.pause(current, type(exc).__name__ + ": " + str(exc)[:300])
        finally:
            self.active.pop(identifier, None)
            try:
                if provider:
                    provider.close()
            finally:
                self.slot.release()

    def sweep(self) -> None:
        for identifier, provider in list(self.active.items()):
            try:
                self.guard(identifier)
            except (PermissionError, OSError):
                provider.cancel()

    def serve(self) -> None:
        while not self.closed.wait(0.2):
            self.sweep()
            rows = self.platform.store.rows(
                "SELECT body FROM documents WHERE kind='deployment' AND json_extract(body,'$.status')='running'"
            )
            for row in rows:
                d = json.loads(row[0])
                if d["runtime_id"] not in {None, self.id}:
                    self.platform.pause(d, "Runtime restarted; new review required")
                elif d["next_at"] <= self.platform.store.clock() and not self.slot.locked():
                    threading.Thread(target=self.tick, args=(d["id"],), daemon=True).start()

    def close(self) -> None:
        self.closed.set()
        for provider in list(self.active.values()):
            provider.cancel()
