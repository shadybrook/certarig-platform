"""Research gateway for OctoPrint's real API with VIRTUAL-only write authority.

The agent gets status and command tools. Only the trusted operator side can mint
one-use approvals. This is an integration experiment, not a safety controller.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class Refused(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def safe_job_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise Refused("invalid_job_path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or any(p in {"", ".", ".."} for p in value.split("/"))
        or any(ord(c) < 32 for c in value)
        or "\\" in value
        or "%" in value
        or path.suffix.lower() not in {".gcode", ".gco", ".g"}
    ):
        raise Refused("invalid_job_path")
    return value


@dataclass(frozen=True)
class Intent:
    machine_id: str
    action: str
    job: str
    sha256: str

    def __post_init__(self) -> None:
        if self.action not in {"start", "pause", "resume", "cancel"}:
            raise Refused("action_not_available")
        if not isinstance(self.machine_id, str) or not self.machine_id:
            raise Refused("invalid_machine_id")
        safe_job_path(self.job)
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256)
        ):
            raise Refused("invalid_sha256")

    def digest(self) -> str:
        return hashlib.sha256(canonical(asdict(self))).hexdigest()


class Audit:
    """A local hash chain detects changes if its final hash is retained separately."""

    def __init__(self, path: Path) -> None:
        if path.exists():
            raise Refused("new_audit_file_required")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.previous = "0" * 64

    def record(self, kind: str, **data: Any) -> None:
        row = {"kind": kind, "time_ns": time.time_ns(), "previous": self.previous, **data}
        digest = hashlib.sha256(canonical(row)).hexdigest()
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**row, "hash": digest}, sort_keys=True) + "\n")
        self.previous = digest


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise Refused("redirect_refused")


class OctoPrintVirtual:
    """An actual HTTP client. Writes require both a literal loopback host and VIRTUAL port."""

    def __init__(self, base_url: str, api_key: str) -> None:
        parsed = urlsplit(base_url)
        try:
            loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
        except ValueError:
            loopback = False
        if (
            parsed.scheme != "http"
            or not loopback
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise Refused("lab_requires_literal_loopback_url")
        self.base_url = base_url.rstrip("/")
        self._key = api_key
        self._opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        if method not in {"GET", "POST"} or not path.startswith("/") or path.startswith("//"):
            raise Refused("invalid_http_request")
        data = canonical(body) if body is not None else None
        request = Request(
            self.base_url + path,
            method=method,
            data=data,
            headers={"X-Api-Key": self._key, "Content-Type": "application/json"},
        )
        with self._opener.open(request, timeout=5) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise Refused("response_too_large")
            return json.loads(raw) if raw else None

    def require_virtual(self) -> None:
        connection = self.request("GET", "/api/connection")
        if connection.get("current", {}).get("port") != "VIRTUAL":
            raise Refused("physical_serial_connection_refused")

    def status(self) -> dict[str, Any]:
        self.require_virtual()
        job = self.request("GET", "/api/job")
        file = job.get("job", {}).get("file", {})
        return {
            "state": job.get("state"),
            "job": file.get("path") or file.get("name"),
            "origin": file.get("origin"),
            "progress": job.get("progress", {}),
            "observed_monotonic": time.monotonic(),
        }

    def file_hash(self, job: str) -> str:
        path = "/downloads/files/local/" + quote(safe_job_path(job), safe="/")
        request = Request(self.base_url + path, headers={"X-Api-Key": self._key})
        digest = hashlib.sha256()
        with self._opener.open(request, timeout=5) as response:
            total = 0
            while chunk := response.read(65536):
                total += len(chunk)
                if total > 16 * 1024 * 1024:
                    raise Refused("job_too_large_for_lab")
                digest.update(chunk)
        return digest.hexdigest()

    def send(self, intent: Intent) -> dict[str, Any]:
        self.require_virtual()
        if self.file_hash(intent.job) != intent.sha256:
            raise Refused("artifact_hash_mismatch")
        if intent.action == "start":
            self.request(
                "POST",
                "/api/files/local/" + quote(intent.job, safe="/"),
                {"command": "select", "print": False},
            )
        current = self.status()
        if current["origin"] != "local" or current["job"] != intent.job:
            raise Refused("selected_job_mismatch")
        if intent.action in {"pause", "resume"}:
            command = {"command": "pause", "action": intent.action}
        else:
            command = {"command": intent.action}
        self.request("POST", "/api/job", command)
        return {
            "dispatched": True,
            "action": intent.action,
            "job": intent.job,
            "physical_result": "not_measured",
            "requires_state_confirmation": True,
        }


class Gateway:
    def __init__(
        self, machine_id: str, adapter: OctoPrintVirtual, audit: Audit, clock: Any = time.monotonic
    ) -> None:
        self.machine_id, self.adapter, self.audit, self.clock = machine_id, adapter, audit, clock
        self._approvals: dict[str, tuple[str, float]] = {}
        self.uncertain = False

    def approve(self, intent: Intent, ttl: float = 60, actor: str = "operator") -> str:
        """Trusted operator entrypoint. Deliberately absent from the agent tool registry."""
        if intent.machine_id != self.machine_id:
            raise Refused("machine_mismatch")
        if not math.isfinite(ttl) or not 0 < ttl <= 300:
            raise Refused("invalid_approval_lifetime")
        approval = secrets.token_urlsafe(24)
        self._approvals[approval] = (intent.digest(), self.clock() + ttl)
        self.audit.record("operator_approved", intent=asdict(intent), actor=actor)
        return approval

    def execute(self, intent: Intent, approval_id: str | None = None) -> dict[str, Any]:
        try:
            if intent.machine_id != self.machine_id:
                raise Refused("machine_mismatch")
            if self.uncertain and intent.action in {"start", "resume"}:
                raise Refused("operator_reconciliation_required")
            status = self.adapter.status()
            age = self.clock() - status["observed_monotonic"]
            if not math.isfinite(age) or not 0 <= age < 2:
                raise Refused("stale_or_invalid_telemetry")
            allowed = {
                "start": {"Operational"},
                "pause": {"Printing"},
                "resume": {"Paused"},
                "cancel": {"Printing", "Paused", "Pausing"},
            }
            if status["state"] not in allowed[intent.action]:
                raise Refused("invalid_machine_state")
            if intent.action in {"start", "resume"}:
                approved = self._approvals.pop(approval_id or "", None)
                if approved is None or approved[0] != intent.digest() or self.clock() >= approved[1]:
                    raise Refused("approval_required_or_invalid")
            self.audit.record("dispatch_attempt", intent=asdict(intent), state=status["state"])
            try:
                result = self.adapter.send(intent)
            except Exception:
                self.uncertain = True
                self.audit.record("dispatch_uncertain", intent=asdict(intent))
                raise
            self.audit.record("controller_accepted", **result)
            return result
        except Refused as exc:
            self.audit.record("command_refused", intent=asdict(intent), reason=str(exc))
            raise
