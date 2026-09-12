"""Single-use human approvals for tools with the ``human_approval`` policy.

Flow:

1. The agent calls ``request(tool, args, reason)`` which creates a *pending* approval.
2. A human (operator principal) sees it in Studio and calls ``grant`` or ``deny``.
3. The agent retries the tool call with ``approval_id``; ``consume`` verifies that the
   approval is granted, unexpired, unused, and bound to the same tool and arguments.

Approvals are bound to the contract hash so a re-configured rig invalidates them.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .config import canonical_hash


class ApprovalError(RuntimeError):
    pass


@dataclass
class Approval:
    approval_id: str
    tool: str
    args_hash: str
    args: dict[str, Any]
    reason: str
    contract_hash: str
    requested_by: str
    requested_at: float
    status: str = "pending"  # pending | granted | denied | consumed | expired
    decided_by: str | None = None
    decided_at: float | None = None
    expires_at: float | None = None
    consumed_at: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApprovalRegistry:
    def __init__(self, ttl_s: int = 300, clock: Any = time.time) -> None:
        self.ttl_s = ttl_s
        self._clock = clock
        self._lock = threading.Lock()
        self._items: dict[str, Approval] = {}

    @staticmethod
    def args_hash(args: dict[str, Any]) -> str:
        return canonical_hash(args)

    def _expire_locked(self) -> None:
        now = self._clock()
        for item in self._items.values():
            if item.status == "granted" and item.expires_at is not None and now > item.expires_at:
                item.status = "expired"
                item.history.append({"at": now, "event": "expired"})

    def request(
        self,
        tool: str,
        args: dict[str, Any],
        reason: str,
        contract_hash: str,
        requested_by: str = "agent",
    ) -> Approval:
        with self._lock:
            self._expire_locked()
            approval = Approval(
                approval_id=f"apr_{secrets.token_hex(6)}",
                tool=tool,
                args_hash=self.args_hash(args),
                args=dict(args),
                reason=reason[:500],
                contract_hash=contract_hash,
                requested_by=requested_by,
                requested_at=self._clock(),
            )
            approval.history.append({"at": approval.requested_at, "event": "requested", "by": requested_by})
            self._items[approval.approval_id] = approval
            return approval

    def decide(self, approval_id: str, grant: bool, decided_by: str) -> Approval:
        with self._lock:
            self._expire_locked()
            approval = self._items.get(approval_id)
            if approval is None:
                raise KeyError(approval_id)
            if approval.status != "pending":
                raise ApprovalError(f"approval {approval_id} is {approval.status}, not pending")
            now = self._clock()
            approval.status = "granted" if grant else "denied"
            approval.decided_by = decided_by
            approval.decided_at = now
            approval.expires_at = now + self.ttl_s if grant else None
            approval.history.append({"at": now, "event": approval.status, "by": decided_by})
            return approval

    def consume(self, approval_id: str, tool: str, args: dict[str, Any], contract_hash: str) -> Approval:
        with self._lock:
            self._expire_locked()
            approval = self._items.get(approval_id)
            if approval is None:
                raise ApprovalError("approval not found")
            if approval.status != "granted":
                raise ApprovalError(f"approval is {approval.status}")
            if approval.tool != tool:
                raise ApprovalError("approval was granted for a different tool")
            if approval.args_hash != self.args_hash(args):
                raise ApprovalError("approval was granted for different arguments")
            if approval.contract_hash != contract_hash:
                raise ApprovalError("approval belongs to a different rig contract")
            now = self._clock()
            approval.status = "consumed"
            approval.consumed_at = now
            approval.history.append({"at": now, "event": "consumed"})
            return approval

    def get(self, approval_id: str) -> Approval | None:
        with self._lock:
            self._expire_locked()
            return self._items.get(approval_id)

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            self._expire_locked()
            rows = [
                item.to_dict() for item in self._items.values() if status is None or item.status == status
            ]
            rows.sort(key=lambda row: row["requested_at"], reverse=True)
            return rows
