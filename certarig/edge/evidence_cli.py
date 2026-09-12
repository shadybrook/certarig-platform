"""``certarig evidence`` sub-commands: pull a checksummed bundle from a node and verify it locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path
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


def verify_directory(root: Path) -> dict[str, Any]:
    """Verify every file listed in SHA256SUMS.txt under ``root`` and report extras/missing."""
    sums_path = root / SUMS_FILE
    if not sums_path.is_file():
        return {"ok": False, "error": f"{SUMS_FILE} missing", "root": str(root)}
    expected = parse_sums(sums_path.read_text(encoding="utf-8"))
    mismatched: list[str] = []
    missing: list[str] = []
    for name, digest in expected.items():
        path = root / name
        if not path.is_file():
            missing.append(name)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            mismatched.append(name)
    listed = set(expected) | {SUMS_FILE, EXPORT_MANIFEST}
    extra = sorted(
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and str(p.relative_to(root)) not in listed
    )
    return {
        "ok": not mismatched and not missing,
        "root": str(root),
        "files": len(expected),
        "mismatched": mismatched,
        "missing": missing,
        "unlisted": extra,
    }


def verify_zip(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if SUMS_FILE not in names:
            return {"ok": False, "error": f"{SUMS_FILE} missing", "zip": str(path)}
        expected = parse_sums(archive.read(SUMS_FILE).decode("utf-8"))
        mismatched = [
            name
            for name, digest in expected.items()
            if name not in names or hashlib.sha256(archive.read(name)).hexdigest() != digest
        ]
        unlisted = sorted(names - set(expected) - {SUMS_FILE, EXPORT_MANIFEST})
    return {
        "ok": not mismatched,
        "zip": str(path),
        "files": len(expected),
        "mismatched": mismatched,
        "unlisted": unlisted,
    }


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


def evidence_accept_twin_gate(args: argparse.Namespace) -> None:
    from .twin_gate import accept_twin_gate

    result = accept_twin_gate(Path(args.source), Path(args.into))
    print(json.dumps(result, indent=2))
    if result["count"] == 0:
        sys.exit(1)


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

    ingest = sub.add_parser(
        "accept-twin-gate",
        help="copy simulator twin-gate stamps into a node evidence dir",
    )
    ingest.add_argument("--from", dest="source", required=True, help="sim library or twin_gate directory")
    ingest.add_argument("--into", required=True, help="node evidence directory")
    ingest.set_defaults(func=evidence_accept_twin_gate)
