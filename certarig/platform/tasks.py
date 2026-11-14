"""Durable bounded task collection; no worker is resumed after a server restart."""

from __future__ import annotations

import threading
from typing import Any

from . import evaluation
from .store import Actor, uid

TERMINAL = {"completed", "failed", "cancelled", "interrupted"}


class Tasks:
    def __init__(self, platform: Any, providers: Any, broker: Any):
        self.p, self.s, self.providers, self.broker = platform, platform.store, providers, broker
        self.stop = threading.Event()
        self.slot = threading.Lock()
        self.workers: list[threading.Thread] = []
        self.providers_active: dict[str, Any] = {}
        self.cancel_events: dict[str, threading.Event] = {}
        for row in self.s.rows("SELECT body FROM documents WHERE kind='task'"):
            import json

            task = json.loads(row[0])
            if task["status"] not in TERMINAL:
                task.update(status="interrupted", error="Control plane restarted; submit a new task")
                self.s.put("task", task)
                self.event(task, "interrupted")

    def get(self, actor: Actor, identifier: str) -> dict[str, Any]:
        task = self.s.get("task", identifier, actor.org_id)
        self.p.asset(actor, task["asset_id"])
        if actor.user_id != task["owner_id"]:
            self.p.reviewer(actor)
        return task

    def listing(self, actor: Actor) -> list[dict[str, Any]]:
        self.p.actor(actor)
        result = []
        for row in self.s.listing("task", actor.org_id):
            try:
                result.append(self.get(actor, row["id"]))
            except (KeyError, PermissionError):
                continue
        return result

    def event(self, task: dict[str, Any], kind: str, **fields: Any) -> None:
        self.s.audit(task["org_id"], kind, task["owner_id"], task_id=task["id"], **fields)

    def events(self, actor: Actor, identifier: str, after: int = 0) -> dict[str, Any]:
        self.get(actor, identifier)
        if not isinstance(after, int) or after < 0:
            raise ValueError("Invalid event cursor")
        import json

        rows = []
        for row in self.s.rows(
            "SELECT seq,body FROM audit WHERE org=? AND seq>? AND json_extract(body,'$.task_id')=? ORDER BY seq LIMIT 4096",
            (actor.org_id, after, identifier),
        ):
            entry = json.loads(row[1])
            if entry.get("task_id") == identifier:
                rows.append({"cursor": row[0], **entry})
        return {"events": rows, "cursor": rows[-1]["cursor"] if rows else after}

    def submit(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {"kind", "target_id"} or body["kind"] not in {"evaluate", "qualify", "team_evaluate"}:
            raise ValueError("Choose an evaluation, qualification or team evaluation task")
        target = (
            self.p.store.get("evaluation", body["target_id"], actor.org_id)
            if body["kind"] == "qualify"
            else self.p.version(actor, body["target_id"])
        )
        version = self.p.version(actor, target["version_id"]) if body["kind"] == "qualify" else target
        if version["author_id"] != actor.user_id:
            raise PermissionError("Only the author may submit evaluation work")
        self.p.binding(actor, version)
        with self.s.atomic():
            self.p.asset(actor, version["asset_id"])
            if (
                self.stop.is_set()
                or sum(t["status"] not in TERMINAL for t in self.s.listing("task", actor.org_id)) >= 8
            ):
                raise ValueError("Task queue unavailable or full")
            task = self.s.put(
                "task",
                {
                    "id": uid("tsk"),
                    "org_id": actor.org_id,
                    "asset_id": version["asset_id"],
                    "owner_id": actor.user_id,
                    **body,
                    "status": "queued",
                    "created_at": self.s.clock(),
                },
            )
            self.event(task, "queued")
            self.cancel_events[task["id"]] = threading.Event()
        self.workers = [w for w in self.workers if w.is_alive()]
        worker = threading.Thread(target=self.run, args=(actor, task["id"]), daemon=True)
        self.workers.append(worker)
        worker.start()
        return task

    def guard(self, actor: Actor, identifier: str) -> None:
        task = self.get(actor, identifier)
        if self.stop.is_set() or self.cancel_events[identifier].is_set() or task["status"] in TERMINAL:
            raise PermissionError("Task cancelled or interrupted")
        version_id = task["target_id"]
        if task["kind"] == "qualify":
            version_id = self.s.get("evaluation", version_id, actor.org_id)["version_id"]
        self.p.binding(actor, self.p.version(actor, version_id))

    def factory(self, identifier: str, connection: dict[str, Any]) -> Any:
        owner = self.s.get("task", identifier, connection["org_id"])
        actor = Actor(owner["owner_id"], owner["org_id"], "")
        self.guard(actor, identifier)
        provider = self.providers(connection)
        self.providers_active[identifier] = provider
        try:
            self.guard(actor, identifier)
        except Exception:
            provider.cancel()
            provider.close()
            raise
        return provider

    def cancel(self, actor: Actor, identifier: str) -> dict[str, Any]:
        with self.s.atomic():
            task = self.get(actor, identifier)
            if task["status"] in TERMINAL:
                return task
            task.update(status="cancelled", finished_at=self.s.clock())
            self.s.put("task", task)
            self.event(task, "cancelled")
            self.cancel_events[identifier].set()
        provider = self.providers_active.get(identifier)
        if provider:
            provider.cancel()
        return task

    def run(self, actor: Actor, identifier: str) -> None:
        with self.slot:
            try:
                self.guard(actor, identifier)
                with self.s.atomic():
                    task = self.get(actor, identifier)
                    task.update(status="running", started_at=self.s.clock())
                    self.s.put("task", task)
                    self.event(task, "running")
                if task["kind"] == "qualify":
                    result = evaluation.qualify(
                        self.p,
                        actor,
                        task["target_id"],
                        self.broker,
                        guard=lambda: self.guard(actor, identifier),
                    )
                else:
                    version = self.p.version(actor, task["target_id"])
                    result = evaluation.collect(
                        self.p,
                        actor,
                        version,
                        lambda c: self.factory(identifier, c),
                        guard=lambda: self.guard(actor, identifier),
                        progress=lambda case: self.event(task, "case_completed", case=case),
                        active=lambda provider: self.providers_active.__setitem__(identifier, provider),
                    )
                self.guard(actor, identifier)
                with self.s.atomic():
                    self.guard(actor, identifier)
                    current = self.get(actor, identifier)
                    current.update(
                        status="failed" if result["status"] == "failed" else "completed",
                        result_id=result["id"],
                        finished_at=self.s.clock(),
                    )
                    self.s.put("task", current)
                    self.event(current, current["status"])
            except Exception as exc:
                with self.s.atomic():
                    task = self.get_record(actor.org_id, identifier)
                    if task["status"] not in TERMINAL:
                        task.update(status="failed", error=str(exc)[:500], finished_at=self.s.clock())
                        self.s.put("task", task)
                        self.event(task, "failed")
            finally:
                self.providers_active.pop(identifier, None)

    def get_record(self, org: str, identifier: str) -> dict[str, Any]:
        return self.s.get("task", identifier, org)

    def close(self) -> None:
        self.stop.set()
        for event in self.cancel_events.values():
            event.set()
        for provider in list(self.providers_active.values()):
            provider.cancel()
        for worker in self.workers:
            worker.join(timeout=2)
