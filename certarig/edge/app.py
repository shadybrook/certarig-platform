from __future__ import annotations

import json
import secrets
import threading
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .evidence import EvidenceStore
from .executor import DeterministicExecutor
from .hardware.base import HardwareAdapter
from .models import CommissioningPlan, PlanState, PlanStep, RigConfig
from .safety import validate_plan


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class CertaRigApplication:
    def __init__(
        self,
        config: RigConfig,
        hardware: HardwareAdapter,
        store: EvidenceStore,
        operator_key: str,
        actuation_enabled: bool,
    ) -> None:
        if len(operator_key) < 12:
            raise ValueError("operator key must contain at least 12 characters")
        self.config = config
        self.hardware = hardware
        self.store = store
        self.operator_key = operator_key
        self.plans: dict[str, CommissioningPlan] = {}
        self._lock = threading.RLock()
        self.executor = DeterministicExecutor(
            hardware=hardware,
            store=store,
            sample_interval_ms=config.sample_interval_ms,
            pressure_abort_bar=config.pressure_abort_bar,
            actuation_enabled=actuation_enabled or config.hardware.mode == "mock",
        )
        self.hardware.force_safe_state()

    def authorized(self, candidate: str | None) -> bool:
        return candidate is not None and secrets.compare_digest(candidate, self.operator_key)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "rig_id": self.config.rig_id,
            "config_hash": self.config.config_hash,
            "hardware_mode": self.config.hardware.mode,
            "actuation_enabled": self.executor.actuation_enabled,
            "pressure_abort_bar": self.config.pressure_abort_bar,
            "output_safe": self.hardware.output_is_safe(),
        }

    def create_plan(self, payload: dict[str, Any]) -> CommissioningPlan:
        steps_raw = payload.get("steps")
        if not isinstance(steps_raw, list):
            raise ValueError("steps must be a list")
        steps = [
            PlanStep(
                action=str(step.get("action", "")),
                duration_ms=int(step.get("duration_ms", 0)),
                valve_open=step.get("valve_open"),
                expected_pressure_min=(
                    float(step["expected_pressure_min"])
                    if step.get("expected_pressure_min") is not None
                    else None
                ),
                expected_pressure_max=(
                    float(step["expected_pressure_max"])
                    if step.get("expected_pressure_max") is not None
                    else None
                ),
            )
            for step in steps_raw
            if isinstance(step, dict)
        ]
        plan = CommissioningPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:12]}",
            rig_id=str(payload.get("rig_id", "")),
            config_hash=str(payload.get("config_hash", "")),
            purpose=str(payload.get("purpose", "")).strip(),
            pressure_limit_bar=float(payload.get("pressure_limit_bar", 0)),
            steps=steps,
            created_at=utc_now(),
        )
        snapshot = self.hardware.snapshot()
        validate_plan(self.config, snapshot, plan)
        with self._lock:
            self.plans[plan.plan_id] = plan
            self.store.save_plan(plan)
        return plan

    def approve_plan(self, plan_id: str, operator: str) -> CommissioningPlan:
        with self._lock:
            plan = self.plans.get(plan_id)
            if plan is None:
                raise KeyError(plan_id)
            if plan.state != PlanState.VALIDATED:
                raise ValueError("only a validated plan can be approved")
            if plan.config_hash != self.config.config_hash:
                raise ValueError("plan configuration hash is stale")
            plan.state = PlanState.APPROVED
            plan.approved_at = utc_now()
            plan.approved_by = operator.strip() or "operator"
            self.store.save_plan(plan)
            return plan

    def execute_plan(self, plan_id: str, confirmation: str) -> dict[str, Any]:
        if confirmation != "I understand this can energize configured output":
            raise ValueError("exact execution confirmation is required")
        with self._lock:
            plan = self.plans.get(plan_id)
        if plan is None:
            raise KeyError(plan_id)
        result = self.executor.run(plan)
        return result.to_dict()

    def close(self) -> None:
        self.executor.request_stop()
        self.hardware.close()
        self.store.close()


def make_handler(app: CertaRigApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CertaRigEdge/0.3"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("request body is too large")
            if length == 0:
                return {}
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def _require_operator(self) -> bool:
            if not app.authorized(self.headers.get("X-CertaRig-Operator-Key")):
                self._send(401, {"error": "operator authentication required"})
                return False
            return True

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, app.health())
                return
            if path == "/v1/snapshot":
                self._send(200, app.hardware.snapshot().to_dict())
                return
            if path.startswith("/v1/plans/"):
                plan_id = path.removeprefix("/v1/plans/")
                plan = app.plans.get(plan_id)
                if plan is None:
                    self._send(404, {"error": "plan not found"})
                else:
                    self._send(200, plan.to_dict())
                return
            if path.startswith("/v1/runs/") and path.endswith("/evidence"):
                run_id = path.removeprefix("/v1/runs/").removesuffix("/evidence").strip("/")
                bundle = app.store.evidence_bundle(run_id)
                if bundle is None:
                    self._send(404, {"error": "run not found"})
                else:
                    self._send(200, bundle)
                return
            self._send(404, {"error": "route not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if path == "/v1/plans":
                    plan = app.create_plan(payload)
                    status = 201 if plan.state == PlanState.VALIDATED else 422
                    self._send(status, plan.to_dict())
                    return
                if path.startswith("/v1/plans/") and path.endswith("/approve"):
                    if not self._require_operator():
                        return
                    plan_id = path.removeprefix("/v1/plans/").removesuffix("/approve").strip("/")
                    plan = app.approve_plan(plan_id, str(payload.get("operator", "")))
                    self._send(200, plan.to_dict())
                    return
                if path == "/v1/runs":
                    if not self._require_operator():
                        return
                    result = app.execute_plan(
                        str(payload.get("plan_id", "")),
                        str(payload.get("confirmation", "")),
                    )
                    self._send(201, result)
                    return
                if path == "/v1/stop":
                    if not self._require_operator():
                        return
                    app.executor.request_stop()
                    self._send(
                        200, {"status": "stop_requested", "output_safe": app.hardware.output_is_safe()}
                    )
                    return
                self._send(404, {"error": "route not found"})
            except KeyError:
                self._send(404, {"error": "resource not found"})
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})
            except RuntimeError as exc:
                self._send(409, {"error": str(exc)})

    return Handler


def make_server(app: CertaRigApplication, host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(app))
