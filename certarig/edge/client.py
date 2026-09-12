"""HTTP clients for the CertaRig Edge API.

``EdgeClient`` speaks to the unified Edge node as either principal and takes care
of the contract hash on every mutating call. ``CertaRigClient`` is the legacy
Phase 2 plan-API client and is kept for the archived workflow.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class EdgeApiError(RuntimeError):
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        super().__init__(f"HTTP {status}: {payload.get('error', payload)}")
        self.status = status
        self.payload = payload

    @property
    def code(self) -> str | None:
        value = self.payload.get("code")
        return str(value) if value is not None else None


class EdgeClient:
    def __init__(
        self,
        base_url: str,
        operator_key: str | None = None,
        agent_key: str | None = None,
        principal_name: str | None = None,
        timeout: float = 10.0,
        auditor_key: str | None = None,
        session_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.operator_key = operator_key
        self.agent_key = agent_key
        self.auditor_key = auditor_key
        self.session_token = session_token
        self.principal_name = principal_name
        self.timeout = timeout
        self._contract_hash: str | None = None

    # ------------------------------------------------------------ plumbing
    def _headers(self, contract: bool) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.session_token:
            headers["X-CertaRig-Session"] = self.session_token
        if self.operator_key:
            headers["X-CertaRig-Operator-Key"] = self.operator_key
            if self.principal_name:
                headers["X-CertaRig-Operator"] = self.principal_name
        elif self.agent_key:
            headers["X-CertaRig-Agent-Key"] = self.agent_key
            if self.principal_name:
                headers["X-CertaRig-Agent"] = self.principal_name
        elif self.auditor_key:
            headers["X-CertaRig-Auditor-Key"] = self.auditor_key
            if self.principal_name:
                headers["X-CertaRig-Auditor"] = self.principal_name
        if contract and self._contract_hash:
            headers["X-CertaRig-Contract"] = self._contract_hash
        return headers

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        contract: bool = True,
        raw: bool = False,
    ) -> Any:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = self._headers(contract)
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = response.read()
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                detail = {"error": exc.reason}
            raise EdgeApiError(exc.code, detail if isinstance(detail, dict) else {"error": detail}) from exc
        if raw:
            return data
        return json.loads(data.decode("utf-8")) if data else {}

    def get(self, path: str) -> dict[str, Any]:
        result: dict[str, Any] = self.request("GET", path)
        return result

    def post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._contract_hash is None:
            self.refresh_contract()
        result: dict[str, Any] = self.request("POST", path, payload or {})
        return result

    # ------------------------------------------------------------ contract
    def refresh_contract(self) -> str:
        document = self.get("/v1/rig")
        self._contract_hash = str(document["contract_hash"])
        return self._contract_hash

    @property
    def contract_hash(self) -> str | None:
        return self._contract_hash

    # ------------------------------------------------------------ reads
    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def rig(self) -> dict[str, Any]:
        return self.get("/v1/rig")

    def signals(self) -> dict[str, Any]:
        return self.get("/v1/signals")

    def capabilities(self) -> dict[str, Any]:
        return self.get("/v1/capabilities")

    def state(self) -> dict[str, Any]:
        return self.get("/v1/live/state")

    def latest_csv(self) -> bytes:
        data: bytes = self.request("GET", "/v1/live/recordings/latest.csv", raw=True)
        return data

    # ------------------------------------------------------------ commands
    def command(self, command: str, approval_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if approval_id:
            payload["approval_id"] = approval_id
        return self.post(f"/v1/live/commands/{command}", payload)

    def start_recording(self, label: str = "bench-run") -> dict[str, Any]:
        return self.post("/v1/live/recordings/start", {"label": label})

    def stop_recording(self) -> dict[str, Any]:
        return self.post("/v1/live/recordings/stop", {})

    # ------------------------------------------------------------ approvals
    def request_approval(
        self, tool: str, args: dict[str, Any] | None = None, reason: str = ""
    ) -> dict[str, Any]:
        return self.post("/v1/approvals/request", {"tool": tool, "args": args or {}, "reason": reason})

    def approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        query = f"?status={status}" if status else ""
        rows: list[dict[str, Any]] = self.get(f"/v1/approvals{query}")["approvals"]
        return rows

    def grant(self, approval_id: str) -> dict[str, Any]:
        return self.post(f"/v1/approvals/{approval_id}/grant", {})

    def deny(self, approval_id: str) -> dict[str, Any]:
        return self.post(f"/v1/approvals/{approval_id}/deny", {})

    # ------------------------------------------------------------ evidence and ops
    def evidence(self) -> dict[str, Any]:
        return self.get("/v1/evidence")

    def evidence_run(self, run_id: str) -> dict[str, Any]:
        return self.get(f"/v1/evidence/runs/{run_id}")

    def download(self, path: str) -> bytes:
        data: bytes = self.request("GET", path, raw=True)
        return data

    def export_evidence(self, run_id: str | None = None, label: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if run_id:
            payload["run_id"] = run_id
        if label:
            payload["label"] = label
        return self.post("/v1/ops/evidence/export", payload)

    def stop_recorder(self, force: bool = False) -> dict[str, Any]:
        return self.post("/v1/ops/recorder/stop", {"force": True} if force else {})

    def shutdown(self, reason: str, approval_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"reason": reason}
        if approval_id:
            payload["approval_id"] = approval_id
        return self.post("/v1/ops/shutdown", payload)

    # ------------------------------------------------------------ procedures
    def procedures(self) -> dict[str, Any]:
        return self.get("/v1/procedures")

    def run_procedure(self, procedure_id: str, label: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"procedure_id": procedure_id}
        if label:
            payload["label"] = label
        return self.post("/v1/procedure_runs", payload)

    def procedure_run(self, run_id: str) -> dict[str, Any]:
        return self.get(f"/v1/procedure_runs/{run_id}")

    def ack(self, run_id: str, step_id: str) -> dict[str, Any]:
        return self.post(f"/v1/procedure_runs/{run_id}/ack", {"run_id": run_id, "step_id": step_id})

    def abort(self, run_id: str, reason: str = "operator abort") -> dict[str, Any]:
        return self.post(f"/v1/procedure_runs/{run_id}/abort", {"run_id": run_id, "reason": reason})


class InProcessClient(EdgeClient):
    """Same interface as :class:`EdgeClient`, dispatched against an in-memory Edge node."""

    def __init__(
        self,
        node: Any,
        operator_key: str | None = None,
        agent_key: str | None = None,
        principal_name: str | None = None,
    ) -> None:
        super().__init__("in-process", operator_key, agent_key, principal_name)
        self.node = node

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        contract: bool = True,
        raw: bool = False,
    ) -> Any:
        from .server import HttpError

        headers = self._headers(contract)
        try:
            status, body, _content_type = self.node.invoke(method, path, headers, payload)
        except HttpError as exc:
            raise EdgeApiError(exc.status, exc.payload) from exc
        if status >= 400:
            raise EdgeApiError(status, body if isinstance(body, dict) else {"error": str(body)})
        if raw:
            return body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        return body if isinstance(body, dict) else {}


class CertaRigClient:
    """Legacy Phase 2 plan API client."""

    def __init__(self, base_url: str, operator_key: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.operator_key = operator_key
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self.operator_key:
            headers["X-CertaRig-Operator-Key"] = self.operator_key
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result: dict[str, Any] = json.loads(response.read().decode("utf-8"))
                return result
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except ValueError:
                detail = {"error": exc.reason}
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def snapshot(self) -> dict[str, Any]:
        return self._request("GET", "/v1/snapshot")

    def create_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/plans", plan)

    def approve_plan(self, plan_id: str, operator: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/plans/{plan_id}/approve", {"operator": operator})

    def execute_plan(
        self, plan_id: str, confirmation: str = "I understand this can energize configured output"
    ) -> dict[str, Any]:
        return self._request("POST", "/v1/runs", {"plan_id": plan_id, "confirmation": confirmation})

    def evidence(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/runs/{run_id}/evidence")

    def stop(self) -> dict[str, Any]:
        return self._request("POST", "/v1/stop", {})
