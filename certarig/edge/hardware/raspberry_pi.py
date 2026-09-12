from __future__ import annotations

import os
from datetime import UTC, datetime
from time import sleep

from ..models import ChannelConfig, RigConfig, RigSnapshot, Sample, in_valid_range
from .base import HardwareAdapter, HardwareError

GPIO_BACKEND_HELP = (
    "Raspberry Pi GPIO needs the system lgpio backend. "
    "Set GPIOZERO_PIN_FACTORY=lgpio and recreate the venv with --system-site-packages "
    "so the OS lgpio package is visible. Isolated Python 3.13 venvs fail this import."
)


def require_pi_gpio_backend() -> None:
    """Fail in English before gpiozero opens pins. Isolated venvs cannot see system lgpio."""
    factory = os.environ.get("GPIOZERO_PIN_FACTORY", "")
    if factory and factory != "lgpio":
        raise HardwareError(
            f"GPIOZERO_PIN_FACTORY={factory} will not drive this bench. Set it to lgpio. {GPIO_BACKEND_HELP}"
        )
    try:
        import lgpio  # noqa: F401
    except ImportError as exc:
        raise HardwareError(GPIO_BACKEND_HELP) from exc
    os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")


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
        require_pi_gpio_backend()
        try:
            from gpiozero import DigitalInputDevice, OutputDevice
        except ImportError as exc:
            raise HardwareError(
                "gpiozero is required for Raspberry Pi GPIO access. " + GPIO_BACKEND_HELP
            ) from exc

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
        for channel in self.config.channels:
            if channel.kind != "analog" or channel.adc_channel is None:
                continue
            voltage = self.adc.read_voltage(channel.adc_channel)
            value = self._scale(channel, voltage)
            quality = "good" if in_valid_range(channel, value) else "out_of_range"
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
            captured_at=captured,
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
            return not bool(self.feedback.value)
        return not bool(self.valve.value)

    def close(self) -> None:
        self.force_safe_state()
        self.adc.close()
        self.valve.close()
        self.emergency_stop.close()
        if self.feedback is not None:
            self.feedback.close()
