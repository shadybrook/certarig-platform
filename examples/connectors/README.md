# Observation connector SDK

Implement the `ObservationSource` protocol: `read()` returns bounded timestamped measurements, `status()` reports connection/quality plus `remote_output_state: unknown`, and `close()` releases resources. `ObservationHardware` adapts this contract into Edge snapshots; it has no equipment-command interface and cannot assert a safe remote output.

Included implementations: `MqttSource` (facade over existing Paho adapter), `SerialSource` (receive-only JSON lines) and `ModbusSource` (actual TCP register reads). There is no network/device discovery or agent-installed plugin loader.

## Operator enrollment

Install optional dependencies on the Edge host, review its configuration and start the Edge manually. Register its **loopback Edge API URL**, auditor credential, organization, exact `mode` and `observation_only: true` in the private platform connector settings. Physical protocol endpoints remain behind that Edge. Pair/enroll through the existing Reviewer flow. The reported profile must also have `observe_only: true` and match the registered mode.

Install reviewed mapping proposals manually with the existing configuration review/application workflow. Review any resulting profile change and repeat agent/team evaluation before deployment. This enables observation; it does not accept physical commissioning or permit actuation.

## MQTT

Use `config/rig.mqtt.broker.json`. Configure exact, unique topics, units and timezone-aware `captured_at` values. Retained, malformed, disconnected or stale sources cannot become good measurements. The network adapter never publishes control commands. Environment-referenced credentials stay server-side.

## Serial JSON lines

Use `config/rig.serial.observe.json`, install `certarig[serial]`, and replace `/dev/REVIEWED_SERIAL_DEVICE` only after identifying the device. Supported rates: 9600, 19200, 38400, 57600, 115200. The read timeout is at most 250 ms; each frame is bounded to 4096 bytes. Each line carries one signal:

```json
{"channel_id":"jacket_c","value":25.2,"unit":"degC","captured_at":"2026-11-14T12:00:00+05:30","quality":"good"}
```

Values are already in the declared engineering units. The firmware owns raw conversion and must be calibrated independently. The SDK sends no application bytes, disables flow control and requests inactive DTR/RTS before opening. Operating systems/drivers can still pulse those lines on open, so no physical safe-start claim is made. Keep actuator power disconnected until wiring and startup behaviour are reviewed. See [pySerial's documented control-line behaviour](https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial.open).

`serial_producer.py` emits synthetic timestamped JSON lines to stdout for inspection/pipe-based fixtures. It does not open hardware.

## Modbus TCP

Use `config/rig.modbus.observe.json`. Register addresses are **zero-based wire addresses**, not printed 40001-style reference numbers. Configure each source's function (`3` holding registers or `4` input registers), `device_id` (1–247), `data_type` (`uint16`, `int16`, `uint32`, `int32`, `float32`), byte/word order, finite gain and offset.

The SDK bounds channel count to 16, validates transaction/protocol/unit/function/length, handles fragmented TCP replies, polls within a two-second overall deadline and refuses every write function. A Modbus timestamp is gateway acquisition time, not a device clock or proof of sensor freshness. Qualify update rates and sensor health separately. Existing `config/rig.modbus.json` remains an in-process fixture.

## Reproduction and tests

```sh
.venv/bin/python -m pytest tests/unit/test_observation_connectors.py
.venv/bin/python -m pytest tests/platform/test_workbench.py
```

The TCP tests start an actual loopback register server. Serial tests use a bounded transport double, not an Arduino or physical port. MQTT real-broker verification remains the existing explicit opt-in integration test. No tests energize equipment.
