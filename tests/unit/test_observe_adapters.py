"""MQTT / Modbus in-process fakes. No broker or PLC required."""

from __future__ import annotations

import pytest

from certarig.edge.config import load_config
from certarig.edge.hardware.base import HardwareError
from certarig.edge.hardware.bus import TagBus
from certarig.edge.hardware.modbus import ModbusHardware
from certarig.edge.hardware.mqtt import MqttHardware
from certarig.edge.ledger import append_outcome, read_outcomes
from certarig.edge.watchdog import start_watchdog
from tests.support import CONFIG_DIR


def test_mqtt_observe_refuses_to_open_the_valve() -> None:
    config = load_config(CONFIG_DIR / "rig.mqtt.json")
    bus = TagBus()
    hw = MqttHardware(config, bus)
    snap = hw.snapshot()
    assert snap.samples
    hw.set_valve(False)
    with pytest.raises(HardwareError, match="observe_only"):
        hw.set_valve(True)
    hw.close()
    assert hw.output_is_safe()


def test_modbus_reads_registers_from_the_bus() -> None:
    config = load_config(CONFIG_DIR / "rig.modbus.json")
    hw = ModbusHardware(config)
    hw.bus.set("hr/40001", 2.5)
    snap = hw.snapshot()
    pressure = next(s for s in snap.samples if s.channel_id == "pressure_emulator")
    assert pressure.value == 2.5
    with pytest.raises(HardwareError, match="observe_only"):
        hw.set_valve(True)


def test_ledger_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    append_outcome(tmp_path, {"procedure_id": "thermal_soak", "status": "passed"})
    rows = read_outcomes(tmp_path, "thermal_soak")
    assert rows[-1]["status"] == "passed"


def test_watchdog_is_inert_without_notify_socket() -> None:
    assert start_watchdog() is None
