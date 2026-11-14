"""Separate trusted observation runtime. It never executes generated source code."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

import jsonschema

from certarig.agent.orchestrator import AgentSession
from certarig.agent.transcript import Transcript

from . import health
from .contracts import OUTPUT
from .evaluation import system_prompt
from .registry import ScopedRegistry
from .service import Platform
from .store import Actor, uid


class Runtime:
    def __init__(self, platform: Platform, provider_factory: Any, validate_receipt: Any, broker: Any = None):
        self.platform, self.factory, self.validate_receipt = platform, provider_factory, validate_receipt
        self.broker = broker
        self.id = uid("run")
        self.active: dict[str, Any] = {}
        self.closed = threading.Event()
        self.slot = threading.Lock()
        self.heartbeat_thread: threading.Thread | None = None
        self.workers: list[threading.Thread] = []
        health.claim(platform, self.id)

    def guard(self, identifier: str) -> dict[str, Any]:
        s = self.platform.store
        with s.lock:
            row = s.one("SELECT org FROM documents WHERE kind='deployment' AND id=?", (identifier,))
            if not row:
                raise PermissionError("Deployment not found")
            d = health.reconcile(self.platform, s.get("deployment", identifier, row[0]))
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
            or health.status(self.platform.store)["state"] != "online"
            or health.status(self.platform.store)["runtime_id"] != self.id
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
                d["next_at"] = (
                    s.clock() + s.get("version", d["version_id"], d["org_id"])["limits"]["interval_s"]
                )
                s.put("deployment", d)
            v = s.get("version", d["version_id"], d["org_id"])
            c = s.get("connection", d["connection_id"], d["org_id"])
            self.activity(identifier, "connecting", "connecting_model")
            provider = self.factory(c)
            self.activity(identifier, "assessing", "model")
            self.active[identifier] = provider
            asset = s.get("asset", d["asset_id"], d["org_id"])
            if v.get("team_members"):
                provider.close()
                provider = None
                from . import teams

                def activate(member_provider: Any) -> None:
                    self.active[identifier] = member_provider

                team_result = teams.run(
                    self.platform,
                    Actor(d["author_id"], d["org_id"], ""),
                    v,
                    self.factory,
                    lambda member: self.registry(d, member, asset),
                    s.root / "transcripts" / (identifier + "-" + str(d["assessments"]) + ".jsonl"),
                    "Assess this enrolled bench in observation mode. Read fresh signals and delegate within the reviewed team.",
                    lambda: self.guard(identifier),
                    activate,
                )
                output = team_result["output"]
                transcript_rows = team_result["transcript"]
            else:
                registry = self.registry(d, v, asset)
                transcript = Transcript(
                    s.root / "transcripts" / (identifier + "-" + str(d["assessments"]) + ".jsonl")
                )
                session = AgentSession(
                    provider,
                    registry,
                    transcript,
                    max_model_calls_per_turn=v["limits"]["model_calls"],
                    system_prompt=system_prompt(v),
                    on_event=lambda event: self.trace_activity(identifier, event),
                )
                result = session.send(
                    "Assess this enrolled bench in observation mode. Read fresh signals; return the configured JSON output."
                )
                output = json.loads(result.text)
                transcript_rows = Transcript.read(transcript.path)
                if result.stopped_reason != "end_turn":
                    raise ValueError("Incomplete assessment")
            jsonschema.validate(output, OUTPUT)
            self.guard(identifier)
            with s.atomic():
                current = s.get("deployment", identifier, d["org_id"])
                self._live(current)  # Never publish a late revoked result.
                current["observations"].append(
                    {
                        "at": s.clock(),
                        "output": output,
                        "transcript": transcript_rows,
                        **({"team": team_result} if v.get("team_members") else {}),
                    }
                )
                current["assessments"] += 1
                current.update(
                    provider_status="idle", activity="waiting_for_assessment", last_assessment_at=s.clock()
                )
                if current["assessments"] >= v["limits"]["max_assessments"]:
                    current.update(
                        status="completed",
                        reason="Assessment limit reached",
                        provider_status="completed",
                        activity="stopped",
                    )
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
                        current.update(provider_status="error", last_provider_error=type(exc).__name__)
                        self.platform.store.put("deployment", current)
        finally:
            self.active.pop(identifier, None)
            try:
                if provider:
                    provider.close()
            except Exception as exc:
                s = self.platform.store
                with s.atomic():
                    current = s.get("deployment", identifier, d["org_id"])
                    if current["status"] == "running":
                        self.platform.pause(current, "Provider cleanup failed; independent review required")
                        current.update(provider_status="error", last_provider_error=type(exc).__name__)
                        s.put("deployment", current)
            finally:
                self.slot.release()

    def registry(self, deployment: dict[str, Any], version: dict[str, Any], asset: dict[str, Any]) -> Any:
        def guard() -> dict[str, Any]:
            return self.guard(deployment["id"])

        base = ScopedRegistry.connected(self.platform.client(asset), version["tools"], guard)
        if not version.get("analysis_tools"):
            return base
        if self.broker is None:
            raise PermissionError("Isolated analysis broker unavailable")
        from .analysis import Analysis, AnalysisRegistry

        return AnalysisRegistry(
            base,
            Analysis(self.platform, self.broker),
            Actor(version["author_id"], version["org_id"], ""),
            version,
            guard,
            deployment["id"],
        )

    def activity(self, identifier: str, provider_status: str, activity: str) -> None:
        s = self.platform.store
        with s.atomic():
            row = s.one("SELECT org FROM documents WHERE kind='deployment' AND id=?", (identifier,))
            if not row:
                raise PermissionError("Deployment not found")
            d = s.get("deployment", identifier, row[0])
            self._live(d)
            d.update(provider_status=provider_status, activity=activity, activity_at=s.clock())
            s.put("deployment", d)

    def trace_activity(self, identifier: str, event: dict[str, Any]) -> None:
        if event["kind"] == "tool_call":
            self.activity(identifier, "using_tool", event["name"])
        elif event["kind"] in {"tool_result", "model_response"}:
            self.activity(identifier, "assessing", "model")

    def sweep(self) -> None:
        # Cancellation does not wait for connector I/O or the Sandbox verifier.
        s = self.platform.store
        for identifier, provider in list(self.active.items()):
            try:
                row = s.one("SELECT org FROM documents WHERE kind='deployment' AND id=?", (identifier,))
                if not row:
                    raise PermissionError("Deployment not found")
                d = health.reconcile(self.platform, s.get("deployment", identifier, row[0]))
                self._live(d)
                actor = Actor(d["reviewer_id"], d["org_id"], "")
                self.platform.reviewer(actor)
                self.platform.asset(actor, d["asset_id"])
                self.platform.asset(Actor(d["author_id"], d["org_id"], ""), d["asset_id"])
                c = s.get("connection", d["connection_id"], d["org_id"])
                for member in d["binding"].get("team_members", []):
                    mc = s.get("connection", member["connection_id"], d["org_id"])
                    if (
                        not mc["enabled"]
                        or not mc["consent"]
                        or mc["revision"] != member["connection_revision"]
                    ):
                        raise PermissionError("Specialist consent removed")
                if (
                    not c["enabled"]
                    or not c["consent"]
                    or c["revision"] != d["binding"]["connection_revision"]
                ):
                    raise PermissionError("Model connection authorization changed")
            except (PermissionError, KeyError, ValueError):
                try:
                    provider.cancel()
                except Exception:
                    pass  # Tool guards and late-result checks still deny authority.

    def _heartbeat_loop(self) -> None:
        while not self.closed.wait(health.HEARTBEAT_S):
            try:
                health.pulse(self.platform, self.id)
                self.sweep()
            except (PermissionError, OSError):
                self.closed.set()
                self.sweep()
                return

    def serve(self) -> None:
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        while not self.closed.wait(0.2):
            self.sweep()
            rows = self.platform.store.rows(
                "SELECT body FROM documents WHERE kind='deployment' AND json_extract(body,'$.status')='running'"
            )
            for row in rows:
                d = json.loads(row[0])
                if d["runtime_id"] != self.id:
                    health.reconcile(self.platform, d)
                elif d["next_at"] <= self.platform.store.clock() and not self.slot.locked():
                    self.workers = [worker for worker in self.workers if worker.is_alive()]
                    worker = threading.Thread(target=self.tick, args=(d["id"],), daemon=True)
                    self.workers.append(worker)
                    worker.start()

    def close(self) -> None:
        self.closed.set()
        health.stop(self.platform, self.id)
        for provider in list(self.active.values()):
            try:
                provider.cancel()
            except Exception:
                pass
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)
        deadline = time.monotonic() + 2
        for worker in self.workers:
            worker.join(timeout=max(0, deadline - time.monotonic()))
