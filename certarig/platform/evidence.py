"""Portable lifecycle evidence, with strict offline completeness and binding checks."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from typing import Any

import jsonschema

from . import profiles
from .contracts import OUTPUT, encoded, fingerprint, verify_trace
from .service import Platform
from .store import Actor

REQUIRED = {"deployment.json", "version.json", "evaluation.json", "asset.json", "events.json"}


def export(platform: Platform, actor: Actor, identifier: str) -> bytes:
    d = platform.deployment(actor, identifier)
    e = platform.store.get("evaluation", d["evaluation_id"], actor.org_id)
    if not e.get("trusted") or e["status"] != "passed":
        raise ValueError("Complete trusted evaluation required for export")
    values = {
        "deployment.json": d,
        "version.json": platform.version(actor, d["version_id"]),
        "evaluation.json": e,
        "asset.json": profiles.evidence_asset(platform, actor, d),
        "events.json": platform.store.events(actor.org_id, identifier),
    }
    files = {name: encoded(value) for name, value in values.items()}
    from . import evidence_v2

    extra = evidence_v2.context(platform, actor, d)
    if (
        extra["workspace.json"]["drafts"]
        or extra["members.json"]
        or extra["analysis.json"]["runs"]
        or extra["analysis.json"]["tools"]
    ):
        data = evidence_v2.package(files, extra)
        verify(data)
        return data
    files["manifest.json"] = encoded(
        {
            "format": "certarig-agent-evidence/1",
            "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()},
            "claim": "Observations and recorded evaluation only; no physical commissioning or deterministic LLM replay",
        }
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    data = output.getvalue()
    verify(data)
    return data


def verify(data: bytes) -> dict[str, Any]:
    if len(data) > 32 * 1024**2:
        raise ValueError("Evidence archive exceeds limit")
    with zipfile.ZipFile(io.BytesIO(data)) as probe:
        if "manifest.json" in probe.namelist():
            entry = probe.getinfo("manifest.json")
            if entry.file_size > 64000:
                raise ValueError("Oversized manifest")
            if json.loads(probe.read(entry)).get("format") == "certarig-agent-evidence/2":
                from .evidence_v2 import verify as verify_v2

                return verify_v2(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if (
            len(entries) != len(REQUIRED) + 1
            or {i.filename for i in entries} != REQUIRED | {"manifest.json"}
            or any(i.file_size > 16 * 1024**2 for i in entries)
        ):
            raise ValueError("Missing, duplicate or unexpected evidence files")
        files = {i.filename: archive.read(i) for i in entries}
    manifest = json.loads(files.pop("manifest.json"))
    if manifest["format"] != "certarig-agent-evidence/1" or set(manifest["files"]) != REQUIRED:
        raise ValueError("Incomplete evidence manifest")
    for name, payload in files.items():
        if hashlib.sha256(payload).hexdigest() != manifest["files"][name]:
            raise ValueError("Corrupt required evidence: " + name)
    values = {name: json.loads(payload) for name, payload in files.items()}
    d, v, e, a, events = (
        values[n] for n in ("deployment.json", "version.json", "evaluation.json", "asset.json", "events.json")
    )
    if (
        fingerprint({k: x for k, x in v.items() if k != "hash"}) != v["hash"]
        or d["version_id"] != v["id"]
        or d["evaluation_id"] != e["id"]
        or d["author_id"] != v["author_id"]
        or d["reviewer_id"] == v["author_id"]
    ):
        raise ValueError("Invalid version or independent review")
    if (
        len({r["org_id"] for r in (d, v, e, a)}) != 1
        or len({r["asset_id"] for r in (d, v, e)}) != 1
        or d["asset_id"] != a["id"]
    ):
        raise ValueError("Organization or asset binding mismatch")
    if "profile_revision" in e["binding"]:
        profile = a.get("reviewed_profile")
        if (
            not isinstance(profile, dict)
            or profile["revision"] != e["binding"]["profile_revision"]
            or profile["asset_id"] != a["id"]
            or profile["org_id"] != a["org_id"]
            or profile["profile_hash"] != a["profile_hash"]
            or profile.get("capabilities_hash") != e["binding"]["capabilities_hash"]
            or profile["profile"] != a["profile"]
            or profile["profile"]["config_hash"] != a["profile_hash"]
            or profile["record_hash"] != fingerprint({k: v for k, v in profile.items() if k != "record_hash"})
        ):
            raise ValueError("Missing, corrupt or mismatched historical profile review")
    check = verify_trace(e["trace"])
    if (
        not check["passed"]
        or not e["trusted"]
        or e["status"] != "passed"
        or e["receipt"]["verification"] != check
        or e["trace"]["binding"] != e["binding"]
        or d["binding"] != e["binding"]
        or e["binding"]["version_hash"] != v["hash"]
        or e["binding"]["profile_hash"] != a["profile_hash"]
        or e["runner_image"] != d["runner_image"]
        or e["policy_hash"] != d["policy_hash"]
    ):
        raise ValueError("Invalid evaluation binding or trace")
    if not any(
        row["event"] == "reviewed_observation_only"
        and row["actor"] == d["reviewer_id"]
        and row.get("binding") == d["binding"]
        for row in events
    ):
        raise ValueError("Missing review history")
    if len(d["observations"]) != d["assessments"] or d["assessments"] > 10:
        raise ValueError("Incomplete observation history")
    for row in d["observations"]:
        jsonschema.validate(row["output"], OUTPUT)
        if not row["transcript"] or not any(t["kind"] == "model_response" for t in row["transcript"]):
            raise ValueError("Missing observation transcript")
    return {
        "valid": True,
        "format": manifest["format"],
        "backend": e["binding"]["backend"],
        "observations": d["assessments"],
        "evaluation": check,
        "authenticity": "Integrity and internal consistency; compare manifest digest with a trusted original",
    }
