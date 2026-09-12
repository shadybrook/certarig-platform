from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from .app import CertaRigApplication, make_server
from .bootstrap import DEFAULT_SKILLS_ROOT, DEFAULT_STUDIO_ROOT, NodeSettings, build_hardware, build_node
from .config import load_config
from .evidence import EvidenceStore
from .server import make_edge_server


def serve(args: argparse.Namespace) -> None:
    """Run the unified Edge node: live kernel, procedures, approvals, ops and Studio."""
    settings = NodeSettings.from_env(
        args.config,
        args.capabilities,
        args.evidence_dir,
        None if args.no_studio else args.static_root,
        args.skills_root,
    )
    node = build_node(settings)
    server = make_edge_server(node, args.bind, args.port)
    node.start()
    from .watchdog import start_watchdog

    start_watchdog()
    print(
        json.dumps(
            {
                "event": "certarig_edge_started",
                "url": f"http://{args.bind}:{server.server_port}/",
                "rig_id": node.config.rig_id,
                "hardware_mode": node.config.hardware.mode,
                "actuation_enabled": node.runtime.allow_output,
                "config_hash": node.config.config_hash,
                "manifest_id": node.manifest.manifest_id,
                "contract_hash": node.contract_hash,
                "evidence_dir": str(Path(args.evidence_dir).resolve()),
                "agent_principal_enabled": node.agent_key is not None,
                "procedures": [row["id"] for row in node.extensions["procedures"].library.list()],
            },
            indent=2,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        node.close()


def legacy_plan_api(args: argparse.Namespace) -> None:
    """Phase 2 plan/approve/execute API. Kept for the archived PoC workflow only."""
    operator_key = os.environ.get("CERTARIG_OPERATOR_KEY", "")
    if len(operator_key) < 12:
        raise SystemExit("CERTARIG_OPERATOR_KEY must be set to at least 12 characters")
    config = load_config(args.config)
    hardware = build_hardware(config)
    store = EvidenceStore(args.database)
    app = CertaRigApplication(
        config=config,
        hardware=hardware,
        store=store,
        operator_key=operator_key,
        actuation_enabled=os.environ.get("CERTARIG_ENABLE_ACTUATION") == "1",
    )
    server = make_server(app, args.bind, args.port)
    print(json.dumps({"event": "certarig_legacy_plan_api_started", "port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


def add_edge_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    edge = subparsers.add_parser("edge", help="run the CertaRig Edge node")
    edge_sub = edge.add_subparsers(dest="edge_command", required=True)

    run = edge_sub.add_parser("serve", help="serve the unified Edge API and Studio")
    run.add_argument("--config", default="config/rig.wave1.json")
    run.add_argument("--capabilities", default="config/capabilities.wave1.json")
    run.add_argument("--evidence-dir", default="evidence/runs")
    run.add_argument("--static-root", default=str(DEFAULT_STUDIO_ROOT))
    run.add_argument("--no-studio", action="store_true", help="do not serve Studio static files")
    run.add_argument("--skills-root", default=str(DEFAULT_SKILLS_ROOT), help="directory of skills/procedures")
    run.add_argument("--bind", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8080)
    run.set_defaults(func=serve)

    legacy = edge_sub.add_parser("legacy-plan-api", help="Phase 2 plan/approve/execute API")
    legacy.add_argument("--config", default="config/rig.example.json")
    legacy.add_argument("--database", default="certarig_evidence.sqlite3")
    legacy.add_argument("--bind", default="127.0.0.1")
    legacy.add_argument("--port", type=int, default=8081)
    legacy.set_defaults(func=legacy_plan_api)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certarig", description="CertaRig agentic test-operations platform")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_edge_parser(subparsers)
    try:
        from certarig.sim.cli import add_sim_parser

        add_sim_parser(subparsers)
    except ImportError:  # pragma: no cover - sim lands in M3
        pass
    try:
        from certarig.agent.cli import add_agent_parser

        add_agent_parser(subparsers)
    except ImportError:  # pragma: no cover - agent lands in M4
        pass
    try:
        from .evidence_cli import add_evidence_parser

        add_evidence_parser(subparsers)
    except ImportError:  # pragma: no cover - evidence tooling lands in M5/M7
        pass
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])
    args.func(args)
