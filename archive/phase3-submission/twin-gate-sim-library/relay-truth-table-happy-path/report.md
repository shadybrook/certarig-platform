# Relay command truth table

- Procedure `relay_truth_table` hash `434b0189c3a1b844836f63c43323620d88d00e96b41d770c3a66d15fa2abc718`
- Run `run_20260912T120002_dde140` · **passed** · all steps and checks passed
- Rig `certarig-wave1-sim` (simulator) config `9e6a03f94e6db04e`
- Contract `ac68338b687f7c9b`
- Hardware `SimulatedRig@Chintans-MacBook-Air.local config=9e6a03f94e6d`
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

`20260912T120002536556Z_relay_truth_table.csv` · 86 samples · sha256 `6cc675caae48a44e1948bbbf9df197dd6475b21e07cc17e17b8a8f5c07c7f41f`

## Bench briefing

_No bench briefing was saved._

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

_None._
