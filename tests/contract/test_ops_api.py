from __future__ import annotations

import hashlib
import json
import threading
import zipfile
from pathlib import Path

import pytest

from certarig.edge.client import EdgeApiError, EdgeClient
from certarig.edge.evidence_cli import pull, verify_directory, verify_zip
from tests.support import edge_server, sim_server, wait_until


def _run_relay(operator) -> str:  # type: ignore[no-untyped-def]
    run_id = str(operator.run_procedure("relay_truth_table", "ops-test")["run_id"])
    assert wait_until(lambda: operator.procedure_run(run_id)["terminal"], timeout=30)
    assert operator.procedure_run(run_id)["status"] == "passed"
    return run_id


def test_evidence_listing_and_downloads() -> None:
    with sim_server() as sim:
        operator = sim.operator()
        agent = sim.agent()
        run_id = _run_relay(operator)
        listing = agent.evidence()
        assert listing["rig_id"] == "certarig-wave1-sim"
        assert listing["contract_hash"] == sim.node.contract_hash
        assert [row["run_id"] for row in listing["runs"]] == [run_id]
        assert listing["recording_active"] is False
        assert len(listing["recordings"]) == 1
        csv_row = listing["recordings"][0]
        data = agent.download(csv_row["path"])
        assert hashlib.sha256(data).hexdigest() == csv_row["sha256"]
        assert data.splitlines()[0].startswith(b"sample_index,timestamp_utc")

        files = agent.evidence_run(run_id)["files"]
        names = {row["name"] for row in files}
        assert {"run.json", "procedure.json"} <= names
        run_doc = json.loads(agent.download(next(r["path"] for r in files if r["name"] == "run.json")))
        assert run_doc["run_id"] == run_id and run_doc["status"] == "passed"

        with pytest.raises(EdgeApiError) as exc:
            agent.download(f"/v1/evidence/runs/{run_id}/files/..%2Frun.json")
        assert exc.value.status in {400, 404}
        with pytest.raises(EdgeApiError) as exc:
            agent.evidence_run("nope")
        assert exc.value.status == 404
        with pytest.raises(EdgeApiError) as exc:
            agent.download("/v1/evidence/recordings/.hidden.csv")
        assert exc.value.status == 400
        with pytest.raises(EdgeApiError) as exc:
            agent.download("/v1/evidence/recordings/run.json")
        assert exc.value.status == 404
        # read_evidence is a read tool: anonymous may list (same as the live CSV), never export
        assert EdgeClient(sim.url).evidence()["runs"][0]["run_id"] == run_id
        with pytest.raises(EdgeApiError) as exc:
            EdgeClient(sim.url).request("POST", "/v1/ops/evidence/export", {}, contract=False)
        assert exc.value.status == 401


def test_recorder_stop_respects_active_runs() -> None:
    with sim_server() as sim:
        operator = sim.operator()
        agent = sim.agent()
        assert agent.stop_recorder()["stopped"] is False
        operator.start_recording("manual")
        assert operator.state()["recording"]["active"] is True
        result = agent.stop_recorder()
        assert result["stopped"] is True and result["completed_recording"]["samples"] >= 0
        assert operator.state()["recording"]["active"] is False

        run_id = str(operator.run_procedure("pressure_guardrail", "hold")["run_id"])
        assert wait_until(
            lambda: operator.procedure_run(run_id)["current_step"] == "raise_pressure", timeout=20
        )
        with pytest.raises(EdgeApiError) as exc:
            agent.stop_recorder()
        assert exc.value.status == 409 and exc.value.code == "run_active"
        with pytest.raises(EdgeApiError) as exc:
            operator.shutdown("too early")
        assert exc.value.status == 409 and exc.value.code == "run_active"
        forced = agent.stop_recorder(force=True)
        assert forced["stopped"] is True
        operator.abort(run_id, "test over")
        assert wait_until(lambda: operator.procedure_run(run_id)["terminal"], timeout=10)


