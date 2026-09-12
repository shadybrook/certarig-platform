from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from certarig.edge.hardware.raspberry_pi import RaspberryPiHardware
from certarig.edge.models import HardwareConfig, RigConfig


class FakePin:
    def __init__(self) -> None:
        self.state = False


class FakeInput:
    def __init__(self, pin: int, **_: object) -> None:
        self.number = pin
        self.pin = FakePin()
        self.value = 0

    def close(self) -> None:
        pass


class FakeOutput(FakeInput):
    def __init__(self, pin: int, *, initial_value: bool, **kwargs: object) -> None:
        super().__init__(pin, **kwargs)
        self.value = int(initial_value)

    def on(self) -> None:
        self.value = 1

    def off(self) -> None:
        self.value = 0


class FakeADC:
    def __init__(self, *_: object) -> None:
        pass

    def close(self) -> None:
        pass


def config(active_high: bool = True) -> RigConfig:
    return RigConfig(
        rig_id="test-rig",
        revision="test",
        sample_interval_ms=100,
        pressure_abort_bar=4.2,
        abort_limits={"pressure": 4.2},
        hardware=HardwareConfig(
            emergency_stop_active_high=active_high,
            relay_feedback_gpio=None,
        ),
        channels=(),
        config_hash="test",
    )


class RaspberryPiHardwareTests(unittest.TestCase):
    def build(self, active_high: bool = True) -> RaspberryPiHardware:
        fake_gpiozero = types.SimpleNamespace(
            DigitalInputDevice=FakeInput,
            OutputDevice=FakeOutput,
        )
        fake_lgpio = types.ModuleType("lgpio")
        with (
            patch.dict(sys.modules, {"gpiozero": fake_gpiozero, "lgpio": fake_lgpio}),
            patch.dict("os.environ", {"GPIOZERO_PIN_FACTORY": "lgpio"}),
            patch("certarig.edge.hardware.raspberry_pi.ADS1115Reader", FakeADC),
        ):
            return RaspberryPiHardware(config(active_high))

    def test_fail_safe_nc_loop_low_is_healthy_and_high_is_active(self) -> None:
        hardware = self.build(active_high=True)
        hardware.emergency_stop.pin.state = False
        self.assertFalse(hardware.emergency_stop_is_active())
        hardware.emergency_stop.pin.state = True
        self.assertTrue(hardware.emergency_stop_is_active())

    def test_estop_uses_raw_pin_state_not_gpiozero_logical_value(self) -> None:
        hardware = self.build(active_high=True)
        hardware.emergency_stop.value = 1
        hardware.emergency_stop.pin.state = False
        self.assertFalse(hardware.emergency_stop_is_active())

    def test_output_initializes_in_safe_state(self) -> None:
        hardware = self.build(active_high=True)
        self.assertEqual(hardware.valve.value, 0)
        self.assertTrue(hardware.output_is_safe())

    def test_active_estop_blocks_open_command(self) -> None:
        hardware = self.build(active_high=True)
        hardware.emergency_stop.pin.state = True
        with self.assertRaisesRegex(Exception, "emergency stop is active"):
            hardware.set_valve(True)
        self.assertTrue(hardware.output_is_safe())

    def test_polarity_can_be_inverted_for_non_wave1_hardware(self) -> None:
        hardware = self.build(active_high=False)
        hardware.emergency_stop.pin.state = False
        self.assertTrue(hardware.emergency_stop_is_active())
        hardware.emergency_stop.pin.state = True
        self.assertFalse(hardware.emergency_stop_is_active())

    def test_missing_lgpio_is_english(self) -> None:
        from certarig.edge.hardware.base import HardwareError
        from certarig.edge.hardware.raspberry_pi import require_pi_gpio_backend

        with (
            patch.dict("os.environ", {"GPIOZERO_PIN_FACTORY": "lgpio"}),
            patch.dict(sys.modules, {"lgpio": None}),
        ):
            with self.assertRaisesRegex(HardwareError, "system-site-packages"):
                require_pi_gpio_backend()

    def test_wrong_pin_factory_is_refused(self) -> None:
        from certarig.edge.hardware.base import HardwareError
        from certarig.edge.hardware.raspberry_pi import require_pi_gpio_backend

        with patch.dict("os.environ", {"GPIOZERO_PIN_FACTORY": "mock"}):
            with self.assertRaisesRegex(HardwareError, "GPIOZERO_PIN_FACTORY=mock"):
                require_pi_gpio_backend()


if __name__ == "__main__":
    unittest.main()
