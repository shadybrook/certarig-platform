"""Actual local TCP/PTY-style transport contracts, without equipment control."""

import json
import socket
import struct
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from certarig.connectors.modbus import ModbusSource
from certarig.connectors.observation import checked_sample
from certarig.connectors.serial import SerialSource
from certarig.edge.config import load_config_dict
from certarig.edge.hardware.base import HardwareError
from certarig.edge.hardware.modbus import ModbusHardware
from certarig.edge.hardware.observation import ObservationHardware


def sample(value=0):
    return {
        "channel_id": "temperature",
        "value": value,
        "unit": "degC",
        "captured_at": datetime.now(UTC).isoformat(),
        "quality": "good",
    }


def test_zero_freshness_and_invalid_identity_units_timestamps():
    assert checked_sample(sample(), expected_unit="degC")["value"] == 0
    old = {**sample(), "captured_at": (datetime.now(UTC) - timedelta(seconds=5)).isoformat()}
    assert checked_sample(old, expected_unit="degC")["quality"] == "stale"
    for change in (
        {"value": True},
        {"value": float("nan")},
        {"unit": "bar"},
        {"channel_id": ""},
        {"captured_at": "2026-01-01"},
        {"captured_at": (datetime.now(UTC) + timedelta(seconds=5)).isoformat()},
        {"quality": "guessed"},
    ):
        with pytest.raises(ValueError):
            checked_sample({**sample(), **change}, expected_unit="degC")


class Port:
    def __init__(self, **kwargs):
        self.settings = kwargs
        self.chunks = []
        self.closed = False

    def open(self):
        assert self.dtr is False and self.rts is False
        assert self.settings["port"] is None

    def read(self, maximum):
        time.sleep(0.005)
        return self.chunks.pop(0) if self.chunks else b""

    def close(self):
        self.closed = True

    def write(self, data):
        pytest.fail("Serial adapter must not write application bytes")


def test_serial_bounded_stream_unknown_output_and_no_writes():
    source = SerialSource(
        {"port": "/dev/test", "baudrate": 115200, "max_age_s": 1}, {"temperature": "degC"}, Port
    )
    try:
        source.ingest(json.dumps(sample()).encode() + b"\n")
        assert source.read()[0]["value"] == 0
        source.ingest(b"invalid\n")
        assert not source.read() and source.status()["quality"] == "malformed"
        source.ingest(json.dumps({**sample(), "unit": "bar"}).encode() + b"\n")
        assert not source.read()
        source.port.chunks = [b"x" * 512] * 9 + [b"\n", json.dumps(sample(12)).encode() + b"\n"]
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and not source.read():
            time.sleep(0.01)
        assert source.read()[0]["value"] == 12
        config = load_config_dict(json.loads(Path("config/rig.thermal.sim.json").read_text()))
        from dataclasses import replace

        config = replace(config, hardware=replace(config.hardware, observe_only=True))
        wrapper = ObservationHardware(config, source)
        assert not wrapper.snapshot().output_safe
        assert not wrapper.output_is_safe()
        assert wrapper.status()["application_bytes_sent"] == 0
        with pytest.raises(HardwareError):
            wrapper.set_valve(False)
        wrapper.force_safe_state()
    finally:
        source.close()
    assert source.port.closed and not source.status()["connected"]


@pytest.mark.parametrize(
    "settings",
    [
        {"port": "socket://host:1"},
        {"port": "/dev/test", "baudrate": 123},
        {"port": "/dev/test", "timeout_s": 10},
    ],
)
def test_serial_refuses_arbitrary_endpoints_and_unbounded_settings(settings):
    with pytest.raises(ValueError):
        SerialSource(settings, {"temperature": "degC"}, Port)


def local_modbus(function=3, data=b"\x00\x7b", corrupt=False):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    calls = []

    def serve():
        try:
            with listener.accept()[0] as conn:
                request = bytearray()
                while len(request) < 12:
                    request.extend(conn.recv(12 - len(request)))
                tid, protocol, size, unit, code, address, count = struct.unpack(">HHHBBHH", request)
                calls.append((code, address, count))
                assert code in {3, 4} and code == function
                body = bytes([code, len(data)]) + data
                reply = struct.pack(">HHHB", tid + (1 if corrupt else 0), 0, len(body) + 1, unit) + body
                # Deliberately fragmented TCP reply.
                conn.sendall(reply[:4])
                conn.sendall(reply[4:])
        finally:
            listener.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return port, calls, thread


@pytest.mark.parametrize("function", [3, 4])
def test_real_modbus_tcp_reads_only_and_handles_partial_frames(function):
    port, calls, thread = local_modbus(function)
    source = ModbusSource(
        {"host": "127.0.0.1", "port": port},
        [
            {
                "channel_id": "temperature",
                "unit": "degC",
                "source": {"register": 10, "function": function, "gain": 0.1},
            }
        ],
    )
    values = source.read()
    thread.join(timeout=1)
    assert values[0]["value"] == pytest.approx(12.3)
    assert calls == [(function, 10, 1)]
    assert source.status()["remote_output_state"] == "unknown"
    assert values[0]["timestamp_origin"] == "gateway_acquisition_not_device"
    assert source.read() == [] and not source.status()["connected"]
    source.close()
    assert source.read() == []


def test_modbus_rejects_wrong_transaction_and_write_functions():
    port, calls, thread = local_modbus(corrupt=True)
    source = ModbusSource(
        {"host": "127.0.0.1", "port": port}, [{"channel_id": "t", "unit": "degC", "source": {"register": 0}}]
    )
    assert source.read() == []
    thread.join(timeout=1)
    for change in (
        {"function": 6},
        {"data_type": "script"},
        {"register": -1},
        {"gain": float("nan")},
        {"byte_order": "guess"},
    ):
        with pytest.raises(ValueError):
            ModbusSource(
                {"host": "127.0.0.1"},
                [{"channel_id": "t", "unit": "degC", "source": {"register": 0, **change}}],
            )


def test_network_modbus_edge_wrapper_preserves_fixture_mode():
    from dataclasses import replace

    cfg = load_config_dict(json.loads(Path("config/rig.thermal.sim.json").read_text()))
    with pytest.raises(HardwareError):
        ObservationHardware(cfg, None)
    port, calls, thread = local_modbus()
    channel = replace(cfg.channels[0], source={"register": 0})
    cfg = replace(
        cfg,
        channels=(channel,),
        hardware=replace(
            cfg.hardware, mode="modbus_tcp", observe_only=True, modbus={"host": "127.0.0.1", "port": port}
        ),
    )
    adapter = ModbusHardware(cfg)
    assert adapter.snapshot().samples[0].value == 123
    thread.join(timeout=1)
    assert not adapter.output_is_safe() and not adapter.status()["remote_output_state"] == "safe"
    with pytest.raises(HardwareError):
        adapter.set_valve(True)
    adapter.force_safe_state()
    adapter.close()


def test_mqtt_shared_source_contract_preserves_existing_adapter():
    from dataclasses import replace

    from certarig.connectors.mqtt import MqttSource

    cfg = load_config_dict(json.loads(Path("config/rig.mqtt.json").read_text()))
    cfg = replace(cfg, hardware=replace(cfg.hardware, observe_only=True))
    source = MqttSource(cfg)
    assert source.read()[0]["quality"] == "good"
    assert source.status()["remote_output_state"] == "unknown"
    source.close()
    with pytest.raises(ValueError):
        MqttSource(replace(cfg, hardware=replace(cfg.hardware, observe_only=False)))
