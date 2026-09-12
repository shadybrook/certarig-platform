from __future__ import annotations

import json
from pathlib import Path

from certarig.edge.bundle import canonicalize, render_report, write_run_bundle
from certarig.edge.evidence_cli import verify_directory
from certarig.sim.scenario import run_scenario_file
from tests.support import SKILLS_DIR, wait_until
from tests.unit.test_procedure_runner import Harness


def test_write_run_bundle_validates_and_checksums(tmp_path: Path) -> None:
    run = {
        "run_id": "run_x",
        "procedure_id": "relay_truth_table",
        "procedure_hash": "abc",
        "status": "passed",
        "outcome_reason": "ok",
        "steps": [{"step_id": "a", "type": "command", "status": "passed"}],
        "checks": [{"check": "event_observed:permit_accepted", "passed": True}],
        "kernel_events": [{"event": "permit_accepted"}],
        "recovery": "none",
    }
    (tmp_path / "procedure.json").write_text("{}", encoding="utf-8")
    manifest = write_run_bundle(
        tmp_path,
        run,
        {
            "rig_id": "r",
            "hardware_mode": "simulator",
            "config_hash": "c" * 64,
            "manifest_hash": "m" * 64,
            "contract_hash": "k" * 64,
            "title": "Relay",
            "seed": 7,
        },
        narrative="The relay followed the truth table.",
    )
    assert manifest["kind"] == "certarig_run_bundle"
    assert (tmp_path / "report.md").read_text().startswith("# Relay")
    assert "The relay followed the truth table." in (tmp_path / "report.md").read_text()
    assert "Deterministic results" in (tmp_path / "report.md").read_text()
    assert verify_directory(tmp_path)["ok"] is True
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    write_run_bundle(tmp_path, run, {"rig_id": "r", "hardware_mode": "simulator", "title": "Relay"})
    assert verify_directory(tmp_path)["ok"] is True


def test_seeded_scenarios_agree_after_canonicalization(tmp_path: Path) -> None:
    scenario = SKILLS_DIR / "electronics" / "relay_truth_table" / "scenarios" / "happy_path.yaml"
    a = run_scenario_file(scenario, tmp_path / "a")
    b = run_scenario_file(scenario, tmp_path / "b")
    assert a.passed and b.passed
    left = canonicalize(a.run or {})
    right = canonicalize(b.run or {})
    assert left["procedure_id"] == right["procedure_id"]
    assert left["status"] == right["status"]
    assert [s["step_id"] for s in left["steps"]] == [s["step_id"] for s in right["steps"]]
    assert [s["status"] for s in left["steps"]] == [s["status"] for s in right["steps"]]
    assert left["checks"] == right["checks"]
    assert [e["event"] for e in left.get("kernel_events", [])] == [
        e["event"] for e in right.get("kernel_events", [])
    ]


def test_flight_recorder_dumps_on_pressure_trip(tmp_path: Path) -> None:
    harness = Harness(str(tmp_path))
    try:
        harness.runtime.command("reset")
        harness.runtime.command("permit")
        harness.rig.set("pressure_emulator", 5.5)
        assert wait_until(
            lambda: (
                (tmp_path / "evidence" / "flight").is_dir()
                and any(
                    p.name.endswith("pressure_high_forced_safe.json")
                    for p in (tmp_path / "evidence" / "flight").glob("*.json")
                )
            ),
            timeout=5,
        )
        dump = next((tmp_path / "evidence" / "flight").glob("*pressure_high_forced_safe.json"))
        body = json.loads(dump.read_text())
        assert body["kind"] == "certarig_flight_recorder"
        assert body["samples"]
        assert harness.rig.output is False
    finally:
        harness.close()


def test_render_report_labels_narrative() -> None:
    text = render_report(
        {"procedure_id": "p", "run_id": "r", "status": "failed", "steps": [], "checks": []},
        {"title": "P", "rig_id": "x", "hardware_mode": "mock", "config_hash": "0", "contract_hash": "1"},
        narrative="I think the pot stuck.",
    )
    assert "narrative" in text.lower() and "I think the pot stuck." in text
    assert "I think the pot stuck." in text
