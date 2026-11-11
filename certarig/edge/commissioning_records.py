"""Reviewed, configuration-bound readiness; software checks never accept physical wiring."""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from .atomic import write_json_atomic
from .config import canonical_hash
from .models import CONCEPT_BY_UNIT
from .runtime import validate_procedure
from .schemas import validate_against_schema
from .server import EdgeNode, HttpError, RequestContext


class CommissioningService:
    def __init__(self, node: EdgeNode) -> None:
        self.node = node
        self.root = node.runtime.evidence_dir / "commissioning"
        self._lock = threading.RLock()
        self.session_id = uuid.uuid4().hex

    def identity(self) -> str:
        adapter = self.node.runtime.hardware
        return f"{type(adapter).__module__}.{type(adapter).__name__}"

    def current(self) -> dict[str, Any] | None:
        path = self.root / f"{self.node.config.config_hash}.json"
        with self._lock:
            if not path.is_file():
                return None
            record = json.loads(path.read_text())
            validate_against_schema(record, "commissioning.schema.json")
            return record

    def readiness(self, procedure_id: str | None = None, *, reviewed: bool = True) -> dict[str, Any]:
        node = self.node
        record = self.current()
        blockers: list[str] = []
        config = node.config
        simulated = config.hardware.mode in {"simulator", "mock"}
        state = node.runtime.state()
        if node.config_path and canonical_hash(json.loads(node.config_path.read_text())) != config.config_hash:
            blockers.append("Configuration on disk differs from the running configuration")
        if state.get("config_hash") != config.config_hash:
            blockers.append("Awaiting samples for the current configuration")
        if state.get("status") != "ok" or not state.get("guardrail", {}).get("process_healthy"):
            blockers.append("Required observations are missing, invalid or outside safe limits")
        if state.get("guardrail", {}).get("estop_active", True):
            blockers.append("E-stop is active or unknown")
        if node.runtime.sample_age_s() > max(1.0, config.sample_interval_ms / 1000 * 3):
            blockers.append("Acquisition is stale")
        samples = {s["channel_id"]: s for s in state.get("samples", [])}
        for channel in config.channels:
            if not channel.required:
                continue
            sample = samples.get(channel.channel_id)
            if sample is None or sample.get("unit") != channel.unit:
                blockers.append(f"Missing or incompatible observation: {channel.channel_id}")
            # Procedures use engineering-unit numbers. Unit conversion is deliberately explicit.
            expected = {"pressure": "bar", "flow": "l/min", "temperature": "degc"}.get(channel.concept)
            inferred = CONCEPT_BY_UNIT.get(channel.unit.lower())
            if (inferred and inferred != channel.concept) or (expected and channel.unit.lower() != expected):
                blockers.append(f"Unsupported procedure unit for {channel.channel_id}: {channel.unit}")
        library = node.extensions["procedures"].library
        ids = [procedure_id] if procedure_id else list(record["procedures"]) if record else [p["id"] for p in library.list()]
        if not ids:
            blockers.append("No supported procedure is available")
        for pid in ids:
            procedure = library.get(pid)
            if procedure is None or validate_procedure(procedure.raw, config):
                blockers.append(f"Unsupported procedure: {pid}")
            elif reviewed and (not record or record.get("procedures", {}).get(pid) != procedure.procedure_hash):
                blockers.append(f"Procedure requires commissioning review: {pid}")
        if reviewed and (not record or record.get("adapter_identity") != self.identity()):
            blockers.append("Current configuration and adapter require human review")
        physical_stage = (record or {}).get("stage")
        if not simulated:
            if not record or physical_stage not in {"observation", "trial", "accepted"}:
                blockers.append("Physical commissioning has not been accepted")
            elif reviewed:
                if record.get("wiring_revision") != config.wiring_revision:
                    blockers.append("Physical wiring revision changed")
                if physical_stage == "trial" and (record.get("session_id") != self.session_id or record.get("expires_at_unix", 0) < time.time()):
                    blockers.append("Attended trial acceptance expired")
                from .physical_review import inspect_evidence

                try:
                    inspect_evidence(node.runtime.evidence_dir, record["checks"], config.config_hash, str(config.wiring_revision), physical_stage)
                except (ValueError, KeyError, OSError):
                    blockers.append("Physical qualification evidence is missing or changed")
                if physical_stage == "observation" and any((library.get(pid) and library.get(pid).requires_output) for pid in ids):
                    blockers.append("Observation acceptance cannot authorize output")
        if procedure_id:
            procedure = library.get(procedure_id)
            if procedure and procedure.requires_output and (config.hardware.observe_only or not node.runtime.allow_output):
                blockers.append("Output operation is unavailable in observe-only mode")
        return {
            "required": config.commissioning_required,
            "ready": not blockers,
            "status": ("simulation_ready" if simulated else f"{physical_stage}_ready") if not blockers else "review_required" if simulated else "control_verification_required",
            "evidence_kind": "simulated" if simulated else "software_observation_only",
            "physical_commissioned": bool(record and record.get("physical_commissioned") and not blockers),
            "config_hash": config.config_hash,
            "adapter_identity": self.identity(),
            "procedure_id": procedure_id,
            "blockers": list(dict.fromkeys(blockers)),
            "record": record,
        }

    def get(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        pid = (ctx.query.get("procedure_id") or [""])[0] or None
        return 200, self.readiness(pid)

    def review(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        self.node._require_operator(ctx)
        if self.node.config.hardware.mode not in {"simulator", "mock"}:
            raise HttpError(409, "Software review cannot accept physical equipment; use the staged physical review")
        if ctx.body.get("expected_config_hash") != self.node.config.config_hash:
            raise HttpError(409, {"error": "Re-read the current configuration before review", "code": "stale_contract"})
        ids = ctx.body.get("procedure_ids")
        if not isinstance(ids, list) or not ids or not all(isinstance(pid, str) for pid in ids):
            raise HttpError(400, "procedure_ids must be a nonempty list of procedure names")
        procedures: dict[str, str] = {}
        for pid in ids:
            if not isinstance(pid, str):
                raise HttpError(400, "procedure name must be a string")
            readiness = self.readiness(pid, reviewed=False)
            if not readiness["ready"]:
                raise HttpError(409, {"error": "Commissioning checks failed", "code": "commissioning_required", **readiness})
            procedures[pid] = self.node.extensions["procedures"].library.get(pid).procedure_hash
        record = {
            "schema_version": 1,
            "rig_id": self.node.config.rig_id,
            "config_hash": self.node.config.config_hash,
            "adapter_identity": self.identity(),
            "reviewed_by": ctx.principal_name,
            "reviewed_at": datetime.now(UTC).isoformat(),
            "evidence_kind": "simulated",
            "physical_commissioned": False,
            "procedures": procedures,
        }
        validate_against_schema(record, "commissioning.schema.json")
        with self._lock:
            write_json_atomic(self.root / f"{self.node.config.config_hash}.json", record)
        return 201, self.readiness(str(ids[0]))

    def require(self, procedure_id: str | None = None) -> None:
        if not self.node.config.commissioning_required:
            return
        readiness = self.readiness(procedure_id)
        if not readiness["ready"]:
            self.node.runtime.command("safe")
            raise HttpError(409, {"error": "Rig is not ready for this operation", "code": "commissioning_required", **readiness})


def install_commissioning(node: EdgeNode) -> CommissioningService:
    service = CommissioningService(node)
    node.extensions["commissioning"] = service
    node.add_route("GET", "/v1/commissioning", service.get, "read_rig")
    node.add_route("POST", "/v1/commissioning/review", service.review)
    from .physical_review import review_physical

    node.add_route("POST", "/v1/commissioning/physical", lambda ctx: review_physical(service, ctx))
    return service
