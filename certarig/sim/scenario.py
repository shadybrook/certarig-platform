"""Scenario DSL runner: drives the simulated rig while the Edge node runs a procedure."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from certarig.edge.bootstrap import NodeSettings, build_node
from certarig.edge.config import load_config
from certarig.edge.runtime.model import ProcedureRun
from certarig.edge.schemas import validate_against_schema
from certarig.edge.server import EdgeNode

from .invariants import check_all, events_from_rows, read_rows
from .plant import SimSettings, SimulatedRig

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
SKILLS_DIR = ROOT / "skills"
SCENARIO_KEY = "scenario-operator-key-000"
SCENARIO_AGENT_KEY = "scenario-agent-key-00000"


class ScenarioError(ValueError):
    pass


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    failures: list[str]
    run: dict[str, Any] | None
    kernel_events: list[str]
    invariants: dict[str, Any]
    csv_path: str | None
    csv_rows: int
    rig_log: list[dict[str, Any]]
    evidence_dir: str | None
    sim_time_s: float
    wall_time_s: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "failures": self.failures,
            "run": self.run,
            "kernel_events": self.kernel_events,
            "invariants": self.invariants,
            "csv_path": self.csv_path,
            "csv_rows": self.csv_rows,
            "rig_log": self.rig_log,
            "evidence_dir": self.evidence_dir,
            "sim_time_s": self.sim_time_s,
            "wall_time_s": self.wall_time_s,
            "notes": self.notes,
        }


def load_scenario(path: str | Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate_against_schema(raw, "scenario.schema.json", ScenarioError)
    for event in raw["events"]:
        keys = [key for key in ("at_s", "at_step", "when_awaiting") if key in event]
        if len(keys) != 1:
            raise ScenarioError(f"event {event} must have exactly one of at_s, at_step, when_awaiting")
    result: dict[str, Any] = raw
    return result


def discover_scenarios(*roots: Path) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        found.extend(sorted(root.rglob("scenarios/*.yaml")))
    return found


class ScenarioRunner:
    """Runs one scenario in-process against a fresh Edge node and simulator."""

    def __init__(
        self, scenario: dict[str, Any], evidence_root: Path | None = None, poll_s: float = 0.005
    ) -> None:
        self.scenario = scenario
        self.evidence_root = evidence_root
        self.poll_s = poll_s

    def _build(self, temp: Path) -> tuple[EdgeNode, SimulatedRig]:
        config_path = CONFIG_DIR / self.scenario.get("rig", "rig.sim.json")
        config = load_config(config_path)
        mode = config.hardware.mode
        if mode not in {"simulator", "mqtt", "modbus_tcp"}:
            raise ScenarioError(f"scenario rig must use simulator, mqtt or modbus_tcp, not {mode}")
        settings = SimSettings.from_config(config, config.hardware.simulator)
        if "seed" in self.scenario:
            settings.seed = int(self.scenario["seed"])
        plant = SimulatedRig(config, settings)
        hardware: SimulatedRig | Any = plant
        if mode == "mqtt":
            from certarig.edge.hardware.mqtt import MqttHardware

            from .bus_twin import PlantOnBus

            hardware = PlantOnBus(plant, MqttHardware(config))
        elif mode == "modbus_tcp":
            from certarig.edge.hardware.modbus import ModbusHardware

            from .bus_twin import PlantOnBus

            hardware = PlantOnBus(plant, ModbusHardware(config))
        node = build_node(
            NodeSettings(
                config_path=config_path,
                capabilities_path=CONFIG_DIR / self.scenario.get("capabilities", "capabilities.wave1.json"),
                evidence_dir=temp / "evidence",
                static_root=None,
                operator_key=SCENARIO_KEY,
                agent_key=SCENARIO_AGENT_KEY,
                auditor_key=None,
                allow_output=True,
                skills_root=SKILLS_DIR,
            ),
            hardware=hardware,
        )
        return node, hardware

    def _apply(
        self, event: dict[str, Any], node: EdgeNode, rig: SimulatedRig, run_id: str | None, notes: list[str]
    ) -> None:
        action = event["action"]
        procedures = node.extensions["procedures"]
        if action == "set_target":
            rig.set_target(event["channel"], float(event["value"]))
        elif action == "ramp":
            rig.ramp(event["channel"], float(event["to"]), float(event.get("over_s", 1.0)))
        elif action == "estop":
            rig.press_estop(bool(event.get("pressed", True)))
        elif action == "fault":
            rig.inject(str(event["kind"]), event.get("channel"), **dict(event.get("params", {})))
        elif action == "clear":
            rig.clear(event.get("kind"), event.get("channel"))
        elif action == "ack":
            if run_id is None:
                raise ScenarioError("ack without a procedure")
            procedures.runner.ack(run_id, str(event["step"]), "scenario-operator")
        elif action == "command":
            node.runtime.command(str(event["command"]))
        elif action == "abort":
            if run_id is None:
                raise ScenarioError("abort without a procedure")
            threading.Thread(
                target=procedures.runner.abort,
                args=(run_id, str(event.get("reason", "scenario abort")), "scenario-operator"),
                daemon=True,
            ).start()
        elif action == "note":
            notes.append(str(event.get("text", "")))
        else:  # pragma: no cover - schema prevents this
            raise ScenarioError(f"unknown action {action}")

    def run(self) -> ScenarioResult:
        started_wall = time.monotonic()
        notes: list[str] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            node, rig = self._build(temp)
            procedures = node.extensions["procedures"]
            run: ProcedureRun | None = None
            try:
                node.start()
                # wait for the first sample so preconditions see a real state
                deadline = time.monotonic() + 5
                while node.runtime.state()["sample_index"] < 1 and time.monotonic() < deadline:
                    time.sleep(self.poll_s)
                procedure_id = self.scenario.get("procedure")
                if procedure_id:
                    procedure = procedures.library.get(procedure_id)
                    if procedure is None:
                        raise ScenarioError(f"procedure {procedure_id!r} is not in the library")
                    run = procedures.runner.start(
                        procedure, self.scenario.get("label", procedure_id), "scenario"
                    )
                else:
                    node.runtime.start_recording(self.scenario.get("label", "scenario"))
                pending = [dict(event) for event in self.scenario["events"]]
                t0 = rig.sim_time
                duration = float(self.scenario.get("duration_s", 120.0))
                acked: set[str] = set()
                scheduled: list[tuple[float, dict[str, Any]]] = []
                while True:
                    now_sim = rig.sim_time - t0
                    current = procedures.runner.get(run.run_id) if run else None
                    # deliver time and step based events
                    remaining: list[dict[str, Any]] = []
                    for event in pending:
                        fire = False
                        if "at_s" in event:
                            fire = now_sim >= float(event["at_s"])
                        elif "at_step" in event:
                            fire = current is not None and any(
                                step.step_id == event["at_step"] and step.status != "pending"
                                for step in current.steps
                            )
                        elif "when_awaiting" in event:
                            fire = (
                                current is not None
                                and current.status.value == "awaiting_operator"
                                and current.current_step == event["when_awaiting"]
                            )
                        if fire:
                            delay = float(event.get("delay_s", 0))
                            if delay > 0:
                                scheduled.append((now_sim + delay, event))
                            else:
                                self._apply(event, node, rig, run.run_id if run else None, notes)
                        else:
                            remaining.append(event)
                    pending = remaining
                    still: list[tuple[float, dict[str, Any]]] = []
                    for when, event in scheduled:
                        if now_sim >= when:
                            self._apply(event, node, rig, run.run_id if run else None, notes)
                        else:
                            still.append((when, event))
                    scheduled = still
                    if (
                        self.scenario.get("auto_ack")
                        and current is not None
                        and current.status.value == "awaiting_operator"
                        and current.current_step
                        and current.current_step not in acked
                    ):
                        acked.add(current.current_step)
                        procedures.runner.ack(run.run_id, current.current_step, "auto-ack")  # type: ignore[union-attr]
                    if run is not None and current is not None and current.status.terminal:
                        break
                    if run is None and now_sim >= duration:
                        break
                    if now_sim >= duration and run is not None:
                        procedures.runner.abort(run.run_id, "scenario duration cap", "scenario")
                        break
                    time.sleep(self.poll_s)
                if run is None and node.runtime.state()["recording"]["active"]:
                    node.runtime.command("safe")
                    node.runtime.stop_recording()
                final_run = procedures.runner.get(run.run_id) if run else None
            finally:
                node.close()
            run_dict = final_run.to_dict() if final_run else None
            csv_path = node.runtime.latest_recording()
            rows = read_rows(csv_path) if csv_path else []
            kernel_events = events_from_rows(rows)
            if final_run is not None:
                kernel_events = kernel_events or [row["event"] for row in final_run.kernel_events]
            expect = self.scenario["expect"]
            invariant_names = expect.get("invariants") or list(check_all([], []).keys())
            if rows:
                invariants = check_all(rows, kernel_events, invariant_names)
            else:
                # No CSV (record: false): row-based invariants are not applicable; event-based still run.
                invariants = {}
                for name in invariant_names:
                    if name == "no_restart_without_reset":
                        invariants[name] = check_all([], kernel_events, [name])[name]
                    elif name == "ends_safe":
                        invariants[name] = {
                            "passed": not rig.output,
                            "problems": [] if not rig.output else ["output high at end"],
                            "problem_count": 0 if not rig.output else 1,
                        }
                    else:
                        invariants[name] = {
                            "passed": True,
                            "problems": [],
                            "problem_count": 0,
                            "skipped": "no CSV recording",
                        }
            failures = self._judge(expect, run_dict, kernel_events, invariants, rig, len(rows))
            evidence_dir: str | None = None
            if self.evidence_root is not None:
                target = self.evidence_root / _slug(self.scenario["name"])
                if target.exists():
                    shutil.rmtree(target)
                target.mkdir(parents=True)
                if csv_path:
                    shutil.copy2(csv_path, target / csv_path.name)
                if final_run is not None and final_run.evidence_dir:
                    for item in Path(final_run.evidence_dir).iterdir():
                        if item.is_file():
                            shutil.copy2(item, target / item.name)
                twin_src = Path(temp) / "evidence" / "twin_gate"
                if twin_src.is_dir():
                    dest = self.evidence_root / "twin_gate"
                    dest.mkdir(parents=True, exist_ok=True)
                    for item in twin_src.iterdir():
                        if item.is_file():
                            shutil.copy2(item, dest / item.name)
                evidence_dir = str(target)
            result = ScenarioResult(
                name=self.scenario["name"],
                passed=not failures,
                failures=failures,
                run=run_dict,
                kernel_events=kernel_events,
                invariants=invariants,
                csv_path=str(csv_path) if csv_path else None,
                csv_rows=len(rows),
                rig_log=rig.log,
                evidence_dir=evidence_dir,
                sim_time_s=round(rig.sim_time, 3),
                wall_time_s=round(time.monotonic() - started_wall, 3),
                notes=notes,
            )
            if evidence_dir is not None:
                (Path(evidence_dir) / "scenario_result.json").write_text(
                    json.dumps({**result.to_dict(), "scenario": self.scenario}, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                result.csv_path = str(Path(evidence_dir) / csv_path.name) if csv_path else None
            else:
                result.csv_path = None
            return result

    @staticmethod
    def _judge(
        expect: dict[str, Any],
        run: dict[str, Any] | None,
        events: list[str],
        invariants: dict[str, Any],
        rig: SimulatedRig,
        csv_rows: int,
    ) -> list[str]:
        failures: list[str] = []
        if "outcome" in expect:
            if run is None:
                failures.append("expected a procedure outcome but no procedure ran")
            elif run["status"] != expect["outcome"]:
                failures.append(f"outcome {run['status']} != {expect['outcome']} ({run['outcome_reason']})")
        if "outcome_reason_contains" in expect and run is not None:
            if expect["outcome_reason_contains"] not in run["outcome_reason"]:
                failures.append(
                    f"outcome reason {run['outcome_reason']!r} lacks {expect['outcome_reason_contains']!r}"
                )
        for name in expect.get("kernel_events_include", []):
            if name not in events:
                failures.append(f"kernel event {name} not observed (saw {sorted(set(events))})")
        for name in expect.get("kernel_events_exclude", []):
            if name in events:
                failures.append(f"kernel event {name} observed but excluded")
        if run is not None:
            status = {step["step_id"]: step["status"] for step in run["steps"]}
            for step in expect.get("steps_passed", []):
                if status.get(step) != "passed":
                    failures.append(f"step {step} status {status.get(step)} != passed")
            for step in expect.get("steps_failed", []):
                if status.get(step) != "failed":
                    failures.append(f"step {step} status {status.get(step)} != failed")
        if "final_output_high" in expect and rig.output != expect["final_output_high"]:
            failures.append(f"final output {rig.output} != {expect['final_output_high']}")
        for name, report in invariants.items():
            if not report["passed"]:
                failures.append(f"invariant {name} violated: {report['problems'][:3]}")
        if csv_rows < int(expect.get("min_csv_rows", 0)):
            failures.append(f"csv rows {csv_rows} < {expect['min_csv_rows']}")
        return failures


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")[:60]


def run_scenario_file(path: str | Path, evidence_root: Path | None = None) -> ScenarioResult:
    return ScenarioRunner(load_scenario(path), evidence_root).run()
