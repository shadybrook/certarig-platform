from __future__ import annotations

import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

from ..models import ChannelConfig, RigConfig, RigSnapshot, Sample
from .base import HardwareAdapter, HardwareError


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ADS1115Reader:
    """Small single shot ADS1115 reader for four single ended inputs."""

    _CONFIG_REGISTER = 0x01
    _CONVERSION_REGISTER = 0x00
    _MUX = {0: 0x4000, 1: 0x5000, 2: 0x6000, 3: 0x7000}

    def __init__(self, bus_number: int, address: int) -> None:
        try:
            from smbus2 import SMBus
        except ImportError as exc:
            raise HardwareError("smbus2 is required for Raspberry Pi ADC access") from exc
        self.bus = SMBus(bus_number)
        self.address = address

    def read_voltage(self, channel: int) -> float:
        if channel not in self._MUX:
            raise HardwareError(f"ADS1115 channel {channel} is invalid")
        # Single shot, single ended, gain ±4.096 V, 128 SPS, comparator disabled.
        config = 0x8000 | self._MUX[channel] | 0x0200 | 0x0100 | 0x0080 | 0x0003
        self.bus.write_i2c_block_data(
            self.address,
            self._CONFIG_REGISTER,
            [(config >> 8) & 0xFF, config & 0xFF],
        )
        sleep(0.01)
        data = self.bus.read_i2c_block_data(self.address, self._CONVERSION_REGISTER, 2)
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        return raw * 4.096 / 32768.0

    def close(self) -> None:
        self.bus.close()


