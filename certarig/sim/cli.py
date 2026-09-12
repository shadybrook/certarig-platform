"""``certarig sim`` sub-commands: serve the digital twin, run scenarios, run the library."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from certarig.edge.bootstrap import DEFAULT_SKILLS_ROOT, DEFAULT_STUDIO_ROOT

from .scenario import CONFIG_DIR, ROOT, SKILLS_DIR, ScenarioResult, discover_scenarios, run_scenario_file

SIM_SCENARIOS = Path(__file__).resolve().parent / "scenarios"


def sim_serve(args: argparse.Namespace) -> None:
    """Serve the Edge node on the simulator with Studio. Sets demo keys if none are configured."""
    os.environ.setdefault("CERTARIG_OPERATOR_KEY", "sim-operator-key-000001")
    os.environ.setdefault("CERTARIG_AGENT_KEY", "sim-agent-key-0000000001")
    from certarig.edge.cli import serve

    serve(
        argparse.Namespace(
            config=args.config,
            capabilities=args.capabilities,
            evidence_dir=args.evidence_dir,
            static_root=str(DEFAULT_STUDIO_ROOT),
            no_studio=False,
            skills_root=str(DEFAULT_SKILLS_ROOT),
            bind=args.bind,
            port=args.port,
        )
    )


def sim_run(args: argparse.Namespace) -> None:
    out = Path(args.out) if args.out else None
    result = run_scenario_file(args.scenario, out)
    print(json.dumps(result.to_dict() if args.verbose else _brief(result), indent=2))
    if not result.passed:
        sys.exit(1)


def _brief(result: ScenarioResult) -> dict[str, object]:
    return {
        "name": result.name,
        "passed": result.passed,
        "failures": result.failures,
        "kernel_events": result.kernel_events,
        "csv_rows": result.csv_rows,
        "sim_time_s": result.sim_time_s,
        "wall_time_s": result.wall_time_s,
        "outcome": (result.run or {}).get("status"),
        "evidence_dir": result.evidence_dir,
    }


def sim_run_library(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = discover_scenarios(SKILLS_DIR, SIM_SCENARIOS)
    if args.filter:
        paths = [path for path in paths if args.filter in str(path)]
    summary = []
    failed = 0
    for path in paths:
        result = run_scenario_file(path, out)
        summary.append({"scenario": str(path.relative_to(ROOT)), **_brief(result)})
        status = "PASS" if result.passed else "FAIL"
        print(
            f"[{status}] {path.relative_to(ROOT)} ({result.wall_time_s:.1f}s) {result.failures or ''}",
            flush=True,
        )
        failed += 0 if result.passed else 1
    (out / "library_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{len(paths) - failed}/{len(paths)} scenarios passed; evidence in {out}")
    if failed:
        sys.exit(1)


def add_sim_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    sim = subparsers.add_parser("sim", help="digital twin: serve, run scenarios, run the procedure library")
    sim_sub = sim.add_subparsers(dest="sim_command", required=True)

    serve = sim_sub.add_parser("serve", help="serve the Edge node + Studio on the simulator")
    serve.add_argument("--config", default=str(CONFIG_DIR / "rig.sim.json"))
    serve.add_argument("--capabilities", default=str(CONFIG_DIR / "capabilities.wave1.json"))
    serve.add_argument("--evidence-dir", default="evidence/sim")
    serve.add_argument("--bind", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(func=sim_serve)

    run = sim_sub.add_parser("run", help="run one scenario file")
    run.add_argument("scenario")
    run.add_argument("--out", default=None, help="directory to copy evidence into")
    run.add_argument("--verbose", action="store_true")
    run.set_defaults(func=sim_run)

    library = sim_sub.add_parser("run-library", help="run every shipped scenario and write evidence")
    library.add_argument("--out", default="evidence/sim-library")
    library.add_argument("--filter", default=None, help="substring filter on scenario paths")
    library.set_defaults(func=sim_run_library)
