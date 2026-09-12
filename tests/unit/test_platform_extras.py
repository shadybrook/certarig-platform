"""Coverage for watchdog, SDK, PlantOnBus, capabilities apply, and leftover templates."""

from __future__ import annotations

from pathlib import Path

from certarig.edge.authoring_templates import build_procedure
from certarig.edge.bootflag import detect_unclean, mark_clean, mark_running, unclean
from certarig.edge.bootstrap import build_hardware
from certarig.edge.config import load_config
from certarig.edge.configurator import apply_capabilities, propose_capabilities
from certarig.edge.hardware.modbus import ModbusHardware
from certarig.edge.hardware.mqtt import MqttHardware
from certarig.edge.watchdog import notify, start_watchdog
from certarig.sdk import CertaRig
from certarig.sim.bus_twin import PlantOnBus
from certarig.sim.plant import SimulatedRig
from tests.support import CONFIG_DIR, OPERATOR_KEY, edge_server, wait_until


def test_watchdog_notify_is_best_effort() -> None:
    notify("READY=1")
    assert start_watchdog() is None


def test_boot_flag_unclean_after_start_without_close(tmp_path: Path) -> None:
    assert detect_unclean(tmp_path) is False
    mark_clean(tmp_path)
    assert unclean(tmp_path) is False
    assert mark_running(tmp_path) is False
    assert detect_unclean(tmp_path) is True


def test_build_hardware_observe_adapters() -> None:
    mqtt = build_hardware(load_config(CONFIG_DIR / "rig.mqtt.json"))
    modbus = build_hardware(load_config(CONFIG_DIR / "rig.modbus.json"))
    assert isinstance(mqtt, MqttHardware)
    assert isinstance(modbus, ModbusHardware)
    mqtt.close()
    modbus.close()


def test_plant_on_bus_forwards_operator_actions() -> None:
    config = load_config(CONFIG_DIR / "rig.mqtt.json")
    plant = SimulatedRig(config)
    adapter = MqttHardware(config)
    twin = PlantOnBus(plant, adapter)
    twin.set_target("pressure", 2.0)
    twin.ramp("flow", 4.0, 0.1)
    twin.press_estop(True)
    snap = twin.snapshot()
    assert snap.emergency_stop_active
    twin.inject("dropout", "pressure")
    twin.clear("dropout", "pressure")
    twin.set_valve(False)
    assert twin.output_is_safe()
    twin.output = False
    assert twin.sim_time >= 0
    assert isinstance(twin.log, list)
    twin.close()


def test_apply_capabilities_rewrites_the_file(tmp_path: Path) -> None:
    raw = {
        "manifest_id": "tiny",
        "revision": "1",
        "tools": {"read_state": {"policy": "allowed"}, "force_safe": {"policy": "allowed"}},
    }
    path = tmp_path / "caps.json"
    preview = propose_capabilities(raw, {"revision": "2", "tools": raw["tools"], "manifest_id": "tiny"})
    applied = apply_capabilities(path, raw, preview["document"], preview["current_hash"])
    assert applied["next_hash"]
    assert path.is_file()


def test_remaining_authoring_templates_validate() -> None:
    assert build_procedure("guardrail_trip", signal="pressure")["id"] == "pressure_guardrail"
    assert build_procedure("truth_table")["id"] == "output_truth_table"
    assert build_procedure("anomaly_snapshot")["steps"][0]["type"] == "wait"


def test_sdk_run_and_pull_evidence(tmp_path: Path) -> None:
    with edge_server(start_loop=True) as edge:
        sdk = CertaRig(edge.url, OPERATOR_KEY)
        run = sdk.run("relay_truth_table")
        wait_until(lambda: sdk.client.procedure_run(run["run_id"])["terminal"], timeout=20)
        export = sdk.pull_evidence(tmp_path)
        assert Path(export["saved_to"]).is_file()
