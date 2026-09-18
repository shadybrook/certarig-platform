# Flow guardrail verification

- Procedure `flow_guardrail` hash `d87092e74475e9d511bf4255a7f2f260d21f97479dfcd8f6b9ad10966e351363`
- Run `run_20260912T164909_fa83c5` · **passed** · all steps and checks passed
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
| raise_flow | trigger | passed | Turn the P2 flow emulator up slowly until the dashboard shows more than 15.0 L/min. Leave P1 in the safe band. Do not touch the E-stop.
 |
| output_removed | expect | passed |  |
| lower_flow | trigger | passed | Turn P2 back down below 10 L/min. |
| no_auto_restart | expect | passed |  |
| permit_rejected | command | passed |  |
| end_safe | command | passed |  |

## Checks

- PASS: {'event_observed': 'permit_accepted'}
- PASS: {'event_observed': 'flow_high_forced_safe'}
- PASS: {'event_observed': 'permit_rejected_reset_required'}
- PASS: {'step': 'output_removed', 'max_elapsed_ms': 500}
- PASS: {'step_passed': 'no_auto_restart'}
- PASS: {'signal': 'flow', 'peak_below': 19.5}

## Kernel events

- `csv_recording_stopped`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `flow_high_forced_safe`
- `process_safe_reset_required`
- `permit_rejected_reset_required`
- `operator_safe`

## Recording

`20260912T164909427739Z_flow_guardrail.csv` · 657 samples · sha256 `825a779aa0fefdebf87343f64302a7f5ce0bfa2da6314e11c9361bed79a22da3`

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
