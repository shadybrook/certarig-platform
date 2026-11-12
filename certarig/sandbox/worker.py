"""Container-only entrypoint; this module is never invoked with submitted content on the host."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .contracts import LIMITS, REQUIRED_CASES, SUITE, blockers, encoded, safe_name


def rehearse(value: dict[str, Any], output: Path, scratch: Path) -> None:
    from certarig.edge.runtime.model import Procedure
    from certarig.sim.scenario import ScenarioRunner

    errors = blockers(value)
    if errors:
        raise ValueError("; ".join(errors))
    document = json.loads(json.dumps(value["document"]))
    document["hardware"]["mode"] = "simulator"
    sim = document["hardware"].setdefault("simulator", {})
    sim.update(seed=value["seed"], time_scale=1.0)
    path = scratch / "rig.json"
    path.write_bytes(encoded(document))
    procedure = value["procedure"]
    channel = next(c for c in document["channels"] if c.get("required", True))
    report: dict[str, Any] = {"suite_revision": SUITE, "cases": {}}

    class Runner(ScenarioRunner):
        def _build(self, temp: Path) -> tuple[Any, Any]:
            node, rig = super()._build(temp)
            node.extensions["procedures"].library.add(Procedure.from_dict(procedure))
            return node, rig

    for name in REQUIRED_CASES:
        events: list[dict[str, Any]] = []
        scenario: dict[str, Any] = {
            "name": name,
            "rig": str(path),
            "seed": value["seed"],
            "duration_s": min(90, float(procedure.get("timeout_s", 60)) + 2),
            "events": events,
            "auto_ack": True,
            "expect": {
                "invariants": [
                    "ends_safe",
                    "csv_rows_contiguous",
                    "no_restart_without_reset",
                    "output_off_when_process_unsafe",
                ]
            },
        }
        if name == "candidate_procedure":
            scenario["procedure"] = procedure["id"]
            scenario["expect"]["outcome"] = "passed"
            if procedure["id"] == "pressure_guardrail":
                # Explicit simulator stimuli for the existing emulator procedure, never real hardware.
                events.extend(
                    [
                        {
                            "at_step": "raise_pressure",
                            "action": "set_target",
                            "channel": "pressure",
                            "value": 4.6,
                        },
                        {
                            "at_step": "lower_pressure",
                            "action": "set_target",
                            "channel": "pressure",
                            "value": 1.5,
                        },
                    ]
                )
        else:
            scenario["duration_s"] = 1.8
            events.extend(
                [
                    {"at_s": 0.3, "action": "command", "command": "reset"},
                    {"at_s": 0.5, "action": "command", "command": "permit"},
                ]
            )
            if name == "overrange":
                events.append(
                    {
                        "at_s": 0.7,
                        "action": "fault",
                        "kind": "saturate",
                        "channel": channel["channel_id"],
                        "params": {"value": channel["valid_max"] + 10},
                    }
                )
            else:
                events.append(
                    {
                        "at_s": 0.7,
                        "action": "fault",
                        "kind": "stale" if name == "stale_source" else "dropout",
                        "channel": channel["channel_id"],
                    }
                )
            events.append(
                {
                    "at_s": 1.05,
                    "action": "clear",
                    "kind": {"stale_source": "stale", "dropout": "dropout", "overrange": "saturate"}[name],
                    "channel": channel["channel_id"],
                }
            )
            events.append({"at_s": 1.4, "action": "command", "command": "permit"})
            scenario["expect"]["final_output_high"] = False
        result = Runner(scenario, output).run()
        folder = Path(result.evidence_dir or "")
        # Flat artifacts avoid arbitrary nested archive extraction on the host.
        for source in list(folder.iterdir()):
            if source.is_file() and source.suffix == ".csv":
                target = output / (name + ".csv")
                target.write_bytes(source.read_bytes())
                break
        report["cases"][name] = {
            "passed": result.passed,
            "run": result.run,
            "recording": name + ".csv",
            "failures": result.failures,
        }
        # Keep the raw run records as JSON but flatten their filenames.
        (output / (name + "-run.json")).write_bytes(encoded(result.to_dict()))
        import shutil

        if folder.is_dir() and folder != output:
            shutil.rmtree(folder)
        twin = output / "twin_gate"
        if twin.is_dir():
            shutil.rmtree(twin)
    (output / "rehearsal.json").write_bytes(encoded(report))


def main() -> None:
    if os.environ.get("CERTARIG_SANDBOX_WORKER") != "1" or not Path("/out").is_dir():
        raise SystemExit("This entrypoint is container-only")
    kind, seconds = sys.argv[1], int(sys.argv[2])
    scratch, output = Path("/scratch"), Path("/out")
    incoming = json.loads(sys.stdin.buffer.read(LIMITS["input_bytes"] * 2))
    paths: dict[str, Path] = {}
    total = 0
    for name, value in incoming.items():
        if not safe_name(name) or "/" in name:
            raise ValueError("invalid input path")
        raw = base64.b64decode(value, validate=True)
        total += len(raw)
        if total > LIMITS["input_bytes"]:
            raise ValueError("input quota exceeded")
        paths[name] = scratch / name
        paths[name].write_bytes(raw)
    versions = {
        "python": sys.version,
        "ngspice": subprocess.run(
            ["ngspice", "--version"], capture_output=True, timeout=5, check=False
        ).stdout.decode(errors="replace"),
    }
    code = 1
    try:
        if kind == "python":
            code = subprocess.run(
                [sys.executable, str(paths["main.py"])], cwd=output, timeout=seconds, check=False
            ).returncode
        elif kind == "spice":
            code = subprocess.run(
                ["ngspice", "-b", str(paths["circuit.cir"])], cwd=output, timeout=seconds, check=False
            ).returncode
        elif kind == "rehearsal":
            rehearse(json.loads(paths["snapshot.json"].read_text()), output, scratch)
            code = 0
        else:
            raise ValueError("unknown job kind")
    except Exception as exc:
        (output / "worker-error.txt").write_text(f"{type(exc).__name__}: {exc}")
    (output / "worker_record.json").write_bytes(
        encoded({"exit_code": code, "kind": kind, "qualification_claim": False, "engine_versions": versions})
    )
    (scratch / "worker.done").write_text("ready for broker freeze")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
