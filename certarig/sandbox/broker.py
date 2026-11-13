"""Persistent experiment broker. Submitted content reaches only the container engine."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import secrets
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

from certarig.edge.atomic import write_bytes_atomic, write_json_atomic
from certarig.edge.config import canonical_hash

from .contracts import (
    LIMITS,
    TERMINAL,
    binding,
    blockers,
    digest,
    encoded,
    identifier,
    safe_name,
    snapshot,
    verify_rehearsal,
)


class Broker:
    def __init__(self, root: Path, engine: Any, clock: Any = time.time) -> None:
        self.root, self.engine, self.clock = root, engine, clock
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
            raise ValueError("broker root must be a private directory owned by this user")
        self.lock = threading.RLock()
        self.slot = threading.Lock()
        self.events: dict[str, threading.Event] = {}
        self.deadlines: dict[str, float] = {}
        self.stopping = threading.Event()
        key = root / ".receipt-key"
        if not key.exists():
            fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
        self.key = key.read_bytes()
        if len(self.key) != 32:
            raise ValueError("corrupt receipt signing key")
        for path in (root / "agent-evaluations").glob("*.json"):
            value = json.loads(path.read_text())
            if value["status"] == "running":
                self.engine.cleanup("crsb-" + value["job_id"])
                value["status"] = "interrupted"
                write_json_atomic(path, value)
        for p in root.glob("sbx_*/workspace.json"):
            workspace = json.loads(p.read_text())
            for job in workspace["jobs"]:
                if job["status"] not in TERMINAL:
                    job.update(status="interrupted", error="broker restarted; no job resumed")
                    self.engine.cleanup("crsb-" + job["job_id"])
            if workspace["status"] == "active":
                workspace["status"] = "expired"
                self._event(workspace, "expired_after_restart")
            self._save(workspace)
        self.sweeper = threading.Thread(target=self._sweep, daemon=True)
        self.sweeper.start()

    def _admit(self, extra: int = 0) -> None:
        total = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
        if total + extra > 1024**3:
            raise ValueError("sandbox store quota exceeded; export/archive existing evidence before new work")

    def _event(self, w: dict[str, Any], event: str) -> None:
        w["events"].append({"at": self.clock(), "event": event})

    def _save(self, w: dict[str, Any]) -> None:
        write_json_atomic(self.root / w["sandbox_id"] / "workspace.json", w)

    def _read(self, sid: str, owner: str, role: str, mutate: bool = False) -> dict[str, Any]:
        identifier(sid, "sbx")
        path = self.root / sid / "workspace.json"
        if not path.is_file():
            raise KeyError("workspace not found")
        w = json.loads(path.read_text())
        if role not in {"operator", "auditor"} and w["owner"] != owner:
            raise PermissionError("workspace belongs to another principal")
        if mutate and (role == "auditor" or w["status"] != "active"):
            raise PermissionError("workspace is read-only or closed")
        if w["status"] == "active" and (
            self.clock() >= w["expires_at"] or time.monotonic() >= self.deadlines.get(sid, float("inf"))
        ):
            w["status"] = "expired"
            self._event(w, "lease_expired")
            self._cancel(w)
            self._save(w)
            if mutate:
                raise ValueError("workspace lease expired")
        return w

    def _cancel(self, w: dict[str, Any]) -> None:
        for job in w["jobs"]:
            event = self.events.get(job["job_id"])
            if event:
                event.set()

    def _sweep(self) -> None:
        while not self.stopping.wait(0.25):
            with self.lock:
                for path in self.root.glob("sbx_*/workspace.json"):
                    try:
                        w = json.loads(path.read_text())
                        self._read(w["sandbox_id"], w["owner"], "operator")
                    except (OSError, ValueError):
                        # Corruption must not leave an uncontrolled worker running.
                        for event in self.events.values():
                            event.set()

    def close(self) -> None:
        self.stopping.set()
        for event in list(self.events.values()):
            event.set()
        self.sweeper.join(timeout=2)

    def _mac(self, value: dict[str, Any]) -> str:
        return hmac.new(self.key, encoded(value), hashlib.sha256).hexdigest()

    def _receipt(self, w: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        if getattr(self.engine, "current_image", self.engine.image) != self.engine.image:
            raise ValueError("runner image changed; requalification required")
        if job["revision"] != w["revision"]:
            raise ValueError("Rehearsal belongs to a previous workspace revision")
        receipt = job.get("receipt")
        if not isinstance(receipt, dict):
            raise ValueError("No trusted rehearsal receipt")
        body = {k: v for k, v in receipt.items() if k != "mac"}
        if (
            not hmac.compare_digest(receipt["mac"], self._mac(body))
            or body["binding"] != binding(w["snapshot"], self.engine.image, w["seed"])
            or body.get("workspace_revision") != w["revision"]
            or body.get("job_id") != job["job_id"]
        ):
            raise ValueError("Rehearsal binding is stale or invalid")
        if (
            not body["verification"]["passed"]
            or job["status"] != "completed"
            or not 0 <= self.clock() - body["at"] <= 86400
        ):
            raise ValueError("Rehearsal did not pass or expired")
        # Required raw evidence is rechecked before a proposal can be reviewed/applied.
        files = self._files(w, job)
        if verify_rehearsal({**w["snapshot"], "seed": w["seed"]}, files) != body["verification"]:
            raise ValueError("Rehearsal raw evidence changed")
        return receipt

    def _files(self, w: dict[str, Any], job: dict[str, Any]) -> dict[str, bytes]:
        result = {}
        for name, sha in job["artifacts"].items():
            if not safe_name(name) or "/" in name:
                raise ValueError("unsafe saved artifact")
            p = self.root / w["sandbox_id"] / job["job_id"] / "artifacts" / name
            if p.is_symlink() or not p.is_file():
                raise ValueError("missing/unsafe artifact")
            data = p.read_bytes()
            if digest(data) != sha:
                raise ValueError("corrupt artifact")
            result[name] = data
        return result

    def call(self, method: str, owner: str, role: str, body: dict[str, Any]) -> dict[str, Any]:
        if role not in {"operator", "agent", "auditor"}:
            raise PermissionError("authentication required")
        if method in {"agent_evaluation", "agent_evaluation_validate"}:
            if role == "auditor" and method == "agent_evaluation":
                raise PermissionError("auditor is read-only")
            from .agent_evaluation import call
            return call(self, method, owner, body)
        with self.lock:
            if method == "preflight":
                return self.engine.preflight()
            if method == "list":
                values = [
                    self._read(p.parent.name, owner, role)
                    for p in self.root.glob("sbx_*/workspace.json")
                    if role in {"operator", "auditor"} or json.loads(p.read_text())["owner"] == owner
                ]
                return {"workspaces": values}
            if method == "create":
                if role == "auditor":
                    raise PermissionError("auditor is read-only")
                recording = base64.b64decode(body.get("recording", ""), validate=True)
                provenance = dict(body.get("provenance") or {})
                if recording:
                    provenance["recording_sha256"] = digest(recording)
                    provenance["recording_kind"] = "copied_samples_not_physical_qualification"
                value = snapshot(body["document"], body["procedure"], body["base_config_hash"], provenance)
                if len(recording) + len(encoded(value)) + 256000 > LIMITS["input_bytes"]:
                    raise ValueError("recording exceeds immutable input quota")
                if len(list(self.root.glob("sbx_*/workspace.json"))) >= 32:
                    raise ValueError("retained workspace quota exceeded")
                active = [
                    p
                    for p in self.root.glob("sbx_*/workspace.json")
                    if json.loads(p.read_text())["status"] == "active"
                ]
                if len(active) >= 3:
                    raise ValueError("close an active workspace before creating another")
                self._admit(len(encoded(value)) * 2 + len(recording) + 4096)
                sid = "sbx_" + secrets.token_hex(8)
                seed = body.get("seed", 11)
                if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**31 - 1:
                    raise ValueError("seed must be a nonnegative 31-bit integer")
                w = {
                    "sandbox_id": sid,
                    "owner": owner,
                    "status": "active",
                    "revision": 0,
                    "seed": seed,
                    "created_at": self.clock(),
                    "expires_at": self.clock() + LIMITS["lease_s"],
                    "snapshot": value,
                    "snapshot_hash": canonical_hash(value),
                    "revision_hashes": {"0": canonical_hash(value)},
                    "jobs": [],
                    "proposals": [],
                    "events": [],
                    "authority": "none",
                    "agent_kind": "deterministic_fixture_or_submitted_code",
                }
                if recording:
                    w["recording"] = {"sha256": digest(recording), "bytes": len(recording)}
                    write_bytes_atomic(self.root / sid / "recording.csv", recording)
                self.deadlines[sid] = time.monotonic() + LIMITS["lease_s"]
                self._event(w, "created")
                write_json_atomic(self.root / sid / "snapshot-0.json", value)
                self._save(w)
                return w
            sid = str(body["sandbox_id"])
            mutating = method in {"revise", "run", "propose"}
            w = self._read(sid, owner, role, mutating)
            if method == "read":
                return w
            if method == "close":
                if role == "auditor":
                    raise PermissionError("auditor is read-only")
                w["status"] = "closed"
                self._cancel(w)
                self._event(w, "closed")
                self._save(w)
                return w
            if method == "revise":
                if w["revision"] >= 50:
                    raise ValueError("workspace revision quota exceeded")
                self._admit(len(encoded(body)) * 2 + 4096)
                if body["expected_revision"] != w["revision"]:
                    raise ValueError("stale workspace revision")
                value = snapshot(
                    body["document"],
                    body.get("procedure", w["snapshot"]["procedure"]),
                    w["snapshot"]["base_config_hash"],
                    w["snapshot"]["provenance"],
                )
                w.update(snapshot=value, snapshot_hash=canonical_hash(value), revision=w["revision"] + 1)
                w["revision_hashes"][str(w["revision"])] = canonical_hash(value)
                write_json_atomic(self.root / sid / f"snapshot-{w['revision']}.json", value)
                self._event(w, "snapshot_revised_previous_receipts_invalidated")
                self._save(w)
                return w
            if method == "run":
                if len(w["jobs"]) >= LIMITS["jobs"]:
                    raise ValueError("workspace job quota exceeded")
                self._admit(LIMITS["output_bytes"] + 1024**2)
                kind = body.get("kind")
                if kind not in {"python", "spice", "rehearsal"}:
                    raise ValueError("unsupported job kind")
                if kind == "rehearsal" and blockers(w["snapshot"]):
                    raise ValueError("; ".join(blockers(w["snapshot"])))
                if not self.engine.preflight()["ready"]:
                    raise ValueError("runtime preflight failed; inspect preflight blockers; no host fallback")
                if (
                    sum(p.stat().st_size for p in (self.root / sid).rglob("*") if p.is_file())
                    >= LIMITS["workspace_bytes"]
                ):
                    raise ValueError("workspace artifact quota exceeded")
                source = body.get("source", "")
                if not isinstance(source, str) or len(source.encode()) > 256_000:
                    raise ValueError("source exceeds 256000-byte limit")
                if kind == "rehearsal" and source.strip():
                    raise ValueError("trusted rehearsal does not accept submitted code")
                if kind != "rehearsal" and not source.strip():
                    raise ValueError("source is required")
                jid = "job_" + secrets.token_hex(8)
                filename = "main.py" if kind == "python" else "circuit.cir"
                inputs = {"snapshot.json": encoded({**w["snapshot"], "seed": w["seed"]})}
                if kind != "rehearsal":
                    inputs[filename] = source.encode()
                if w.get("recording"):
                    data = (self.root / sid / "recording.csv").read_bytes()
                    if digest(data) != w["recording"]["sha256"]:
                        raise ValueError("recorded input changed")
                    inputs["recording.csv"] = data
                retained = sum(p.stat().st_size for p in (self.root / sid).rglob("*") if p.is_file())
                if (
                    retained + sum(map(len, inputs.values())) + LIMITS["output_bytes"]
                    > LIMITS["workspace_bytes"]
                ):
                    raise ValueError("workspace cannot reserve bounded job inputs and outputs")
                self._admit(sum(map(len, inputs.values())) + LIMITS["output_bytes"] + 1024**2)
                for name, data in inputs.items():
                    write_bytes_atomic(self.root / sid / jid / "inputs" / name, data)
                job = {
                    "job_id": jid,
                    "kind": kind,
                    "revision": w["revision"],
                    "status": "queued",
                    "source": source,
                    "snapshot_hash": w["snapshot_hash"],
                    "input_hashes": {k: digest(v) for k, v in inputs.items()},
                    "artifacts": {},
                    "created_at": self.clock(),
                    "qualification": False,
                    "runner_image": self.engine.image,
                }
                w["jobs"].append(job)
                self._save(w)
                event = self.events[jid] = threading.Event()
                threading.Thread(target=self._run, args=(sid, jid, inputs, event), daemon=True).start()
                return job
            if method == "propose":
                job = next(j for j in w["jobs"] if j["job_id"] == body["job_id"])
                receipt = self._receipt(w, job)
                kind = body.get("kind", "configuration")
                if kind not in {"configuration", "procedure"}:
                    raise ValueError("only structured configuration/procedure proposals can be submitted")
                existing = next(
                    (
                        p
                        for p in w["proposals"]
                        if p["job_id"] == job["job_id"]
                        and p["kind"] == kind
                        and p["revision"] == w["revision"]
                    ),
                    None,
                )
                if existing is not None:
                    return existing
                self._admit(len(encoded(w["snapshot"])) * 2 + 4096)
                proposal = {
                    "proposal_id": "prp_" + secrets.token_hex(8),
                    "kind": kind,
                    "job_id": job["job_id"],
                    "revision": w["revision"],
                    "base_config_hash": w["snapshot"]["base_config_hash"],
                    "snapshot_hash": w["snapshot_hash"],
                    "receipt": receipt,
                    "document": w["snapshot"]["document"],
                    "procedure": w["snapshot"]["procedure"],
                    "provenance": w["snapshot"]["provenance"],
                    "status": "needs_operator_review",
                }
                w["proposals"].append(proposal)
                self._event(w, "proposal_submitted_no_configuration_applied")
                self._save(w)
                return proposal
            if method == "validate_proposal":
                if role != "operator":
                    raise PermissionError("only an operator may review promotion")
                proposal = next(p for p in w["proposals"] if p["proposal_id"] == body["proposal_id"])
                if (
                    proposal["snapshot_hash"] != w["snapshot_hash"]
                    or proposal["base_config_hash"] != body["base_config_hash"]
                ):
                    raise ValueError("stale sandbox proposal")
                job = next(j for j in w["jobs"] if j["job_id"] == proposal["job_id"])
                self._receipt(w, job)
                return proposal
            if method == "artifact":
                job = next(j for j in w["jobs"] if j["job_id"] == body["job_id"])
                name = str(body["name"])
                artifact_data = self._files(w, job).get(name)
                if artifact_data is None:
                    raise KeyError("artifact not found")
                return {"name": name, "data": base64.b64encode(artifact_data).decode()}
            if method == "export":
                return {"data": base64.b64encode(self.export(w)).decode()}
            raise ValueError("unknown broker operation")

    def _run(self, sid: str, jid: str, inputs: dict[str, bytes], event: threading.Event) -> None:
        try:
            while not self.slot.acquire(timeout=0.1):
                if event.is_set():
                    raise RuntimeError("cancelled while queued")
            try:
                with self.lock:
                    w = self._read(sid, "", "operator", True)
                    job = next(j for j in w["jobs"] if j["job_id"] == jid)
                    seconds = min(
                        LIMITS["rehearsal_s"] if job["kind"] == "rehearsal" else LIMITS["analysis_s"],
                        int(
                            min(
                                w["expires_at"] - self.clock(),
                                self.deadlines.get(sid, time.monotonic()) - time.monotonic(),
                            )
                        ),
                    )
                    if seconds < 1 or event.is_set():
                        raise RuntimeError("workspace cancelled or expired")
                    job["status"] = "running"
                    self._save(w)
                outcome = self.engine.run(jid, job["kind"], inputs, seconds, event)
                with self.lock:
                    w = self._read(sid, "", "operator")
                    job = next(j for j in w["jobs"] if j["job_id"] == jid)
                    files = outcome["files"]
                    retained = sum(p.stat().st_size for p in (self.root / sid).rglob("*") if p.is_file())
                    if sum(map(len, files.values())) + retained > LIMITS["workspace_bytes"]:
                        raise ValueError("workspace artifact quota exceeded")
                    # Queued jobs cannot reserve future space across other workspaces.
                    self._admit(sum(map(len, files.values())) + 4096)
                    for name, data in files.items():
                        if not safe_name(name) or "/" in name:
                            raise ValueError("unsafe artifact name")
                        write_bytes_atomic(self.root / sid / jid / "artifacts" / name, data)
                    job.update(
                        status="cancelled"
                        if event.is_set() or w["status"] != "active"
                        else outcome["status"],
                        resource=outcome["resource"],
                        artifacts={k: digest(v) for k, v in files.items()},
                    )
                    if job["kind"] == "rehearsal" and job["status"] == "completed":
                        original = json.loads(inputs["snapshot.json"])
                        verification = verify_rehearsal(original, files)
                        receipt = {
                            "binding": binding(
                                {k: v for k, v in original.items() if k != "seed"},
                                self.engine.image,
                                original["seed"],
                            ),
                            "verification": verification,
                            "at": self.clock(),
                            "job_id": jid,
                            "workspace_revision": job["revision"],
                        }
                        job["receipt"] = {**receipt, "mac": self._mac(receipt)}
                        job["qualification"] = verification["passed"]
                    job["finished_at"] = self.clock()
                    self._event(w, f"job_{jid}_{job['status']}")
                    self._save(w)
            finally:
                self.slot.release()
        except Exception as exc:
            with self.lock:
                path = self.root / sid / "workspace.json"
                w = json.loads(path.read_text())
                job = next(j for j in w["jobs"] if j["job_id"] == jid)
                job.update(
                    status="cancelled" if event.is_set() else "failed",
                    error=f"{type(exc).__name__}: {exc}",
                    finished_at=self.clock(),
                )
                self._save(w)
        finally:
            with self.lock:
                self.events.pop(jid, None)

    def export(self, w: dict[str, Any]) -> bytes:
        if any(j["status"] not in TERMINAL for j in w["jobs"]):
            raise ValueError("finish or cancel jobs before export")
        files = {"workspace.json": encoded(w)}
        if w.get("recording"):
            data = (self.root / w["sandbox_id"] / "recording.csv").read_bytes()
            if digest(data) != w["recording"]["sha256"]:
                raise ValueError("recorded input changed")
            files["recording.csv"] = data
        for revision in range(w["revision"] + 1):
            p = self.root / w["sandbox_id"] / f"snapshot-{revision}.json"
            data = p.read_bytes()
            if canonical_hash(json.loads(data)) != w["revision_hashes"][str(revision)]:
                raise ValueError("snapshot revision changed")
            files[p.name] = data
        for job in w["jobs"]:
            for name, sha in job["input_hashes"].items():
                data = (self.root / w["sandbox_id"] / job["job_id"] / "inputs" / name).read_bytes()
                if digest(data) != sha:
                    raise ValueError("job input changed")
                files[job["job_id"] + "/inputs/" + name] = data
            for name, data in self._files(w, job).items():
                files[job["job_id"] + "/artifacts/" + name] = data
        files["manifest.json"] = encoded(
            {
                "kind": "certarig_sandbox_bundle",
                "schema_version": 1,
                "files": {k: digest(v) for k, v in files.items()},
                "authority": "none",
                "worker_image": self.engine.image,
            }
        )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
        return buffer.getvalue()
