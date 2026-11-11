"""All hardware/model/provider evidence here is a software fixture, never a bench pass."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from certarig.agent.skills import SkillIndex
from certarig.agent.tools import ToolRegistry
from certarig.edge.atomic import write_json_atomic
from certarig.edge.bootstrap import NodeSettings, build_node
from certarig.edge.client import EdgeApiError, InProcessClient
from certarig.edge.config import ConfigurationError, load_config_dict
from certarig.edge.evidence_cli import verify_directory
from certarig.edge.hardware.mixed import PulseCounter, SourceSampler, shunt_current, w1_temperature
from certarig.edge.live import LiveBenchRuntime
from certarig.edge.physical_review import ACCEPTANCE_CHECKS, checked_file, inspect_evidence
from certarig.edge.recording_analysis import analyze_csv, reproduce_checks
from certarig.edge.revalidation import profile_hash, revalidation
from certarig.edge.twin_gate import check_gate, record_sim_pass
from certarig.sim.plant import SimulatedRig
from tests.support import AGENT_KEY, CONFIG_DIR, OPERATOR_KEY, SKILLS_DIR, ControllableRig, wait_until


def raw_config():
    return json.loads((CONFIG_DIR / "rig.thermal.capstone.json").read_text())


@pytest.fixture
def node_factory(tmp_path):
    nodes = []

    def factory(raw=None, hardware=None):
        root = tmp_path / str(len(nodes))
        root.mkdir()
        path = root / "rig.json"
        write_json_atomic(path, raw or raw_config())
        settings = NodeSettings(
            path,
            CONFIG_DIR / "capabilities.capstone.json",
            root / "evidence",
            None,
            OPERATOR_KEY,
            AGENT_KEY,
            None,
            True,
            SKILLS_DIR,
        )
        node = build_node(settings, hardware)
        node.start()
        nodes.append(node)
        op = InProcessClient(node, operator_key=OPERATOR_KEY, principal_name="reviewer")
        agent = InProcessClient(node, agent_key=AGENT_KEY, principal_name="fixture-agent")
        assert wait_until(lambda: node.runtime.state()["status"] == "ok")
        return node, op, agent

    yield factory
    for node in nodes:
        node.close()


def complete_answers(doc):
    return {
        "equipment": "Documented simulator fixture",
        "safe_state": "deenergized",
        "procedures": ["thermal_soak"]
        if doc["channels"][0]["concept"] == "temperature"
        else ["pressure_guardrail"],
        "document": doc,
        "calibration_records": [
            {
                "calibration_id": c["calibration_id"],
                "reference": "SIMULATION_FIXTURE: known synthetic scaling",
            }
            for c in doc["channels"]
        ],
    }


@pytest.mark.parametrize("template", ["thermal", "pressure_flow"])
def test_resumable_interview_apply_and_provenance(node_factory, template):
    node, op, agent = node_factory()
    value = agent.post("/v1/commissioning/interviews", {})
    base = "/v1/commissioning/interviews/" + value["interview_id"]
    assert agent.post(base + "/propose", {})["status"] == "needs_evidence"
    templates = op.get("/v1/commissioning/templates")["templates"]
    doc = templates[template]
    doc["rig_id"] += "-new"
    answers = complete_answers(doc)
    value = agent.post(
        base + "/answers",
        {
            "expected_revision": 0,
            "answers": answers,
            "sources": {k: "fixture specification" for k in answers},
        },
    )
    with pytest.raises(EdgeApiError):
        agent.post(base + "/answers", {"expected_revision": 0})
    assert op.get(base)["revision"] == 1
    proposed = agent.post(base + "/propose", {})
    assert proposed["status"] == "proposed", proposed
    payload = {
        "document": doc,
        "expected_current_hash": proposed["proposal"]["current_hash"],
        "interview_id": value["interview_id"],
        "interview_revision": 1,
    }
    with pytest.raises(EdgeApiError):
        agent.post("/v1/rig/apply", payload)
    with pytest.raises(EdgeApiError):
        op.post("/v1/rig/apply", {**payload, "interview_revision": 0})
    op.post("/v1/rig/apply", payload)
    op.refresh_contract()
    assert node.config.rig_id == doc["rig_id"]
    evidence = node.extensions["interviews"].evidence()
    assert evidence["interview"]["applied_config_hash"] == node.config.config_hash
    assert evidence["calibration_records"] == answers["calibration_records"]
    assert not op.get("/v1/commissioning")["ready"]
    if template == "thermal":
        op.post(
            "/v1/commissioning/review",
            {"expected_config_hash": node.config.config_hash, "procedure_ids": ["thermal_soak"]},
        )
        approval = op.request_approval("run_procedure", {"procedure_id": "thermal_soak"}, "fixture run")
        op.grant(approval["approval_id"])
        run = op.run_procedure("thermal_soak", approval_id=approval["approval_id"])
        assert wait_until(lambda: op.procedure_run(run["run_id"])["terminal"])
        folder = node.runtime.evidence_dir / "procedure_runs" / run["run_id"]
        verification = verify_directory(folder)
        assert verification["ok"], verification
        assert json.loads((folder / "check_analysis.json").read_text())["consistent"]
        (folder / "interview.json").unlink()
        assert not verify_directory(folder)["ok"]


@pytest.mark.parametrize(
    "bad",
    [
        "sources",
        "units",
        "calibration",
        "identity",
        "safe",
        "procedure",
        "document",
        "unparsed",
        "records",
        "schema",
    ],
)
def test_interview_refusals(node_factory, bad):
    node, op, agent = node_factory()
    iv = op.post("/v1/commissioning/interviews", {})
    base = "/v1/commissioning/interviews/" + iv["interview_id"]
    answers = complete_answers(raw_config())
    sources = {k: "operator record" for k in answers}
    text = ""
    if bad == "sources":
        sources = {}
    if bad == "units":
        answers["document"]["channels"][0]["unit"] = "bar"
    if bad == "calibration":
        answers["calibration_records"] = []
    if bad == "identity":
        answers["document"]["channels"][0].pop("source")
    if bad == "safe":
        answers["safe_state"] = "leave running"
    if bad == "procedure":
        answers["procedures"] = ["arbitrary_shell"]
    if bad == "document":
        answers.pop("document")
    if bad == "unparsed":
        text = "guess all safety limits"
    if bad == "records":
        answers["calibration_records"] = "not a list"
    if bad == "schema":
        answers["document"]["channels"][0]["safe_max"] = -1
    op.post(base + "/answers", {"expected_revision": 0, "answers": answers, "sources": sources, "text": text})
    result = op.post(base + "/propose", {})
    assert result["status"] == "needs_evidence" and result["blockers"] and "proposal" not in result
    assert node.config.rig_id == raw_config()["rig_id"]


def test_interview_tool_text_and_paths(node_factory):
    node, op, agent = node_factory()
    registry = ToolRegistry(agent, SkillIndex([]))
    iv = registry.execute("commissioning_interview", {"action": "create"}).result
    identifier = iv["interview_id"]
    assert registry.execute("commissioning_interview", {"action": "read", "interview_id": identifier}).ok
    result = registry.execute(
        "commissioning_interview",
        {
            "action": "update",
            "interview_id": identifier,
            "expected_revision": 0,
            "text": "equipment: thermal fixture\nsafe_state: deenergized\nprocedures: thermal_soak",
        },
    )
    assert result.ok and result.result["answers"]["procedures"] == ["thermal_soak"]
    assert registry.execute(
        "commissioning_interview", {"action": "propose", "interview_id": identifier}
    ).result["blockers"]
    assert not registry.execute("commissioning_interview", {"action": "apply", "interview_id": identifier}).ok
    for path in ["../config", "iv_0000000000000000"]:
        with pytest.raises(EdgeApiError):
            op.get("/v1/commissioning/interviews/" + path)
    with pytest.raises(EdgeApiError):
        op.post(
            "/v1/commissioning/interviews/" + identifier + "/answers",
            {"expected_revision": 1, "sources": {"bad": ""}},
        )
    assert op.get("/v1/commissioning/interviews")["interviews"]


def test_distinct_thermal_dynamics_and_profile_gate(tmp_path):
    raw = raw_config()
    raw["hardware"]["simulator"]["noise"] = {}
    raw["hardware"]["simulator"]["thermal"].update(initial_c=65, heat_input_w=0)
    cfg = load_config_dict(raw)
    plant = SimulatedRig(cfg)
    initial = 65.0
    snap = plant.snapshot()
    assert snap.samples[0].value == pytest.approx(25 + (initial - 25) * math.exp(-2 * 0.02 / 100), abs=1e-5)
    plant.set_target("temperature", 125)
    for _ in range(3000):
        snap = plant.snapshot()
    assert snap.samples[0].value > 85
    plant.inject("dropout", "temperature")
    assert not plant.snapshot().samples
    plant.clear()
    plant.inject("stuck", "temperature")
    frozen = plant.snapshot().samples[0].value
    assert plant.snapshot().samples[0].value == frozen
    plant.clear()
    plant.set_target("temperature", 45)
    record_sim_pass(tmp_path, "thermal_soak", "abc", "fixture", cfg)
    assert check_gate(tmp_path, "abc", "raspberry_pi", config=cfg) is None
    changed = copy.deepcopy(raw)
    changed["channels"][0]["calibration_id"] = "new-calibration"
    assert (
        check_gate(tmp_path, "abc", "raspberry_pi", config=load_config_dict(changed))["code"]
        == "twin_profile_mismatch"
    )
    changed = copy.deepcopy(raw)
    changed["hardware"]["simulator"]["thermal"]["capacity_j_per_c"] *= 2
    assert profile_hash(cfg) != profile_hash(load_config_dict(changed))
    delta = revalidation(raw, changed)
    assert delta["full_qualification"]
    changed = copy.deepcopy(raw)
    changed["channels"][0]["safe_max"] = 80
    delta = revalidation(raw, changed)
    assert delta["changed_channels"] and not delta["full_qualification"]
    assert not revalidation(raw, raw)["required_checks"]


def test_pulse_zero_crc_shunt_and_cached_io(tmp_path):
    clock = [0.0]
    counter = PulseCounter(600, clock=lambda: clock[0])
    assert counter.read() == (0, 0)
    counter.pulse()
    counter.pulse()
    assert counter.read() == (0.2, 2)
    clock[0] = 1.1
    assert counter.read() == (0, 0)
    with pytest.raises(ValueError):
        PulseCounter(0)
    assert shunt_current([0, 100], 0.1)[0] == pytest.approx(0.01)
    assert shunt_current([255, 156], 0.1)[0] == pytest.approx(-0.01)
    with pytest.raises(ValueError):
        shunt_current([0, 1], 0)
    path = tmp_path / "w1_slave"
    path.write_text("crc YES\na t=22500")
    assert w1_temperature(path) == (22.5, 22500)
    path.write_text("crc NO\na t=22500")
    with pytest.raises(ValueError):
        w1_temperature(path)
    cfg = load_config_dict(raw_config())
    c = cfg.channels[0]
    sampler = SourceSampler(c, lambda: (45.0, 100.0))
    assert sampler.sample().quality == "missing"
    sampler.start()
    assert wait_until(lambda: sampler.sample().quality == "good")
    sampler.close()
    for value in [float("nan"), 200]:
        sampler = SourceSampler(c, lambda v=value: (v, None))
        sampler.acquire()
        assert sampler.sample().quality != "good"
    sampler = SourceSampler(c, lambda: (_ for _ in ()).throw(OSError("bus")))
    sampler.acquire()
    assert sampler.sample().quality == "read_error"
    sampler.close()


class ElectricalFixture(ControllableRig):
    feedback_override = None
    unknown = False

    def snapshot(self):
        return replace(
            super().snapshot(),
            output_feedback=None
            if self.unknown
            else self.output
            if self.feedback_override is None
            else self.feedback_override,
            feedback_source="electrical_gpio",
        )


def physical_config():
    raw = raw_config()
    raw.update(wiring_revision="software-fixture-wiring-v1")
    raw["hardware"].update(
        mode="raspberry_pi", feedback_required=True, relay_feedback_gpio=25, feedback_settle_ms=0
    )
    raw["channels"][0].update(
        adc_channel=0,
        raw_min_v=0.0,
        raw_max_v=3.3,
        engineering_min=0.0,
        engineering_max=120.0,
        source={"kind": "adc"},
    )
    raw["channels"][0].pop("stuck_samples", None)
    raw["channels"][0].pop("stuck_epsilon", None)
    return raw


def test_feedback_mismatch_unknown_and_freshness(tmp_path):
    config = load_config_dict(physical_config())
    hw = ElectricalFixture(config)
    runtime = LiveBenchRuntime(config, hw, tmp_path, allow_output=True)
    try:
        runtime.sample_once()
        runtime.command("reset")
        runtime.command("permit")
        hw.feedback_override = False
        state = runtime.sample_once()
        assert state["guardrail"]["trip_latched"] and not hw.output
        assert state["guardrail"]["reason"] == "output_feedback_mismatch"
        hw.unknown = True
        assert runtime.sample_once()["guardrail"]["reason"] == "output_feedback_unknown"
        snap = hw.snapshot()
        old = (datetime.now(UTC) - timedelta(seconds=3)).isoformat()
        c = replace(config.channels[0], max_age_ms=50)
        from certarig.edge.commissioning import ProcessGuardrail

        guard = ProcessGuardrail(replace(config, channels=(c,)))
        assert not guard.observe(
            replace(snap, samples=(replace(snap.samples[0], captured_at=old),))
        ).process_healthy
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "bad", ["gpio", "calibration", "w1", "current", "poll", "gain", "adc", "feedback", "nan"]
)
def test_mixed_source_validation(bad):
    raw = physical_config()
    ch = raw["channels"][0]
    if bad == "gpio":
        ch["source"] = {"kind": "pulse", "gpio": 23, "pulses_per_litre": 600}
    if bad == "calibration":
        ch["source"] = {"kind": "pulse", "gpio": 17, "pulses_per_litre": 0}
    if bad == "w1":
        ch["source"] = {"kind": "w1", "device_id": "../../private"}
    if bad == "current":
        ch["source"] = {"kind": "ina219", "shunt_ohms": 0.1, "address": 72}
    if bad == "poll":
        ch["source"]["poll_s"] = 0
    if bad == "gain":
        ch["source"]["gain"] = float("inf")
    if bad == "adc":
        ch["raw_max_v"] = 4.5
    if bad == "feedback":
        raw["hardware"]["relay_feedback_gpio"] = None
    if bad == "nan":
        ch["safe_max"] = float("nan")
    with pytest.raises(ConfigurationError):
        load_config_dict(raw)


def qualification_files(node):
    checks = {}
    root = node.runtime.evidence_dir
    raw = root / "raw-session.txt"
    raw.write_text("SOFTWARE FIXTURE - not physical evidence")
    ref = {"path": raw.name, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
    for key in ACCEPTANCE_CHECKS:
        path = root / f"{key}.json"
        write_json_atomic(
            path,
            {
                "check": key,
                "passed": True,
                "evidence_kind": "physical",
                "config_hash": node.config.config_hash,
                "wiring_revision": node.config.wiring_revision,
                "artifacts": [ref],
            },
        )
        checks[key] = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return checks


def test_staged_physical_review_is_operator_bound_and_evidence_bound(node_factory):
    raw = physical_config()
    hw = ElectricalFixture(load_config_dict(raw))
    node, op, agent = node_factory(raw, hw)
    checks = qualification_files(node)
    service = node.extensions["commissioning"]
    payload = {
        "stage": "observation",
        "expected_config_hash": node.config.config_hash,
        "wiring_revision": node.config.wiring_revision,
        "attest_reviewed": True,
        "procedure_ids": ["thermal_soak"],
        "checks": checks,
    }
    assert not op.get("/v1/commissioning")["ready"]
    with pytest.raises(EdgeApiError):
        op.post("/v1/commissioning/review", payload)
    with pytest.raises(EdgeApiError):
        agent.post("/v1/commissioning/physical", payload)
    assert op.post("/v1/commissioning/physical", payload)["status"] == "observation_ready"
    proc = node.extensions["procedures"].library.get("thermal_soak")
    record_sim_pass(node.runtime.evidence_dir, proc.id, proc.procedure_hash, "fixture-sim", node.config)
    assert op.post("/v1/commissioning/physical", {**payload, "stage": "trial"})["status"] == "trial_ready"
    with pytest.raises(EdgeApiError):
        op.command("permit")
    with pytest.raises(EdgeApiError):
        op.post("/v1/commissioning/physical", {**payload, "stage": "accepted"})
    approval = op.request_approval("run_procedure", {"procedure_id": "thermal_soak"}, "software fixture")
    op.grant(approval["approval_id"])
    run = op.run_procedure("thermal_soak", approval_id=approval["approval_id"])
    assert wait_until(lambda: op.procedure_run(run["run_id"])["terminal"])
    assert op.procedure_run(run["run_id"])["status"] == "passed"
    assert op.post("/v1/commissioning/physical", {**payload, "stage": "accepted"})["physical_commissioned"]
    folder = node.runtime.evidence_dir / "procedure_runs" / run["run_id"]
    assert verify_directory(folder)["ok"]
    (node.runtime.evidence_dir / "raw-session.txt").write_text("changed")
    assert not service.readiness("thermal_soak")["ready"]
    # Portable historical bundle retains the original review artifacts.
    assert verify_directory(folder)["ok"]


def test_qualification_refusals_and_expired_trial(node_factory, tmp_path):
    raw = physical_config()
    node, op, _ = node_factory(raw, ElectricalFixture(load_config_dict(raw)))
    checks = qualification_files(node)
    with pytest.raises(ValueError):
        checked_file(node.runtime.evidence_dir, {"path": "../outside", "sha256": "x"})
    with pytest.raises(ValueError):
        inspect_evidence(
            node.runtime.evidence_dir, {}, node.config.config_hash, node.config.wiring_revision, "trial"
        )
    with pytest.raises(ValueError):
        inspect_evidence(node.runtime.evidence_dir, checks, "wrong", node.config.wiring_revision, "trial")
    payload = {
        "stage": "trial",
        "expected_config_hash": node.config.config_hash,
        "wiring_revision": node.config.wiring_revision,
        "attest_reviewed": True,
        "procedure_ids": ["thermal_soak"],
        "checks": checks,
    }
    for update in [
        {"stage": "bad"},
        {"attest_reviewed": False},
        {"expected_config_hash": "old"},
        {"procedure_ids": []},
        {},
    ]:
        with pytest.raises(EdgeApiError):
            op.post("/v1/commissioning/physical", {**payload, **update})
    proc = node.extensions["procedures"].library.get("thermal_soak")
    record_sim_pass(node.runtime.evidence_dir, proc.id, proc.procedure_hash, "fixture", node.config)
    op.post("/v1/commissioning/physical", payload)
    service = node.extensions["commissioning"]
    service.session_id = "new-boot"
    assert not service.readiness("thermal_soak")["ready"]


def test_offline_check_reproduction():
    config = raw_config()
    data = b"jacket_c_value,record_kind,output_feedback,elapsed_s\n45,sample,false,0\n46,sample,true,0.1\n"
    run = {
        "events": [{"kind": "step_passed", "step": "soak"}],
        "kernel_events": [{"event": "safe"}],
        "checks": [
            {"check": {"signal": "temperature", "peak_below": 85}, "passed": True},
            {"check": {"step_passed": "soak"}, "passed": True},
            {"check": {"event_observed": "safe"}, "passed": True},
            {"check": {"event_not_observed": "bad"}, "passed": True},
            {"check": {"step": "soak", "max_elapsed_ms": 20}, "passed": True},
        ],
    }
    result = reproduce_checks(data, config, run)
    assert result["consistent"]
    assert result["checks"][-1]["source"] == "not_independently_reproduced"
    assert analyze_csv(data, config)["feedback_transition_intervals_s"]
    run["checks"][0]["passed"] = False
    assert not reproduce_checks(data, config, run)["consistent"]


def test_model_revision_tamper_and_undeclared_output_steps(tmp_path):
    from certarig.edge.runtime.library import _semantic_errors
    cfg = load_config_dict(raw_config())
    path = record_sim_pass(tmp_path, "thermal_soak", "hash", "run", cfg)
    record = json.loads(path.read_text())
    record["model_revision"] = "unqualified-model"
    write_json_atomic(path, record)
    assert check_gate(tmp_path, "hash", "raspberry_pi", config=cfg)["code"] == "twin_profile_mismatch"
    errors = _semantic_errors({"steps": [{"id": "hidden-permit", "type": "command", "command": "permit"}], "requires_output": False}, cfg)
    assert any("requires_output" in error for error in errors)
