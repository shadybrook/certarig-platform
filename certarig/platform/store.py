"""Transactional organization data and private server sessions."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from certarig.edge.atomic import write_json_atomic


def uid(prefix: str) -> str:
    return prefix + "_" + secrets.token_hex(12)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Actor:
    user_id: str
    org_id: str
    role: str


class Store:
    def __init__(self, root: Path, clock: Any = time.time):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
            raise ValueError("Platform storage requires a private directory owned by this user")
        self.root, self.clock = root, clock
        self.lock = threading.RLock()
        self.db = sqlite3.connect(root / "platform.sqlite", check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, issuer TEXT, subject TEXT, UNIQUE(issuer,subject));
        CREATE TABLE IF NOT EXISTS memberships(user_id TEXT REFERENCES users(id), org_id TEXT, role TEXT,
          enabled INTEGER DEFAULT 1, PRIMARY KEY(user_id,org_id));
        CREATE TABLE IF NOT EXISTS documents(kind TEXT,id TEXT,org TEXT,asset TEXT,body TEXT,
          PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,user_id TEXT,org_id TEXT,csrf TEXT,
          created REAL,touched REAL);
        CREATE TABLE IF NOT EXISTS transactions(kind TEXT,hash TEXT,body TEXT,expires REAL,PRIMARY KEY(kind,hash));
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, org TEXT,body TEXT);
        """)

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def provision(self, issuer: str, subject: str, org: str, role: str) -> str:
        if role not in {"author", "reviewer"}:
            raise ValueError("unknown application role")
        with self.lock, self.db:
            self.db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?)", (uid("usr"), issuer, subject))
            user = self.db.execute(
                "SELECT id FROM users WHERE issuer=? AND subject=?", (issuer, subject)
            ).fetchone()[0]
            self.db.execute("INSERT OR REPLACE INTO memberships VALUES(?,?,?,1)", (user, org, role))
            return str(user)

    def rows(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.lock:
            return list(self.db.execute(sql, parameters).fetchall())

    def one(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        values = self.rows(sql, parameters)
        return values[0] if values else None

    def actor(self, user: str, org: str) -> Actor:
        row = self.one("SELECT role FROM memberships WHERE user_id=? AND org_id=? AND enabled=1", (user, org))
        if not row:
            raise PermissionError("No active organization membership")
        return Actor(user, org, str(row[0]))

    def login(self, issuer: str, subject: str) -> tuple[str, dict[str, Any]]:
        with self.lock:
            row = self.db.execute(
                "SELECT u.id,m.org_id FROM users u JOIN memberships m ON m.user_id=u.id WHERE issuer=? AND subject=? AND enabled=1 ORDER BY m.org_id",
                (issuer, subject),
            ).fetchone()
            if not row:
                raise PermissionError("Account has no organization membership")
            token, csrf, now = secrets.token_urlsafe(32), secrets.token_urlsafe(32), self.clock()
            self.db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?)", (sha(token), row[0], row[1], csrf, now, now)
            )
            return token, {"user_id": row[0], "org_id": row[1], "csrf": csrf}

    def session(self, token: str, csrf: str | None = None) -> tuple[Actor, str]:
        with self.lock:
            row = self.db.execute("SELECT * FROM sessions WHERE hash=?", (sha(token),)).fetchone()
            if not row or self.clock() - row["created"] >= 28800 or self.clock() - row["touched"] >= 1800:
                raise PermissionError("Application session expired; sign in again")
            if csrf is not None and not secrets.compare_digest(csrf, row["csrf"]):
                raise PermissionError("Invalid CSRF token")
            actor = self.actor(row["user_id"], row["org_id"])
            self.db.execute("UPDATE sessions SET touched=? WHERE hash=?", (self.clock(), sha(token)))
            return actor, str(row["csrf"])

    def logout(self, token: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM sessions WHERE hash=?", (sha(token),))

    def transaction(self, kind: str, token: str, body: dict[str, Any], ttl: float = 300) -> None:
        with self.lock:
            self.db.execute(
                "INSERT INTO transactions VALUES(?,?,?,?)",
                (kind, sha(token), json.dumps(body), self.clock() + ttl),
            )

    def consume(self, kind: str, token: str) -> dict[str, Any]:
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row = self.db.execute(
                    "SELECT * FROM transactions WHERE kind=? AND hash=?", (kind, sha(token))
                ).fetchone()
                if not row or row["expires"] <= self.clock():
                    raise ValueError("Expired or consumed transaction")
                self.db.execute("DELETE FROM transactions WHERE kind=? AND hash=?", (kind, sha(token)))
                self.db.execute("COMMIT")
                return dict(json.loads(row["body"]))
            except Exception:
                self.db.execute("ROLLBACK")
                raise

    def put(self, kind: str, value: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)",
                (
                    kind,
                    value["id"],
                    value["org_id"],
                    value.get("asset_id", ""),
                    json.dumps(value, allow_nan=False),
                ),
            )
            return value

    def get(self, kind: str, identifier: str, org: str) -> dict[str, Any]:
        row = self.one("SELECT body FROM documents WHERE kind=? AND id=? AND org=?", (kind, identifier, org))
        if not row:
            raise KeyError("Resource not found")
        return dict(json.loads(row[0]))

    def listing(self, kind: str, org: str) -> list[dict[str, Any]]:
        return [
            dict(json.loads(r[0]))
            for r in self.rows(
                "SELECT body FROM documents WHERE kind=? AND org=? ORDER BY rowid", (kind, org)
            )
        ]

    def audit(self, org: str, event: str, actor: str, **fields: Any) -> None:
        with self.lock:
            self.db.execute(
                "INSERT INTO audit(org,body) VALUES(?,?)",
                (
                    org,
                    json.dumps(
                        {"at": self.clock(), "event": event, "actor": actor, **fields}, allow_nan=False
                    ),
                ),
            )

    def events(self, org: str, deployment_id: str) -> list[dict[str, Any]]:
        return [
            dict(v)
            for r in self.rows("SELECT body FROM audit WHERE org=? ORDER BY seq", (org,))
            if (v := json.loads(r[0])).get("deployment_id") == deployment_id
        ]

    def secret(self, identifier: str, value: dict[str, Any] | None = None) -> dict[str, Any]:
        if not identifier.replace("_", "").isalnum():
            raise ValueError("Invalid secret reference")
        path = self.root / "secrets" / (identifier + ".json")
        if value is not None:
            write_json_atomic(path, value)
            os.chmod(path, 0o600)
        if path.is_symlink():
            raise ValueError("Unsafe secret reference")
        return dict(json.loads(path.read_text()))
