"""Trusted runtime heartbeat. Reading status never restores expired execution authority."""

from __future__ import annotations

from typing import Any

HEARTBEAT_S = 1.0
TIMEOUT_S = 5.0


def status(store: Any) -> dict[str, Any]:
    try:
        record = store.get("runtime", "local", "")
    except KeyError:
        return {"state": "offline", "runtime_id": None, "heartbeat_at": None, "timeout_s": TIMEOUT_S}
    age = store.clock() - record["heartbeat_at"]
    return {
        **record,
        "state": record["state"] if record["state"] != "online" or 0 <= age <= TIMEOUT_S else "unresponsive",
        "timeout_s": TIMEOUT_S,
    }


def interrupt(platform: Any, d: dict[str, Any], reason: str) -> dict[str, Any]:
    d.update(status="interrupted", reason=reason, provider_status="interrupted", activity="stopped")
    platform.store.put("deployment", d)
    platform.store.audit(d["org_id"], "interrupted", "runtime_health", deployment_id=d["id"], reason=reason)
    return d


def claim(platform: Any, runtime_id: str) -> None:
    s = platform.store
    with s.atomic():
        previous = status(s)
        for row in s.rows("SELECT body FROM documents WHERE kind='deployment'"):
            import json

            d = json.loads(row[0])
            if d["status"] == "running" or (previous["runtime_id"] is not None and d["status"] == "approved"):
                interrupt(platform, d, "Runtime restarted; new independent review required")
        s.put(
            "runtime",
            {
                "id": "local",
                "org_id": "",
                "runtime_id": runtime_id,
                "state": "online",
                "heartbeat_at": s.clock(),
            },
        )


def pulse(platform: Any, runtime_id: str) -> None:
    s = platform.store
    with s.atomic():
        record = status(s)
        if record["runtime_id"] != runtime_id or record["state"] != "online":
            raise PermissionError("Runtime heartbeat expired or superseded; restart and obtain fresh review")
        record.pop("timeout_s", None)
        record["heartbeat_at"] = s.clock()
        s.put("runtime", record)


def reconcile(platform: Any, d: dict[str, Any]) -> dict[str, Any]:
    s = platform.store
    with s.atomic():
        current = s.get("deployment", d["id"], d["org_id"])
        if current["status"] != "running":
            return current
        runtime = status(s)
        if runtime["state"] != "online" or runtime["runtime_id"] != current["runtime_id"]:
            return interrupt(
                platform,
                current,
                "Observation runtime is offline or its heartbeat expired; new review required",
            )
        if s.clock() >= current["expires_at"]:
            platform.pause(current, "Observation lease expired; new review required")
        return current


def stop(platform: Any, runtime_id: str) -> None:
    s = platform.store
    with s.atomic():
        record = status(s)
        if record["runtime_id"] != runtime_id:
            return
        record.pop("timeout_s", None)
        record.update(state="offline", heartbeat_at=s.clock())
        s.put("runtime", record)
        for row in s.rows("SELECT body FROM documents WHERE kind='deployment'"):
            import json

            d = json.loads(row[0])
            if d["status"] == "running" and d["runtime_id"] == runtime_id:
                interrupt(platform, d, "Observation runtime stopped; new review required")
