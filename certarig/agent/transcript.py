"""Append-only JSONL transcript of an agent session.

Every entry has ``kind``: session_started, user, model_response, tool_call, tool_result,
assistant, error, session_ended. The transcript is part of the evidence bundle and is the
input to :class:`ReplayProvider`.
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class Transcript:
    def __init__(self, path: str | Path, session_id: str | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = (
            session_id or f"ses_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}"
        )
        self._lock = threading.Lock()
        self.entries = 0

    def write(self, kind: str, **payload: Any) -> dict[str, Any]:
        entry = {"at": datetime.now(UTC).isoformat(), "session_id": self.session_id, "kind": kind, **payload}
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
            self.entries += 1
        return entry

    @staticmethod
    def read(path: str | Path) -> list[dict[str, Any]]:
        rows = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
