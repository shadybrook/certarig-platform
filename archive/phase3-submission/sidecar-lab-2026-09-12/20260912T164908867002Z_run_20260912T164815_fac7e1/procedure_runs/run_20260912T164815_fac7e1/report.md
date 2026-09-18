# Pressure guardrail verification

- Procedure `pressure_guardrail` hash `e4fc18842bf34db758d06c9a1013ad8fc7b81bab26b195eeece634e1ef52832e`
- Run `run_20260912T164815_fac7e1` · **passed** · all steps and checks passed
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
| raise_pressure | trigger | passed | Turn the P1 pressure emulator up slowly until the dashboard shows more than 4.2 bar. Do not touch the E-stop.
 |
| output_removed | expect | passed |  |
| lower_pressure | trigger | passed | Turn P1 back down below 3.5 bar. |
| no_auto_restart | expect | passed |  |
| permit_rejected | command | passed |  |
| end_safe | command | passed |  |

## Checks

- PASS: {'event_observed': 'permit_accepted'}
- PASS: {'event_observed': 'pressure_high_forced_safe'}
- PASS: {'event_observed': 'permit_rejected_reset_required'}
- PASS: {'step': 'output_removed', 'max_elapsed_ms': 500}
- PASS: {'step_passed': 'no_auto_restart'}
- PASS: {'signal': 'pressure', 'peak_below': 9.5}

## Kernel events

- `csv_recording_stopped`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `pressure_high_forced_safe`
- `process_safe_reset_required`
- `permit_rejected_reset_required`
- `operator_safe`

## Recording

`20260912T164815402100Z_pressure_guardrail.csv` · 445 samples · sha256 `ab60a10a521b07e8554c05170388c30469eba002c713120fe239dd9a439c5192`

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

If the output did not drop within the response time, stop: force safe from Studio, remove the external 5 V supply and inspect the GPIO23 transistor stage and relay wiring before retrying.
