# Dual potentiometer guardrail

- Procedure `dual_pot_guardrail` hash `2f5abebaf9ed64957271fcd7ea2e9a72ccf9cb128427e5fd2773c9b9c5d0b3ee`
- Run `run_20260912T165027_1abed2` · **passed** · all steps and checks passed
- Rig `certarig-wave1-dry-bench` (raspberry_pi) config `e9922ec2e77b1006`
- Contract `9e144a0f814cb072`
- Hardware `RaspberryPiHardware@certarig-pi config=e9922ec2e77b`
- CertaRig 0.4.0

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
| safe_start | command | passed |  |
| reset | command | passed |  |
| permit | command | passed |  |
| stable_permit | expect | passed |  |
| raise_pressure | trigger | passed | Turn P1 up slowly until the dashboard shows more than 4.2 bar. Leave P2 in the safe band. Do not touch the E-stop.
 |
| pressure_output_removed | expect | passed |  |
| lower_pressure | trigger | passed | Turn P1 back down below 3.5 bar. Leave P2 untouched. |
| reset_after_pressure | command | passed |  |
| permit_after_pressure | command | passed |  |
| raise_flow | trigger | passed | Turn P2 up slowly until the dashboard shows more than 15.0 L/min. Leave P1 in the safe band.
 |
| flow_output_removed | expect | passed |  |
| lower_flow | trigger | passed | Turn P2 back down below 10 L/min. |
| no_auto_restart | expect | passed |  |
| permit_rejected | command | passed |  |
| end_safe | command | passed |  |

## Checks

- PASS: {'event_observed': 'permit_accepted'}
- PASS: {'event_observed': 'pressure_high_forced_safe'}
- PASS: {'event_observed': 'flow_high_forced_safe'}
- PASS: {'event_observed': 'permit_rejected_reset_required'}
- PASS: {'step': 'pressure_output_removed', 'max_elapsed_ms': 500}
- PASS: {'step': 'flow_output_removed', 'max_elapsed_ms': 500}
- PASS: {'step_passed': 'no_auto_restart'}
- PASS: {'signal': 'pressure', 'peak_below': 9.5}
- PASS: {'signal': 'flow', 'peak_below': 19.5}

## Kernel events

- `csv_recording_stopped`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `pressure_high_forced_safe`
- `process_safe_reset_required`
- `trip_reset_output_safe`
- `permit_accepted`
- `flow_high_forced_safe`
- `process_safe_reset_required`
- `permit_rejected_reset_required`
- `operator_safe`

## Recording

`20260912T165027745800Z_dual_pot_guardrail.csv` · 738 samples · sha256 `aca42c8f6b8ba62100a1ff500f09a413684fcf3dd992c8342fdd1d95b90d7445`

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

If either pot fails to drop the output, stop: force safe, remove the external 5 V supply and inspect GPIO23 and the ADS1115 wiring for that channel before retrying.
