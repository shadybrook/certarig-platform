from __future__ import annotations

from pathlib import Path

from certarig.edge.briefing import read_briefing, write_briefing
from certarig.edge.bundle import render_report, write_run_bundle


def test_briefing_write_and_read_round_trip(tmp_path: Path) -> None:
    assert read_briefing(tmp_path)["present"] is False
    saved = write_briefing(
        tmp_path,
        {
            "p1_role": "P1 pressure",
            "p2_role": "P2 flow",
            "estop": "mushroom",
            "relay": "permit",
            "diagram_notes": "as-built.svg",
            "ignored": "drop me",
        },
    )
    assert saved["present"] is True
    loaded = read_briefing(tmp_path)
    assert loaded["briefing"]["diagram_notes"] == "as-built.svg"
    assert "ignored" not in loaded["briefing"]


def test_bundle_embeds_briefing_json(tmp_path: Path) -> None:
    write_briefing(tmp_path, {"p1_role": "P1", "p2_role": "P2"})
    run_dir = tmp_path / "procedure_runs" / "run_b"
    run_dir.mkdir(parents=True)
    run = {
        "run_id": "run_b",
        "procedure_id": "relay_truth_table",
        "procedure_hash": "abc",
        "status": "passed",
        "steps": [],
        "checks": [],
        "kernel_events": [],
    }
    write_run_bundle(
        run_dir,
        run,
        {
            "rig_id": "r",
            "hardware_mode": "simulator",
            "config_hash": "c" * 64,
            "manifest_hash": "m" * 64,
            "contract_hash": "k" * 64,
            "title": "Relay",
            "evidence_root": str(tmp_path),
        },
    )
    text = (run_dir / "report.md").read_text()
    assert "P1" in text and "Bench briefing" in text
    assert (run_dir / "briefing.json").is_file()


def test_render_report_mentions_missing_briefing() -> None:
    text = render_report(
        {"procedure_id": "p", "run_id": "r", "status": "passed", "steps": [], "checks": []},
        {"title": "P", "rig_id": "x", "hardware_mode": "mock", "config_hash": "0", "contract_hash": "1"},
    )
    assert "No bench briefing was saved" in text
