# Pressure guardrail verification

- Procedure `pressure_guardrail` hash `e4fc18842bf34db758d06c9a1013ad8fc7b81bab26b195eeece634e1ef52832e`
- Run `run_20260912T120014_0f1045` · **passed** · all steps and checks passed
- Rig `certarig-wave1-sim` (simulator) config `9e6a03f94e6db04e`
- Contract `ac68338b687f7c9b`
- Hardware `SimulatedRig@Chintans-MacBook-Air.local config=9e6a03f94e6d`
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

- `estop_closed_reset_required`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `pressure_high_forced_safe`
- `process_safe_reset_required`
- `permit_rejected_reset_required`
- `operator_safe`

## Recording

`20260912T120014073672Z_sim-guardrail.csv` · 213 samples · sha256 `e9ead768fb0ce0b67b18f20b1b879c51afb5d5f1bf0979db62deeb0d2630e36c`

## Bench briefing

_No bench briefing was saved._

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

If the output did not drop within the response time, stop: force safe from Studio, remove the external 5 V supply and inspect the GPIO23 transistor stage and relay wiring before retrying.
