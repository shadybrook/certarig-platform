# Relay command truth table

- Procedure `relay_truth_table` hash `434b0189c3a1b844836f63c43323620d88d00e96b41d770c3a66d15fa2abc718`
- Run `run_20260912T164757_036efd` · **passed** · all steps and checks passed
- Rig `certarig-wave1-dry-bench` (raspberry_pi) config `e9922ec2e77b1006`
- Contract `9e144a0f814cb072`
- Hardware `RaspberryPiHardware@certarig-pi config=e9922ec2e77b`
- CertaRig 0.4.0

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
| boot_safe | expect | passed |  |
| cycle1_reset | command | passed |  |
| cycle1_permit | command | passed |  |
| cycle1_hold | wait | passed |  |
| cycle1_safe | command | passed |  |
| cycle2_reset | command | passed |  |
| cycle2_permit | command | passed |  |
| cycle2_hold | wait | passed |  |
| cycle2_safe | command | passed |  |
| cycle3_reset | command | passed |  |
| cycle3_permit | command | passed |  |
| cycle3_hold | wait | passed |  |
| cycle3_safe | command | passed |  |
| permit_without_reset | command | passed |  |

## Checks

- PASS: {'event_observed': 'permit_accepted'}
- PASS: {'event_observed': 'operator_safe'}
- PASS: {'event_observed': 'permit_rejected_reset_required'}
- PASS: {'event_not_observed': 'pressure_high_forced_safe'}
- PASS: {'event_not_observed': 'estop_open_forced_safe'}

## Kernel events

- `estop_closed_reset_required`
- `trip_reset_output_safe`
- `permit_accepted`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `operator_safe`
- `permit_rejected_reset_required`

## Recording

`20260912T164757432718Z_relay_truth_table.csv` · 27 samples · sha256 `23cfcba8eca31e8dd43db571d20e775f6fe625d59dd2b45b923a85abcd5c8735`

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

_None._
