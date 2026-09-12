"""Operational endpoints: evidence listing/download, recorder stop, evidence export, shutdown.

Everything here is governed by the capability manifest like any other tool. ``shutdown`` is the
procedure that was improvised over SSH on 2026-09-12; it is now a single audited call that
refuses while a procedure run is active, forces the kernel safe, flushes the recorder, writes a
shutdown record into the evidence directory and only then hands over to the OS.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import threading
import time
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from certarig import __version__

from .server import EdgeNode, HttpError, RequestContext

EXPORTS_DIR = "exports"
SUMS_FILE = "SHA256SUMS.txt"
EXPORT_MANIFEST = "export_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _safe_name(name: str) -> str:
    if not name or name in {".", ".."} or "/" in name or "\\" in name or name.startswith("."):
        raise HttpError(400, {"error": "invalid file name", "code": "bad_name"})
    return name


def _file_row(path: Path, base: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.relative_to(base)),
        "name": path.name,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "sha256": sha256_file(path),
    }


def evidence_files(evidence_dir: Path, run_id: str | None = None) -> list[Path]:
    """Files that belong in an evidence export: run folders, recordings, shutdown records."""
    if run_id is not None:
        target = evidence_dir / "procedure_runs" / run_id
        return sorted(p for p in target.rglob("*") if p.is_file()) if target.is_dir() else []
    out: list[Path] = []
    for path in sorted(evidence_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(evidence_dir)
        if relative.parts[0] == EXPORTS_DIR:
            continue
        out.append(path)
    return out


def write_sums(files: list[tuple[str, str]]) -> str:
    """Render a ``sha256sum -c`` compatible listing."""
    return "".join(f"{digest}  {name}\n" for name, digest in sorted(files))


def export_bundle(
    evidence_dir: Path,
    context: dict[str, Any],
    run_id: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    files = evidence_files(evidence_dir, run_id)
    if not files:
        raise HttpError(404, {"error": "nothing to export", "code": "no_evidence"})
    out_dir = evidence_dir / EXPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = run_id or label or "all"
    name = f"{_utc_stamp()}_{''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in suffix)}.zip"
    target = out_dir / name
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            row = _file_row(path, evidence_dir)
            rows.append(row)
            archive.write(path, row["path"])
        archive.writestr(SUMS_FILE, write_sums([(row["path"], row["sha256"]) for row in rows]))
        manifest = {
            "kind": "certarig_evidence_export",
            "certarig_version": __version__,
            "created_at": datetime.now(UTC).isoformat(),
            "run_id": run_id,
            "label": label,
            "files": rows,
            **context,
        }
        archive.writestr(EXPORT_MANIFEST, json.dumps(manifest, indent=2, sort_keys=True))
    return {
        "filename": name,
        "path": f"/v1/evidence/exports/{name}",
        "size": target.stat().st_size,
        "sha256": sha256_file(target),
        "files": len(rows),
        "run_id": run_id,
    }


class OpsService:
    def __init__(
        self,
        node: EdgeNode,
        poweroff: Callable[[], None] | None = None,
        shutdown_delay_s: float = 1.0,
    ) -> None:
        self.node = node
        self.poweroff = poweroff
        self.shutdown_delay_s = shutdown_delay_s
        self.shutting_down = False
        self.shutdown_record: dict[str, Any] | None = None
        self._lock = threading.Lock()

    @property
    def evidence_dir(self) -> Path:
        return self.node.runtime.evidence_dir

    def _context(self) -> dict[str, Any]:
        return {
            "rig_id": self.node.config.rig_id,
            "hardware_mode": self.node.config.hardware.mode,
            "config_hash": self.node.config.config_hash,
            "manifest_id": self.node.manifest.manifest_id,
            "manifest_hash": self.node.manifest.manifest_hash,
            "contract_hash": self.node.contract_hash,
        }

    # ------------------------------------------------------------ evidence
    def _runs(self) -> list[dict[str, Any]]:
        procedures = self.node.extensions.get("procedures")
        rows: list[dict[str, Any]] = list(procedures.runner.list()) if procedures is not None else []
        known = {row["run_id"] for row in rows}
        runs_dir = self.evidence_dir / "procedure_runs"
        if runs_dir.is_dir():
            for folder in sorted(runs_dir.iterdir()):
                run_file = folder / "run.json"
                if folder.name in known or not run_file.is_file():
                    continue
                try:
                    document = json.loads(run_file.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                rows.append(
                    {
                        "run_id": document.get("run_id", folder.name),
                        "procedure_id": document.get("procedure_id"),
                        "status": document.get("status"),
                        "started_at": document.get("started_at"),
                        "ended_at": document.get("ended_at"),
                        "outcome_reason": document.get("outcome_reason"),
                        "persisted_only": True,
                    }
                )
        return rows

    def list_evidence(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        recordings = [
            {**_file_row(p, self.evidence_dir), "path": f"/v1/evidence/recordings/{p.name}"}
            for p in sorted(self.evidence_dir.glob("*.csv"))
        ]
        exports_dir = self.evidence_dir / EXPORTS_DIR
        exports = (
            [
                {**_file_row(p, self.evidence_dir), "path": f"/v1/evidence/exports/{p.name}"}
                for p in sorted(exports_dir.glob("*.zip"))
            ]
            if exports_dir.is_dir()
            else []
        )
        shutdowns = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(self.evidence_dir.glob("shutdown_*.json"))
        ]
        return 200, {
            "evidence_dir": str(self.evidence_dir),
            "runs": self._runs(),
            "recordings": recordings,
            "exports": exports,
            "shutdowns": shutdowns,
            "recording_active": bool(self.node.runtime.state()["recording"]["active"]),
            **self._context(),
        }

    def run_files(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        run_id = _safe_name(ctx.params["run_id"])
        folder = self.evidence_dir / "procedure_runs" / run_id
        if not folder.is_dir():
            raise HttpError(404, "run evidence not found")
        files = [
            {**_file_row(p, folder), "path": f"/v1/evidence/runs/{run_id}/files/{p.name}"}
            for p in sorted(folder.iterdir())
            if p.is_file()
        ]
        return 200, {"run_id": run_id, "files": files}

    def _serve(self, path: Path, base: Path) -> tuple[int, bytes, str]:
        resolved = path.resolve()
        if not resolved.is_file() or base.resolve() not in resolved.parents:
            raise HttpError(404, "file not found")
        suffix = resolved.suffix.lower()
        content_type = {
            ".csv": "text/csv; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".jsonl": "application/x-ndjson; charset=utf-8",
            ".zip": "application/zip",
            ".md": "text/markdown; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        return 200, resolved.read_bytes(), content_type

    def run_file(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        run_id = _safe_name(ctx.params["run_id"])
        name = _safe_name(ctx.params["name"])
        base = self.evidence_dir / "procedure_runs" / run_id
        return self._serve(base / name, base)

    def recording_file(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        name = _safe_name(ctx.params["name"])
        if not name.endswith(".csv"):
            raise HttpError(404, "file not found")
        return self._serve(self.evidence_dir / name, self.evidence_dir)

    def export_file(self, ctx: RequestContext) -> tuple[int, bytes, str]:
        name = _safe_name(ctx.params["name"])
        base = self.evidence_dir / EXPORTS_DIR
        return self._serve(base / name, base)

    # ------------------------------------------------------------ ops tools
    def stop_recorder(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        procedures = self.node.extensions.get("procedures")
        active = procedures.runner.active if procedures is not None else None
        if active is not None and not ctx.body.get("force"):
            raise HttpError(
                409,
                {
                    "error": f"procedure run {active.run_id} owns the recorder; abort the run or pass force=true",
                    "code": "run_active",
                    "run_id": active.run_id,
                },
            )
        state = self.node.runtime.state()
        if not state["recording"]["active"]:
            return 200, {"stopped": False, "reason": "no recording active", "recording": state["recording"]}
        state = self.node.runtime.stop_recording()
        return 200, {"stopped": True, "completed_recording": state.get("completed_recording")}

    def export_evidence(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        run_id = ctx.body.get("run_id")
        label = ctx.body.get("label")
        bundle = export_bundle(
            self.evidence_dir,
            self._context(),
            _safe_name(str(run_id)) if run_id else None,
            str(label) if label else None,
        )
        return 200, bundle

    def shutdown(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        procedures = self.node.extensions.get("procedures")
        active = procedures.runner.active if procedures is not None else None
        if active is not None:
            raise HttpError(
                409,
                {
                    "error": f"procedure run {active.run_id} is active; abort or finish it before shutting down",
                    "code": "run_active",
                    "run_id": active.run_id,
                },
            )
        with self._lock:
            if self.shutting_down:
                return 200, {"status": "shutting_down", "record": self.shutdown_record}
            self.shutting_down = True
        reason = str(ctx.body.get("reason") or "operator requested shutdown")
        steps: list[dict[str, Any]] = []
        state = self.node.runtime.state()
        if state["recording"]["active"]:
            stopped = self.node.runtime.stop_recording()
            steps.append({"step": "recorder_stopped", **(stopped.get("completed_recording") or {})})
        state = self.node.runtime.command("safe")
        steps.append(
            {
                "step": "kernel_forced_safe",
                "event": state["guardrail"].get("event"),
                "output_high": state["outputs"]["gpio23_command_high"],
            }
        )
        record = {
            "kind": "certarig_shutdown",
            "at": datetime.now(UTC).isoformat(),
            "reason": reason,
            "requested_by": {"principal": ctx.principal.value, "name": ctx.principal_name},
            "approval_id": ctx.approval_id,
            "steps": steps,
            "poweroff": "scheduled" if self.poweroff is not None else "not configured (runtime close only)",
            **self._context(),
        }
        (self.evidence_dir / f"shutdown_{_utc_stamp()}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )
        self.shutdown_record = record
        self.node.flags["shutting_down"] = True
        threading.Thread(target=self._complete_shutdown, name="certarig-shutdown", daemon=True).start()
        return 200, {"status": "shutting_down", "record": record}

    def _complete_shutdown(self) -> None:
        time.sleep(self.shutdown_delay_s)
        try:
            self.node.runtime.close()
        finally:
            if self.poweroff is not None:
                self.poweroff()


def poweroff_command(command: str) -> Callable[[], None]:
    """Run an OS poweroff command detached from the Edge process (systemd will stop the unit)."""

    def run() -> None:
        subprocess.Popen(shlex.split(command), start_new_session=True)  # noqa: S603

    return run


def install_ops(
    node: EdgeNode, poweroff: Callable[[], None] | None = None, shutdown_delay_s: float = 1.0
) -> OpsService:
    service = OpsService(node, poweroff, shutdown_delay_s)
    add = node.add_route
    add("GET", "/v1/evidence", service.list_evidence, "read_evidence")
    add("GET", "/v1/evidence/runs/{run_id}", service.run_files, "read_evidence")
    add("GET", "/v1/evidence/runs/{run_id}/files/{name}", service.run_file, "read_evidence")
    add("GET", "/v1/evidence/recordings/{name}", service.recording_file, "read_evidence")
    add("GET", "/v1/evidence/exports/{name}", service.export_file, "read_evidence")
    add("POST", "/v1/ops/recorder/stop", service.stop_recorder, "stop_recorder")
    add("POST", "/v1/ops/evidence/export", service.export_evidence, "export_evidence")
    add("POST", "/v1/ops/shutdown", service.shutdown, "shutdown")
    node.extensions["ops"] = service
    return service
