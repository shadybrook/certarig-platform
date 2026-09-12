from __future__ import annotations

import unittest

from certarig.edge.commissioning import DryBenchInterlock


class DryBenchInterlockTests(unittest.TestCase):
    def test_boot_and_monitor_mode_are_safe(self) -> None:
        state = DryBenchInterlock(allow_output=False)
        state.observe(False)
        result = state.command("permit")
        self.assertFalse(result.drive_high)
        self.assertEqual(result.event, "permit_rejected_monitor_only")

    def test_healthy_permit_can_drive_when_explicitly_enabled(self) -> None:
        state = DryBenchInterlock(allow_output=True)
        state.observe(False)
        rejected = state.command("permit")
        self.assertFalse(rejected.drive_high)
        self.assertEqual(rejected.event, "permit_rejected_reset_required")
        state.command("reset")
        result = state.command("permit")
        self.assertTrue(result.drive_high)
        self.assertEqual(result.event, "permit_accepted")

    def test_estop_forces_safe_and_latches_trip(self) -> None:
        state = DryBenchInterlock(allow_output=True)
        state.observe(False)
        state.command("reset")
        self.assertTrue(state.command("permit").drive_high)
        result = state.observe(True)
        self.assertFalse(result.drive_high)
        self.assertFalse(result.permit_requested)
        self.assertTrue(result.trip_latched)
        self.assertEqual(result.event, "estop_open_forced_safe")

    def test_release_never_auto_reenergizes(self) -> None:
        state = DryBenchInterlock(allow_output=True)
        state.observe(False)
        state.command("reset")
        state.command("permit")
        state.observe(True)
        result = state.observe(False)
        self.assertFalse(result.drive_high)
        self.assertTrue(result.trip_latched)
        self.assertEqual(result.event, "estop_closed_reset_required")

    def test_reset_requires_healthy_closed_loop(self) -> None:
        state = DryBenchInterlock(allow_output=True)
        result = state.command("reset")
        self.assertTrue(result.trip_latched)
        self.assertEqual(result.event, "reset_rejected_estop_open")
        state.observe(False)
        result = state.command("reset")
        self.assertFalse(result.drive_high)
        self.assertFalse(result.trip_latched)
        self.assertEqual(result.event, "trip_reset_output_safe")


if __name__ == "__main__":
    unittest.main()
