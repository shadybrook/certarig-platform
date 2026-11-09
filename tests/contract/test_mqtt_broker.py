"""Observation transport: deterministic callback checks and opt-in local-broker proof."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from certarig.edge.config import load_config_dict
from certarig.edge.hardware.base import HardwareError
from certarig.edge.hardware.mqtt import MqttHardware
from tests.support import CONFIG_DIR, wait_until


def config(port=18883):
    raw = json.loads((CONFIG_DIR / "rig.mqtt.broker.json").read_text())
    raw["hardware"]["mqtt"]["port"] = port
    return raw


class ClientFixture:
    def connect_async(self, *args, **kwargs):
        pass

    def loop_start(self):
        pass

    def subscribe(self, *args, **kwargs):
        pass

    def disconnect(self):
        pass

    def loop_stop(self):
        pass

    def username_pw_set(self, *args):
        pass

    def tls_set(self):
        pass


def test_network_callback_quality_and_no_writes(monkeypatch):
    import paho.mqtt.client as mqtt

    client = ClientFixture()
    monkeypatch.setattr(mqtt, "Client", lambda *a, **kw: client)
    raw = config()
    raw["hardware"]["mqtt"].update(username_env="TEST_MQTT_USER", password_env="TEST_MQTT_PASSWORD", tls=True)
    monkeypatch.setenv("TEST_MQTT_USER", "fixture")
    hw = MqttHardware(load_config_dict(raw))
    assert hw.snapshot().samples[0].quality == "disconnected"
    hw._on_connect(client, None, None, 0, None)
    assert hw.snapshot().samples[0].quality == "missing"
    assert hw.status()["connected"]

    def send(payload, retain=False, topic="rig/pressure"):
        hw._on_message(
            client, None, SimpleNamespace(payload=json.dumps(payload).encode(), topic=topic, retain=retain)
        )

    good = {"value": 1.0, "unit": "bar", "captured_at": datetime.now(UTC).isoformat()}
    send(good)
    assert hw.snapshot().samples[0].quality == "good"
    for value in [
        "wrong",
        [],
        {**good, "value": True},
        {**good, "unit": "psi"},
        {**good, "captured_at": "invalid"},
        {**good, "value": float("nan")},
    ]:
        send(value)
        assert hw.snapshot().samples[0].quality == "malformed"
    send({**good, "value": 200})
    assert hw.snapshot().samples[0].quality == "out_of_range"
    send({**good, "quality": "bad"})
    assert hw.snapshot().samples[0].quality == "bad_source_quality"
    send({**good, "captured_at": (datetime.now(UTC) - timedelta(seconds=5)).isoformat()})
    assert hw.snapshot().samples[0].quality == "stale"
    send(good, True)
    assert hw.snapshot().samples[0].quality == "retained"
    send(good, topic="not/mapped")
    hw.set_valve(False)
    hw.force_safe_state()
    assert hw.bus.commands() == []
    with pytest.raises(HardwareError):
        hw.set_valve(True)
    hw._on_disconnect(client, None, None, 0, None)
    assert hw.snapshot().samples[0].quality == "disconnected"
    hw._on_connect(client, None, None, 1, None)
    assert not hw.status()["connected"]
    hw.close()
    assert hw.closed
    raw["hardware"]["observe_only"] = False
    with pytest.raises(HardwareError):
        MqttHardware(load_config_dict(raw))
    raw = config()
    raw["channels"][0]["source"]["topic"] = "rig/#"
    with pytest.raises(HardwareError):
        MqttHardware(load_config_dict(raw))


@pytest.mark.mqtt_integration
@pytest.mark.skipif(
    not os.environ.get("CERTARIG_MQTT_TEST_PORT"), reason="needs an explicitly selected local broker"
)
def test_real_loopback_broker_observation_and_staleness():
    import paho.mqtt.client as mqtt

    port = int(os.environ["CERTARIG_MQTT_TEST_PORT"])
    hw = MqttHardware(load_config_dict(config(port)))
    publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    publisher.connect("127.0.0.1", port, 10)
    publisher.loop_start()
    try:
        assert wait_until(lambda: hw.connected)

        # Publish until subscription acknowledgement has arrived; no assumed sleeps.
        def observed():
            publisher.publish(
                "rig/pressure",
                json.dumps({"value": 1.0, "unit": "bar", "captured_at": datetime.now(UTC).isoformat()}),
                qos=1,
            ).wait_for_publish()
            return hw.snapshot().samples[0].quality == "good"

        assert wait_until(observed)
        assert hw.snapshot().samples[0].value == 1
        assert wait_until(lambda: hw.snapshot().samples[0].quality == "stale", timeout=3)
        assert hw.bus.commands() == []
        with pytest.raises(HardwareError):
            hw.set_valve(True)
        hw._client.disconnect()
        assert wait_until(lambda: not hw.connected)
        assert hw.snapshot().samples[0].quality == "disconnected"
    finally:
        publisher.disconnect()
        publisher.loop_stop()
        hw.close()