def test_export_bundle_is_checksummed_and_pull_verifies_it(tmp_path: Path) -> None:
    with sim_server() as sim:
        operator = sim.operator()
        with pytest.raises(EdgeApiError) as exc:
            operator.export_evidence(run_id="missing")
        assert exc.value.status == 404
        run_id = _run_relay(operator)
        bundle = sim.agent().export_evidence()
        assert bundle["files"] >= 3  # run.json, procedure.json, csv
        archive = sim.agent().download(bundle["path"])
        assert hashlib.sha256(archive).hexdigest() == bundle["sha256"]
        zip_path = tmp_path / bundle["filename"]
        zip_path.write_bytes(archive)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            assert "SHA256SUMS.txt" in names and "export_manifest.json" in names
            manifest = json.loads(zf.read("export_manifest.json"))
            assert manifest["contract_hash"] == sim.node.contract_hash
            assert manifest["run_id"] is None
            assert any(f"procedure_runs/{run_id}/run.json" == row["path"] for row in manifest["files"])
        assert verify_zip(zip_path)["ok"] is True

        # a run-scoped bundle contains only that run
        scoped = operator.export_evidence(run_id=run_id, label="scoped")
        (tmp_path / "scoped.zip").write_bytes(operator.download(scoped["path"]))
        with zipfile.ZipFile(tmp_path / "scoped.zip") as zf:
            assert all(
                n.startswith(f"procedure_runs/{run_id}/") or n in {"SHA256SUMS.txt", "export_manifest.json"}
                for n in zf.namelist()
            )
        # exports show up in the listing but are never re-exported
        listing = operator.evidence()
        assert len(listing["exports"]) == 2
        again = operator.export_evidence()
        assert again["files"] == bundle["files"]

        # pull + verify through the client, then tamper
        result = pull(operator, tmp_path / "pulled")
        assert result["ok"] is True and result["verification"]["mismatched"] == []
        assert result["rig_id"] == "certarig-wave1-sim"
        extracted = Path(result["extracted_to"])
        assert verify_directory(extracted)["ok"] is True
        target = extracted / "procedure_runs" / run_id / "run.json"
        target.write_text(target.read_text().replace('"passed"', '"PASSED"'))
        report = verify_directory(extracted)
        assert report["ok"] is False and report["mismatched"] == [f"procedure_runs/{run_id}/run.json"]
        (extracted / "procedure_runs" / run_id / "procedure.json").unlink()
        assert verify_directory(extracted)["missing"] == [f"procedure_runs/{run_id}/procedure.json"]
        (extracted / "SHA256SUMS.txt").unlink()
        assert verify_directory(extracted)["ok"] is False


def test_shutdown_requires_human_approval_and_leaves_the_rig_safe() -> None:
    with sim_server() as sim:
        operator = sim.operator()
        agent = sim.agent()
        ops = sim.node.extensions["ops"]
        powered_off = threading.Event()
        ops.poweroff = powered_off.set
        ops.shutdown_delay_s = 0.05

        with pytest.raises(EdgeApiError) as exc:
            agent.shutdown("agent wants out")
        assert exc.value.status == 428 and exc.value.code == "approval_required"

        operator.command("reset")
        operator.command("permit")
        assert sim.rig.output is True
        operator.start_recording("last-one")
        approval = agent.request_approval("shutdown", {"reason": "bench work complete"}, "done for today")
        operator.grant(approval["approval_id"])
        result = agent.shutdown("bench work complete", approval_id=approval["approval_id"])
        assert result["status"] == "shutting_down"
        record = result["record"]
        assert [s["step"] for s in record["steps"]] == ["recorder_stopped", "kernel_forced_safe"]
        assert record["steps"][1]["output_high"] is False
        assert record["requested_by"] == {"principal": "agent", "name": "agent-under-test"}
        assert record["approval_id"] == approval["approval_id"]
        assert record["poweroff"] == "scheduled"
        assert sim.rig.output is False
        assert powered_off.wait(5)
        assert wait_until(
            lambda: sim.node.runtime._thread is None or not sim.node.runtime._thread.is_alive(), 5
        )
        health = operator.health()
        assert health["shutting_down"] is True
        assert operator.evidence()["shutdowns"][0]["reason"] == "bench work complete"
        assert list(sim.evidence_dir.glob("shutdown_*.json"))
        # a second call is idempotent
        assert operator.shutdown("again")["status"] == "shutting_down"


def test_shutdown_without_poweroff_command_only_closes_runtime() -> None:
    with edge_server() as edge:
        ops = edge.node.extensions["ops"]
        ops.shutdown_delay_s = 0.05
        result = edge.operator().shutdown("dev box")
        assert result["record"]["poweroff"].startswith("not configured")
        assert wait_until(lambda: edge.rig.closed, 5)
        assert edge.rig.output is False


def test_briefing_round_trip_is_copied_into_a_run_bundle() -> None:
    with sim_server() as sim:
        operator = sim.operator()
        empty = operator.get("/v1/ops/briefing")
        assert empty["present"] is False
        saved = operator.post(
            "/v1/ops/briefing",
            {
                "p1_role": "Pressure emulator P1",
                "p2_role": "Flow emulator P2",
                "estop": "GPIO24",
                "relay": "GPIO23",
                "diagram_notes": "wave-1 dry bench",
            },
        )
        assert saved["present"] is True
        assert saved["briefing"]["p1_role"] == "Pressure emulator P1"
        run_id = _run_relay(operator)
        report = (sim.evidence_dir / "procedure_runs" / run_id / "report.md").read_text()
        assert "Pressure emulator P1" in report
        briefing = json.loads(
            (sim.evidence_dir / "procedure_runs" / run_id / "briefing.json").read_text()
        )
        assert briefing["p2_role"] == "Flow emulator P2"
