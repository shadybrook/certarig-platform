# Flow guardrail verification

- Procedure `flow_guardrail` hash `d87092e74475e9d511bf4255a7f2f260d21f97479dfcd8f6b9ad10966e351363`
- Run `run_20260912T120018_8e3fb2` · **passed** · all steps and checks passed
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

- `estop_closed_reset_required`
- `operator_safe`
- `trip_reset_output_safe`
- `permit_accepted`
- `flow_high_forced_safe`
- `process_safe_reset_required`
- `permit_rejected_reset_required`
- `operator_safe`

## Recording

`20260912T120018457526Z_sim-flow-guardrail.csv` · 242 samples · sha256 `33f3b722b0b77e6fa559b691a0ab25ee3ebe76898b4db7129e2e6d6f78ab5741`

## Bench briefing

_No bench briefing was saved._

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

If the output did not drop within the response time, stop: force safe from Studio, remove the external 5 V supply and inspect the GPIO23 transistor stage and relay wiring before retrying.
