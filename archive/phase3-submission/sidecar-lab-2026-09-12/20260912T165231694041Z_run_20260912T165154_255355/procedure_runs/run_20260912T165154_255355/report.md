# E-stop trip and anti-restart verification

- Procedure `estop_anti_restart` hash `b312dca54cd03eed9164451cb73cc2809d9c2bacee93598a1a9ea7b6076f59b8`
- Run `run_20260912T165154_255355` · **passed** · all steps and checks passed
- Rig `certarig-wave1-dry-bench` (raspberry_pi) config `e9922ec2e77b1006`
- Contract `9e144a0f814cb072`
- Hardware `RaspberryPiHardware@certarig-pi config=e9922ec2e77b`
- CertaRig 0.4.0

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
| reset | command | passed |  |
| permit | command | passed |  |
| press_estop | trigger | passed | Press the E-stop mushroom head firmly until it latches. |
| output_removed | expect | passed |  |
| release_estop | trigger | passed | Twist the E-stop head to release it. |
| no_restart | expect | passed |  |
| permit_rejected | command | passed |  |
| end_safe | command | passed |  |

## Checks

- PASS: {'event_observed': 'estop_open_forced_safe'}
- PASS: {'event_observed': 'estop_closed_reset_required'}
- PASS: {'event_observed': 'permit_rejected_reset_required'}
- PASS: {'step': 'output_removed', 'max_elapsed_ms': 300}

## Kernel events

- `csv_recording_stopped`
- `trip_reset_output_safe`
- `permit_accepted`
- `estop_open_forced_safe`
- `estop_closed_reset_required`
- `permit_rejected_reset_required`

## Recording

`20260912T165154772516Z_estop_anti_restart.csv` · 264 samples · sha256 `205149a1248dd3986b1f1aee81fe9a14f4e3f71118576eb0eacd9d5e35b81347`

## Bench briefing

- **p1_role**: Pressure emulator P1, ADS1115 A0
- **p2_role**: Flow emulator P2, ADS1115 A1
- **estop**: GPIO24 mushroom head
- **relay**: GPIO23 permit / indicator
- **diagram_notes**: Wave-1 dry bench sidecar lab 2026-09-12. Phase 3 files not used.
- updated_at: `2026-09-12T16:23:44.654891+00:00`

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

If the output stayed on with the E-stop pressed, remove the external relay supply immediately. Check NC1 wiring on GPIO24 and NC2 in the relay power branch.