class RaspberryPiHardware(HardwareAdapter):
    """GPIO and ADS1115 adapter. Output initializes and closes in the safe state."""

    def __init__(self, config: RigConfig) -> None:
        try:
            from gpiozero import DigitalInputDevice, OutputDevice
        except ImportError as exc:
            raise HardwareError("gpiozero is required for Raspberry Pi GPIO access") from exc

        self.config = config
        hardware = config.hardware
        self.valve = OutputDevice(
            hardware.valve_output_gpio,
            active_high=hardware.output_active_high,
            initial_value=False,
        )
        self.emergency_stop = DigitalInputDevice(
            hardware.emergency_stop_gpio,
            pull_up=True,
            bounce_time=0.02,
        )
        self.feedback = (
            DigitalInputDevice(hardware.relay_feedback_gpio, pull_up=False)
            if hardware.relay_feedback_gpio is not None
            else None
        )
        self.adc = ADS1115Reader(hardware.i2c_bus, hardware.ads1115_address)
        self._io_lock = threading.Lock()
        self._samplers: list[Any] = []
        self._pulse_inputs: list[Any] = []
        if any(c.source and c.source.get("kind") in {"adc", "pulse", "w1", "ina219"} for c in config.channels):
            from .mixed import PulseCounter, SourceSampler, shunt_current, w1_temperature

            for channel in config.channels:
                source = channel.source or {}
                kind = source.get("kind", "adc")
                reader: Any
                if kind == "adc":
                    def read_adc(c: ChannelConfig = channel) -> tuple[float, float]:
                        with self._io_lock:
                            voltage = self.adc.read_voltage(c.adc_channel if c.adc_channel is not None else -1)
                        return self._scale(c, voltage), voltage
                    reader = read_adc
                elif kind == "pulse":
                    counter = PulseCounter(float(source["pulses_per_litre"]), float(source.get("window_s", 1)))
                    pin = DigitalInputDevice(int(source["gpio"]), pull_up=False)
                    pin.when_activated = counter.pulse
                    self._pulse_inputs.append(pin)
                    reader = counter.read
                elif kind == "w1":
                    device_id = str(source["device_id"])
                    if not re.fullmatch(r"28-[a-fA-F0-9]+", device_id):
                        raise HardwareError("Reviewed 1-Wire device identity required")
                    path = Path("/sys/bus/w1/devices") / device_id / "w1_slave"
                    def read_w1(p: Path = path) -> tuple[float, float]:
                        return w1_temperature(p)
                    reader = read_w1
                elif kind == "ina219":
                    def read_current(s: dict[str, Any] = source) -> tuple[float, float]:
                        with self._io_lock:
                            data = self.adc.bus.read_i2c_block_data(int(s["address"]), 1, 2)
                        return shunt_current(data, float(s["shunt_ohms"]))
                    reader = read_current
                else:
                    raise HardwareError(f"Unsupported physical source: {kind}")
                def calibrated(read: Any = reader, s: dict[str, Any] = source) -> tuple[float, float | None]:
                    value, raw = read()
                    return value * float(s.get("gain", 1)) + float(s.get("offset", 0)), raw
                sampler = SourceSampler(channel, calibrated, float(source.get("poll_s", 1 if kind == "w1" else 0.1)))
                self._samplers.append(sampler)
                sampler.start()
        self.force_safe_state()

    def emergency_stop_is_active(self) -> bool:
        # DigitalInputDevice.value is a logical active/inactive value. With
        # pull_up=True gpiozero treats a LOW input as active, so it is the
        # inverse of the electrical level used by our fail-safe NC loop.
        raw_high = bool(self.emergency_stop.pin.state)
        return raw_high if self.config.hardware.emergency_stop_active_high else not raw_high

    @staticmethod
    def _scale(channel: ChannelConfig, voltage: float) -> float:
        required = (
            channel.raw_min_v,
            channel.raw_max_v,
            channel.engineering_min,
            channel.engineering_max,
        )
        if any(value is None for value in required):
            raise HardwareError(f"{channel.channel_id} has incomplete analog scaling")
        assert channel.raw_min_v is not None
        assert channel.raw_max_v is not None
        assert channel.engineering_min is not None
        assert channel.engineering_max is not None
        if channel.raw_max_v <= channel.raw_min_v:
            raise HardwareError(f"{channel.channel_id} raw voltage range is invalid")
        ratio = (voltage - channel.raw_min_v) / (channel.raw_max_v - channel.raw_min_v)
        return channel.engineering_min + ratio * (channel.engineering_max - channel.engineering_min)

    def snapshot(self) -> RigSnapshot:
        captured = utc_now()
        samples: list[Sample] = []
        if self._samplers:
            samples = [sampler.sample() for sampler in self._samplers]
        for channel in (() if self._samplers else self.config.channels):
            if channel.kind != "analog" or channel.adc_channel is None:
                continue
            voltage = self.adc.read_voltage(channel.adc_channel)
            value = self._scale(channel, voltage)
            quality = "good" if channel.valid_min <= value <= channel.valid_max else "out_of_range"
            samples.append(
                Sample(
                    channel_id=channel.channel_id,
                    value=round(value, 5),
                    unit=channel.unit,
                    raw_value=round(voltage, 6),
                    quality=quality,
                    captured_at=captured,
                )
            )
        return RigSnapshot(
            rig_id=self.config.rig_id,
            config_hash=self.config.config_hash,
            emergency_stop_active=self.emergency_stop_is_active(),
            output_safe=self.output_is_safe(),
            samples=tuple(samples),
            captured_at=utc_now(),
            output_feedback=(bool(self.feedback.pin.state) == self.config.hardware.feedback_active_high) if self.feedback is not None else None,
            feedback_source="electrical_gpio" if self.feedback is not None else "command_derived",
        )

    def set_valve(self, open_state: bool) -> None:
        if open_state and self.emergency_stop_is_active():
            raise HardwareError("emergency stop is active")
        if open_state:
            self.valve.on()
        else:
            self.valve.off()

    def force_safe_state(self) -> None:
        self.valve.off()

    def output_is_safe(self) -> bool:
        if self.feedback is not None:
            return not (bool(self.feedback.pin.state) == self.config.hardware.feedback_active_high)
        return not bool(self.valve.value)

    def close(self) -> None:
        self.force_safe_state()
        for sampler in self._samplers:
            sampler.close()
        for pin in self._pulse_inputs:
            pin.close()
        self.adc.close()
        self.valve.close()
        self.emergency_stop.close()
        if self.feedback is not None:
            self.feedback.close()
