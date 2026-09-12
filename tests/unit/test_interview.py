from __future__ import annotations

import json
from pathlib import Path

from certarig.edge.bundle import render_report, write_run_bundle
from certarig.edge.configurator import propose_rig
from certarig.edge.interview import (
    acknowledge_auto_arm,
    answer_interview,
    attach_interview_image,
    attach_proposal,
    extract_facts,
    parse_signals,
    proposed_document,
    read_interview,
    start_interview,
)
from tests.support import CONFIG_DIR, sim_server


def test_parse_signals_from_plain_text() -> None:
    rows = parse_signals("jacket_c temperature 80 degC, pressure 4.2 bar")
    assert rows[0]["concept"] == "temperature" and rows[0]["trip"] == 80.0
    assert rows[1]["concept"] == "pressure" and rows[1]["unit"] == "bar"


def test_read_empty_and_parse_edge_cases(tmp_path: Path) -> None:
    assert read_interview(tmp_path)["present"] is False
    assert parse_signals("", [{"concept": "pressure", "trip": 1}])[0]["concept"] == "pressure"
    assert parse_signals("[1, 2]") == []
    assert parse_signals('{"signals": [{"concept": "pressure", "trip": "nope"}]}')[0]["trip"] is None
    filled = extract_facts("", {"modules": "relay only", "observe_only": "none", "diagram": "notes"})
    assert filled["modules"] == "relay only"
    denied = extract_facts("no mqtt and no modbus, just pots")
    assert "MQTT" not in denied.get("modules", "")


def test_one_dump_can_fill_every_required_slot() -> None:
    facts = extract_facts(
        "ADC pots, E-stop, relay. jacket_c temperature 80 degC. observe-only: none. thermal-jacket.md"
    )
    assert "E-stop" in facts["modules"]
    assert facts["signals"][0]["concept"] == "temperature"
    assert facts["observe_only"] == "none"
    assert "thermal-jacket.md" in facts["diagram"]


def test_interview_round_trip_and_bundle(tmp_path: Path) -> None:
    started = start_interview(tmp_path)
    assert started["status"] == "in_progress"
    assert "modules" in started["missing"]
    done = answer_interview(
        tmp_path,
        {
            "text": "temperature jacket, E-stop. jacket_c temperature 80 degC. none. thermal-jacket.md",
            "signals": [
                {"customer_name": "jacket_c", "concept": "temperature", "unit": "degC", "trip": 80}
            ],
        },
    )
    assert done["status"] == "complete"
    assert done["missing"] == []
    loaded = read_interview(tmp_path)
    assert loaded["answers"]["diagram"] == "thermal-jacket.md"
    raw = json.loads((CONFIG_DIR / "rig.thermal.sim.json").read_text())
    proposed = proposed_document(raw, loaded)
    assert proposed["abort_limits"]["temperature"] == 80.0
    assert proposed["channels"][0]["safe_max"] == 80.0
    run_dir = tmp_path / "procedure_runs" / "run_i"
    run_dir.mkdir(parents=True)
    write_run_bundle(
        run_dir,
        {
            "run_id": "run_i",
            "procedure_id": "thermal_soak",
            "procedure_hash": "abc",
            "status": "passed",
            "steps": [],
            "checks": [],
            "kernel_events": [],
        },
        {
            "rig_id": "r",
            "hardware_mode": "simulator",
            "config_hash": "c" * 64,
            "manifest_hash": "m" * 64,
            "contract_hash": "k" * 64,
            "title": "Thermal",
            "evidence_root": str(tmp_path),
        },
    )
    assert (run_dir / "interview.json").is_file()
    assert "jacket_c temperature" in (run_dir / "report.md").read_text()


def test_render_report_mentions_missing_interview() -> None:
    text = render_report(
        {"procedure_id": "p", "run_id": "r", "status": "passed", "steps": [], "checks": []},
        {"title": "P", "rig_id": "x", "hardware_mode": "mock", "config_hash": "0", "contract_hash": "1"},
    )
    assert "No commissioning interview was saved" in text


def test_extract_and_propose_cover_observe_and_new_channel() -> None:
    mqtt = extract_facts("MQTT and Modbus sit beside the dashboard. observe everything.")
    assert "MQTT" in mqtt["modules"]
    assert "observe" in mqtt["observe_only"].lower()
    json_signals = parse_signals(
        json.dumps({"signals": [{"customer_name": "tank", "concept": "pressure", "unit": "bar", "trip": 3.5}]})
    )
    assert json_signals[0]["customer_name"] == "tank"
    listed = parse_signals(json.dumps([{"concept": "flow", "trip": 12, "unit": "L/min"}]))
    assert listed[0]["concept"] == "flow"
    as_built = extract_facts("as-built wiring on the cart, no file")
    assert "as-built" in as_built["diagram"]
    raw = json.loads((CONFIG_DIR / "rig.thermal.sim.json").read_text())
    interview = {
        "status": "complete",
        "answers": {"observe_only": "MQTT stays observe-only", "signals": ""},
        "signals": [{"customer_name": "extra_flow", "concept": "flow", "unit": "L/min", "trip": 12}],
    }
    proposed = proposed_document(raw, interview)
    extra = next(channel for channel in proposed["channels"] if channel["channel_id"] == "extra_flow")
    assert extra.get("calibration_id") == "UNCAL-extra_flow"
    assert proposed["hardware"]["observe_only"] is True
    assert proposed["abort_limits"]["flow"] == 12.0
    from_text = proposed_document(
        raw,
        {"answers": {"signals": "jacket_c temperature 77 degC", "observe_only": "none"}, "signals": []},
    )
    assert from_text["abort_limits"]["temperature"] == 77.0


