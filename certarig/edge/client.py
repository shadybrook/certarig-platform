from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class CertaRigClient:
    def __init__(self, base_url: str, operator_key: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.operator_key = operator_key
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.operator_key:
            headers["X-CertaRig-Operator-Key"] = self.operator_key
        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
                message = detail.get("error", "request failed")
            finally:
                exc.close()
            raise RuntimeError(f"CertaRig API {exc.code}: {message}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def snapshot(self) -> dict[str, Any]:
        return self._request("GET", "/v1/snapshot")

    def create_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/v1/plans", plan)

    def approve_plan(self, plan_id: str, operator: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/plans/{plan_id}/approve", {"operator": operator})

    def execute_plan(self, plan_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/runs",
            {
                "plan_id": plan_id,
                "confirmation": "I understand this can energize configured output",
            },
        )

    def evidence(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/runs/{run_id}/evidence")

    def stop(self) -> dict[str, Any]:
        return self._request("POST", "/v1/stop", {})
