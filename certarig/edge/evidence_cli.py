"""``certarig evidence`` sub-commands: pull a checksummed bundle from a node and verify it locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .client import EdgeClient
from .ops import EXPORT_MANIFEST, SUMS_FILE


def _client(args: argparse.Namespace) -> EdgeClient:
    operator = args.operator_key or os.environ.get("CERTARIG_OPERATOR_KEY")
    agent = args.agent_key or os.environ.get("CERTARIG_AGENT_KEY")
    if not operator and not agent:
        raise SystemExit(
            "set CERTARIG_OPERATOR_KEY or CERTARIG_AGENT_KEY (or pass --operator-key/--agent-key)"
        )
    return EdgeClient(args.url, operator_key=operator, agent_key=agent, principal_name=args.name)


def parse_sums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        out[name.strip()] = digest.strip()
    return out


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name and str(path) == name


def _verify_payload(files: dict[str, bytes]) -> dict[str, Any]:
    if SUMS_FILE not in files:
        return {"ok": False, "error": f"{SUMS_FILE} missing"}
    errors: list[str] = []
    try:
        expected = parse_sums(files[SUMS_FILE].decode("utf-8"))
        if not expected or any(not _safe_member(name) or len(digest) != 64 for name, digest in expected.items()):
            raise ValueError("invalid or empty checksum listing")
        missing = sorted(set(expected) - set(files))
        mismatched = sorted(name for name, digest in expected.items() if name in files and hashlib.sha256(files[name]).hexdigest() != digest)
        # Verify manifests too: omitted requirements are not a complete bundle.
        for name, data in files.items():
            if name.endswith("/manifest.json") or name == "manifest.json":
                manifest = json.loads(data)
                if manifest.get("kind") == "certarig_run_bundle":
                    prefix = name[:-len("manifest.json")]
                    for row in manifest["files"]:
                        target = prefix + row["path"]
                        if not _safe_member(target) or target not in files or hashlib.sha256(files[target]).hexdigest() != row["sha256"]:
                            errors.append(f"missing or corrupt manifest artifact: {target}")
            if name.endswith("/run.json") or name == "run.json":
                run = json.loads(data)
                prefix = name[:-len("run.json")]
                recording = run.get("recording")
                procedure = json.loads(files[prefix + "procedure.json"]) if prefix + "procedure.json" in files else {}
                if procedure.get("record", True) and run.get("status") == "passed" and not recording:
                    errors.append(f"passing run lacks required recording: {name}")
                if recording:
                    target = prefix + str(recording["filename"])
                    if not _safe_member(target) or target not in files or hashlib.sha256(files[target]).hexdigest() != recording["sha256"]:
                        errors.append(f"missing or corrupt raw recording: {target}")
                    elif prefix + "sample_analysis.json" in files:
                        from .recording_analysis import analyze_csv

                        config = json.loads(files[prefix + "config.json"])
                        actual = analyze_csv(files[target], config)
                        if actual != json.loads(files[prefix + "sample_analysis.json"]):
                            errors.append(f"raw sample analysis does not reproduce: {name}")
                        if actual["rows"] != recording["samples"] or actual["unsafe_command_rows"]:
                            errors.append(f"recording count or command invariant mismatch: {name}")
                provenance_name = prefix + "provenance.json"
                if provenance_name in files and json.loads(files[provenance_name]).get("approval_required"):
                    required = ["config.json", "procedure.json", "commissioning.json", "approval.json", "events.jsonl", "sample_analysis.json"]
                    errors.extend(f"required run artifact missing: {prefix + item}" for item in required if prefix + item not in files)
                    approval = json.loads(files.get(prefix + "approval.json", b"null"))
                    if not approval or approval.get("status") != "consumed" or approval.get("contract_hash") != run.get("contract_hash"):
                        errors.append(f"missing or mismatched consumed approval: {name}")
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        return {"ok": False, "error": f"malformed evidence: {exc}"}
    return {
        "ok": not missing and not mismatched and not errors, "files": len(expected),
        "missing": missing, "mismatched": mismatched, "errors": errors,
        "unlisted": sorted(set(files) - set(expected) - {SUMS_FILE, EXPORT_MANIFEST, "manifest.json"}),
    }


def verify_directory(root: Path) -> dict[str, Any]:
    files: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            return {"ok": False, "error": "symbolic links are not portable evidence", "root": str(root)}
        if path.is_file():
            name = path.relative_to(root).as_posix()
            if not _safe_member(name):
                return {"ok": False, "error": "unsafe evidence path", "root": str(root)}
            files[name] = path.read_bytes()
    return {**_verify_payload(files), "root": str(root)}


def verify_zip(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(not _safe_member(name) for name in names):
                return {"ok": False, "error": "unsafe or duplicate archive member", "zip": str(path)}
            result = _verify_payload({name: archive.read(name) for name in names})
            return {**result, "zip": str(path)}
    except (OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "error": str(exc), "zip": str(path)}


def pull(
    client: EdgeClient, out_dir: Path, run_id: str | None = None, label: str | None = None
) -> dict[str, Any]:
    bundle = client.export_evidence(run_id, label)
    data = client.download(bundle["path"])
    digest = hashlib.sha256(data).hexdigest()
    if digest != bundle["sha256"]:
        return {
            "ok": False,
            "error": "downloaded archive checksum does not match the node's report",
            **bundle,
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / bundle["filename"]
    archive_path.write_bytes(data)
    verification = verify_zip(archive_path)
    if not verification["ok"]:
        return {"ok": False, "verification": verification}
    extract_dir = out_dir / archive_path.stem
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.namelist():
            if member.startswith("/") or ".." in Path(member).parts:
                return {"ok": False, "error": f"unsafe member path {member!r}", **bundle}
        archive.extractall(extract_dir)
    verification = verify_directory(extract_dir)
    manifest_path = extract_dir / EXPORT_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    return {
        "ok": verification["ok"],
        "archive": str(archive_path),
        "archive_sha256": digest,
        "extracted_to": str(extract_dir),
        "rig_id": manifest.get("rig_id"),
        "contract_hash": manifest.get("contract_hash"),
        "verification": verification,
        **{k: bundle[k] for k in ("filename", "size", "files", "run_id")},
    }


def evidence_pull(args: argparse.Namespace) -> None:
    result = pull(_client(args), Path(args.out), args.run, args.label)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        sys.exit(1)


def evidence_verify(args: argparse.Namespace) -> None:
    target = Path(args.path)
    result = verify_zip(target) if target.is_file() and target.suffix == ".zip" else verify_directory(target)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        sys.exit(1)


def evidence_list(args: argparse.Namespace) -> None:
    listing = _client(args).evidence()
    print(json.dumps(listing, indent=2))


def add_evidence_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    evidence = subparsers.add_parser("evidence", help="pull, list and verify checksummed evidence bundles")
    sub = evidence.add_subparsers(dest="evidence_command", required=True)

    def common(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--url", default="http://127.0.0.1:8080")
        parser.add_argument("--operator-key", default=None)
        parser.add_argument("--agent-key", default=None)
        parser.add_argument("--name", default="evidence-cli")

    p = sub.add_parser("pull", help="export a bundle on the node, download it and verify every checksum")
    common(p)
    p.add_argument("--out", default="evidence/pulled")
    p.add_argument("--run", default=None, help="only this procedure run id")
    p.add_argument("--label", default=None)
    p.set_defaults(func=evidence_pull)

    v = sub.add_parser("verify", help="verify a pulled bundle (zip or extracted directory) offline")
    v.add_argument("path")
    v.set_defaults(func=evidence_verify)

    ls = sub.add_parser("list", help="list runs, recordings and exports on the node")
    common(ls)
    ls.set_defaults(func=evidence_list)
