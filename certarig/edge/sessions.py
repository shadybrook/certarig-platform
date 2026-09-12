"""Short-lived session tokens minted from the long-lived operator/agent/auditor keys."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Any

from .capabilities import Principal


@dataclass
class Session:
    token: str
    role: Principal
    name: str
    expires_at: float

    def expired(self, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) >= self.expires_at

    def public(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "role": self.role.value,
            "name": self.name,
            "expires_at": self.expires_at,
        }


class SessionRegistry:
    def __init__(self, ttl_s: int = 3600) -> None:
        self.ttl_s = ttl_s
        self._sessions: dict[str, Session] = {}

    def mint(self, role: Principal, name: str) -> Session:
        token = secrets.token_urlsafe(24)
        session = Session(token=token, role=role, name=name, expires_at=time.time() + self.ttl_s)
        digest = hashlib.sha256(token.encode()).hexdigest()
        self._sessions[digest] = session
        return session

    def resolve(self, token: str) -> Session | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        session = self._sessions.get(digest)
        if session is None or session.expired():
            return None
        return session
