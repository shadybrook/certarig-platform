from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import CommissioningPlan, EvidenceEvent, RunResult


class EvidenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence)
                );
                """
            )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def save_plan(self, plan: CommissioningPlan) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO plans(plan_id, state, config_hash, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    state=excluded.state,
                    config_hash=excluded.config_hash,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    plan.plan_id,
                    plan.state.value,
                    plan.config_hash,
                    self._json(plan.to_dict()),
                    plan.approved_at or plan.created_at,
                ),
            )

    def append_event(self, event: EvidenceEvent) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO events(run_id, sequence, event_type, payload_json, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.run_id,
                    event.sequence,
                    event.event_type,
                    self._json(event.payload),
                    event.recorded_at,
                ),
            )

    def checksum(self, run_id: str) -> str:
        rows = self._connection.execute(
            "SELECT sequence, event_type, payload_json, recorded_at FROM events WHERE run_id=? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        payload = [dict(row) for row in rows]
        return hashlib.sha256(self._json(payload).encode("utf-8")).hexdigest()

    def save_run(self, result: RunResult) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO runs(run_id, plan_id, outcome, payload_json, completed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    result.plan_id,
                    result.outcome.value,
                    self._json(result.to_dict()),
                    result.completed_at,
                ),
            )

    def evidence_bundle(self, run_id: str) -> dict[str, Any] | None:
        run_row = self._connection.execute(
            "SELECT payload_json FROM runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run_row is None:
            return None
        events = self._connection.execute(
            "SELECT sequence, event_type, payload_json, recorded_at FROM events WHERE run_id=? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        return {
            "run": json.loads(run_row["payload_json"]),
            "events": [
                {
                    "sequence": row["sequence"],
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload_json"]),
                    "recorded_at": row["recorded_at"],
                }
                for row in events
            ],
            "checksum": self.checksum(run_id),
        }

    def close(self) -> None:
        self._connection.close()