def test_proposed_document_matches_sim_channels_without_explicit_concept() -> None:
    raw = json.loads((CONFIG_DIR / "rig.sim.json").read_text())
    interview = {
        "status": "complete",
        "answers": {"observe_only": "none", "signals": "pressure 4.05 bar, flow 14.5 L/min"},
        "signals": [
            {"concept": "pressure", "unit": "bar", "trip": 4.05},
            {"concept": "flow", "unit": "L/min", "trip": 14.5},
        ],
    }
    proposed = proposed_document(raw, interview)
    ids = [channel["channel_id"] for channel in proposed["channels"]]
    assert ids == ["pressure_emulator", "flow_emulator"]
    assert proposed["abort_limits"]["pressure"] == 4.05
    assert proposed["channels"][0]["safe_max"] == 4.05
    preview = propose_rig(raw, proposed)
    assert preview["next_hash"]
    assert any("abort_limits" in row or "safe_max" in row or "channels" in row for row in preview["diff"])


def test_attach_interview_image_fills_diagram_slot(tmp_path: Path) -> None:
    import base64

    png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"fake-bench-photo").decode("ascii")
    saved = attach_interview_image(
        tmp_path, filename="bench.png", content_base64=png, media_type="image/png"
    )
    assert saved["answers"]["diagram"].startswith("interview-images/")
    assert saved["images"][0]["bytes"] > 0
    stored = tmp_path / saved["images"][0]["path"]
    assert stored.is_file()


def test_auto_arm_refuses_without_proposal_and_never_sets_valve(tmp_path: Path) -> None:
    start_interview(tmp_path)
    try:
        acknowledge_auto_arm(
            tmp_path,
            acknowledgement="I applied the map and understand the kernel owns output",
            operator="lab",
            allow_output=True,
            hardware_mode="simulator",
        )
    except RuntimeError as exc:
        assert "proposed map" in str(exc)
    else:
        raise AssertionError("auto-arm must refuse before propose")
    answer_interview(
        tmp_path,
        {
            "text": "ADC pots, E-stop, relay. pressure 4.05 bar. observe-only: none.",
            "modules": "ADC/pots, E-stop, relay",
            "observe_only": "none",
            "signals": [{"concept": "pressure", "unit": "bar", "trip": 4.05}],
        },
    )
    attach_proposal(tmp_path, {"diff": [], "next_hash": "n", "current_hash": "c", "restart_required": False})
    stamped = acknowledge_auto_arm(
        tmp_path,
        acknowledgement="I applied the map and understand the kernel owns output",
        operator="lab",
        allow_output=True,
        hardware_mode="simulator",
    )
    assert stamped["auto_arm"]["set_valve"] is False
    assert stamped["auto_arm"]["may_request_permit"] is True


def test_attach_proposal_persists(tmp_path: Path) -> None:
    start_interview(tmp_path)
    saved = attach_proposal(
        tmp_path,
        {"diff": ["~ abort_limits.temperature"], "next_hash": "n", "current_hash": "c", "restart_required": False},
    )
    assert saved["proposed"]["next_hash"] == "n"


def test_interview_on_thermal_sim_proposes_and_applies_trip() -> None:
    with sim_server(config_name="rig.thermal.sim.json") as sim:
        operator = sim.operator()
        started = operator.post("/v1/ops/interview/start", {})
        assert "signals" in started["missing"]
        complete = operator.post(
            "/v1/ops/interview/answer",
            {
                "text": "temperature jacket, E-stop, no MQTT. jacket_c temperature 80 degC. none. second-plant.md",
                "signals": [
                    {"customer_name": "jacket_c", "concept": "temperature", "unit": "degC", "trip": 80}
                ],
            },
        )
        assert complete["status"] == "complete"
        assert complete["missing"] == []
        preview = operator.post("/v1/ops/interview/propose", {})
        assert preview["restart_required"] is False
        assert preview["document"]["abort_limits"]["temperature"] == 80.0
        applied = operator.post(
            "/v1/rig/apply",
            {"document": preview["document"], "expected_current_hash": preview["current_hash"]},
        )
        assert applied["next_hash"] == sim.node.config.config_hash
        assert sim.node.config.abort_limits["temperature"] == 80.0
        assert (sim.evidence_dir / "interview.json").is_file()
