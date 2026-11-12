"""Offline consistency and raw-sample replay. HMAC authenticity requires the local broker."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from certarig.edge.config import canonical_hash

from .contracts import LIMITS, TERMINAL, binding, digest, safe_name, verify_rehearsal


def verify(path: Path) -> dict[str, Any]:
    errors = []
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 6000 or sum(e.file_size for e in entries) > LIMITS["workspace_bytes"] * 2:
                raise ValueError("bundle exceeds evidence limits")
            if len({e.filename for e in entries}) != len(entries) or any(
                not safe_name(e.filename) or (e.external_attr >> 16) & 0o170000 == 0o120000 for e in entries
            ):
                raise ValueError("unsafe or duplicate bundle member")
            files = {e.filename: archive.read(e) for e in entries}
        manifest = json.loads(files["manifest.json"])
        if manifest["kind"] != "certarig_sandbox_bundle" or manifest["authority"] != "none":
            raise ValueError("invalid sandbox manifest")
        expected = manifest["files"]
        if set(expected) != set(files) - {"manifest.json"} or any(
            digest(files[n]) != sha for n, sha in expected.items()
        ):
            raise ValueError("missing/corrupt/unlisted artifact")
        w = json.loads(files["workspace.json"])
        if canonical_hash(w["snapshot"]) != w["snapshot_hash"] or w["authority"] != "none":
            raise ValueError("workspace snapshot/authority mismatch")
        if w.get("recording") and digest(files["recording.csv"]) != w["recording"]["sha256"]:
            raise ValueError("recording input mismatch")
        for revision in range(w["revision"] + 1):
            if (
                canonical_hash(json.loads(files[f"snapshot-{revision}.json"]))
                != w["revision_hashes"][str(revision)]
            ):
                raise ValueError("snapshot history mismatch")
        for job in w["jobs"]:
            if job["status"] not in TERMINAL:
                raise ValueError("unfinished job in exported evidence")
            prefix = job["job_id"] + "/"
            for name, sha in job["input_hashes"].items():
                if digest(files[prefix + "inputs/" + name]) != sha:
                    raise ValueError("job input mismatch")
            outputs = {n: files[prefix + "artifacts/" + n] for n in job["artifacts"]}
            if any(digest(outputs[n]) != sha for n, sha in job["artifacts"].items()):
                raise ValueError("job artifact mismatch")
            if job.get("receipt"):
                raw = json.loads(files[prefix + "inputs/snapshot.json"])
                receipt = job["receipt"]
                if (
                    receipt.get("job_id") != job["job_id"]
                    or receipt.get("workspace_revision") != job["revision"]
                ):
                    raise ValueError("receipt job/revision mismatch")
                if receipt["binding"] != binding(
                    {k: v for k, v in raw.items() if k != "seed"}, job["runner_image"], raw["seed"]
                ):
                    raise ValueError("receipt binding mismatch")
                if verify_rehearsal(raw, outputs) != receipt["verification"]:
                    raise ValueError("raw-sample qualification replay mismatch")
            elif job["qualification"]:
                raise ValueError("qualification without trusted receipt")
        return {
            "ok": True,
            "sandbox_id": w["sandbox_id"],
            "authority": "none",
            "jobs": len(w["jobs"]),
            "authenticity": "Consistency/replay only; validate receipt HMAC with original local broker",
        }
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        errors.append(str(exc))
    return {"ok": False, "errors": errors}
