"""Customer-session client. Shared Edge role keys are deliberately unsupported."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class PlatformClient:
    def __init__(self, base_url: str, session: str, csrf: str = ""):
        p = urlsplit(base_url)
        if (
            p.scheme != "http"
            or p.hostname != "127.0.0.1"
            or p.username
            or p.password
            or p.path not in {"", "/"}
            or p.query
            or p.fragment
        ):
            raise ValueError("Platform proof accepts loopback origin only")
        self.base, self.session, self.csrf = base_url.rstrip("/"), session, csrf

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/v1/") or "?" in path or "#" in path:
            raise ValueError("Expected a platform API path")
        data = json.dumps(body or {}).encode() if method == "POST" else None
        req = Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Cookie": "certarig_session=" + self.session,
                "X-CSRF-Token": self.csrf,
                "Origin": self.base,
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=650) as response:
            raw = response.read(32 * 1024**2 + 1)
            if len(raw) > 32 * 1024**2:
                raise ValueError("Response quota exceeded")
            return raw if response.headers.get_content_type() == "application/zip" else json.loads(raw)

    def me(self) -> dict[str, Any]:
        return dict(self.request("GET", "/v1/auth/me"))

    def create_agent(self, **definition: Any) -> dict[str, Any]:
        return dict(self.request("POST", "/v1/agents", definition))

    def revoke(self, deployment_id: str) -> dict[str, Any]:
        return dict(self.request("POST", "/v1/deployments/" + deployment_id + "/revoke"))

    def observation_tools(self, asset_id: str) -> list[dict[str, Any]]:
        return list(self.request("GET", "/v1/assets/" + asset_id + "/tools")["tools"])

    def preview_profile(self, asset_id: str) -> dict[str, Any]:
        return dict(self.request("POST", "/v1/assets/" + asset_id + "/profile-review/preview", {}))

    def accept_profile(self, asset_id: str, review_id: str) -> dict[str, Any]:
        return dict(
            self.request("POST", "/v1/assets/" + asset_id + "/profile-review", {"review_id": review_id})
        )

    def runtime_health(self) -> dict[str, Any]:
        return dict(self.request("GET", "/v1/deployments/runtime")["runtime"])
