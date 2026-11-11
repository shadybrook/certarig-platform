"""Explicit setup, broker lifecycle and offline verification commands."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .broker import Broker
from .contracts import CONTEXT, PROFILE
from .engine import DockerEngine, command, resource_preflight
from .evidence import verify
from .transport import server

DEFAULT_ROOT = Path.home() / ".certarig" / "sandbox"


def prepare(args: argparse.Namespace) -> None:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    check = resource_preflight(root)
    if not check["ready"]:
        print(json.dumps(check, indent=2))
        raise SystemExit(1)
    started = command(
        [
            "colima",
            "start",
            PROFILE,
            "--cpus",
            "2",
            "--memory",
            "2",
            "--disk",
            "20",
            "--mount",
            "none",
            "--activate=false",
        ],
        timeout=180,
    )
    if started.returncode:
        raise SystemExit(started.stderr.decode(errors="replace"))
    repo = Path(__file__).resolve().parents[2]
    # Curated build context avoids sending the repo's .git, credentials, evidence or virtualenv.
    with tempfile.TemporaryDirectory(prefix="cr-sandbox-build-") as temporary:
        stage = Path(temporary)
        for folder in ["certarig", "config", "skills"]:
            source = repo / folder
            if any(p.is_symlink() for p in source.rglob("*")):
                raise ValueError("symlinks are not permitted in the worker build context")
            shutil.copytree(source, stage / folder, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for file in ["pyproject.toml", "README.md"]:
            shutil.copy2(repo / file, stage / file)
        shutil.copy2(repo / "deploy/sandbox/Dockerfile", stage / "Dockerfile")
        shutil.copy2(repo / "deploy/sandbox/requirements.txt", stage / "requirements.txt")
        subprocess.run(
            [
                "docker",
                "--context",
                CONTEXT,
                "build",
                "--platform",
                "linux/arm64",
                "--iidfile",
                str(root / "image.id"),
                "-t",
                "certarig-sandbox:v1",
                str(stage),
            ],
            check=True,
        )
    image = (root / "image.id").read_text().strip()
    check = DockerEngine(image, root, qualification_mode=True).preflight()
    if not check["ready"]:
        raise SystemExit(json.dumps(check))
    os.chmod(root / "image.id", 0o600)
    print(
        json.dumps(
            {
                "image": image,
                "preflight": check,
                "qualification": "pending; run sandbox qualify before serving jobs",
            }
        )
    )


def main_action(args: argparse.Namespace) -> None:
    root = Path(args.root)
    if args.sandbox_command == "verify":
        result = verify(Path(args.bundle))
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            raise SystemExit(1)
    elif args.sandbox_command == "qualify":
        image = (root / "image.id").read_text().strip()
        check = DockerEngine(image, root, qualification_mode=True).preflight()
        if not check["ready"]:
            raise SystemExit(json.dumps(check))
        import sys
        import xml.etree.ElementTree as ET

        repo = Path(__file__).resolve().parents[2]
        report = root / "runtime-tests.xml"
        env = {**os.environ, "CERTARIG_SANDBOX_QUALIFY": "1", "CERTARIG_SANDBOX_ROOT": str(root.resolve())}
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/sandbox/test_runtime.py",
                "-q",
                "--junitxml",
                str(report),
            ],
            cwd=repo,
            env=env,
            check=False,
        )
        expected = {
            "test_container_isolation",
            "test_infinite_loop_deadline",
            "test_memory_limit",
            "test_process_limit",
            "test_excessive_output",
            "test_spice",
            "test_trusted_rehearsal_and_repeatability",
        }
        cases = list(ET.parse(report).getroot().iter("testcase")) if report.exists() else []
        passed = (
            run.returncode == 0
            and {r.attrib["name"] for r in cases} == expected
            and all(not list(r) or all(x.tag == "properties" for x in r) for r in cases)
        )
        from certarig.edge.atomic import write_json_atomic

        write_json_atomic(
            root / "qualification.json",
            {
                "image": image,
                "passed": passed,
                "suite": "sandbox-runtime-v1",
                "cases": sorted(expected),
                "report_sha256": __import__("hashlib").sha256(report.read_bytes()).hexdigest()
                if report.exists()
                else None,
            },
        )
        if not passed:
            raise SystemExit("Runtime qualification failed; jobs remain disabled")
    elif args.sandbox_command == "prepare":
        prepare(args)
    elif args.sandbox_command == "preflight":
        check = resource_preflight(root if root.exists() else Path.cwd())
        image_path = root / "image.id"
        if image_path.is_file():
            check = DockerEngine(image_path.read_text().strip(), root).preflight()
        else:
            check["blockers"].append("Pinned sandbox image has not been built")
            check["ready"] = False
        print(json.dumps(check, indent=2))
    else:
        image = (root / "image.id").read_text().strip()
        engine = DockerEngine(image, root)
        # Broker may expose its blocked status, but never launch without preflight.
        broker = Broker(root, engine)
        endpoint = Path(args.socket)
        listener = server(endpoint, broker)
        try:
            listener.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            listener.server_close()
            broker.close()
            endpoint.unlink(missing_ok=True)


def add_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = sub.add_parser("sandbox", help="local isolated experiments; no physical authority")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    actions = parser.add_subparsers(dest="sandbox_command", required=True)
    for name in ["prepare", "preflight", "qualify", "serve", "verify"]:
        action = actions.add_parser(name)
        action.set_defaults(func=main_action)
        if name == "serve":
            action.add_argument("--socket", default=str(DEFAULT_ROOT / "broker.sock"))
        elif name == "verify":
            action.add_argument("bundle")
