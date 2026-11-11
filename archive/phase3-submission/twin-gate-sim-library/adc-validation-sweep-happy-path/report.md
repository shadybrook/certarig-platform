# ADC channel validation sweep

- Procedure `adc_validation` hash `c8a138df2e810a9bbabc6d8ba64317f54e9e0ae5b48006aadfb522eeeaae8a9b`
- Run `run_20260912T120004_4ae689` · **passed** · all steps and checks passed
- Rig `certarig-wave1-sim` (simulator) config `9e6a03f94e6db04e`
- Contract `ac68338b687f7c9b`
- Hardware `SimulatedRig@Chintans-MacBook-Air.local config=9e6a03f94e6d`
- CertaRig 0.4.0

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
| baseline | expect | passed |  |
| pressure_low | trigger | passed | Turn P1 fully anticlockwise (minimum pressure). |
| pressure_high | trigger | passed | Turn P1 slowly to maximum. Expect the trip indicator; the output is not armed. |
| pressure_mid | trigger | passed | Return P1 to roughly the middle of its travel (2 to 3 bar). |
| flow_low | trigger | passed | Turn P2 fully anticlockwise (minimum flow). |
| flow_high | trigger | passed | Turn P2 slowly to maximum. |
| flow_mid | trigger | passed | Return P2 to roughly the middle of its travel (6 to 10 L/min). |
| settle | expect | passed |  |
| output_never_armed | expect | passed |  |

## Checks

- PASS: {'event_not_observed': 'permit_accepted'}
- PASS: {'step_passed': 'settle'}
- PASS: {'signal': 'pressure', 'peak_below': 10.0}
- PASS: {'signal': 'flow', 'peak_below': 20.0}

## Kernel events

- `estop_closed_reset_required`
- `csv_recording_started`
- `pressure_high_forced_safe`
- `process_safe_reset_required`
- `flow_high_forced_safe`
- `process_safe_reset_required`

## Recording

`20260912T120004283733Z_adc_validation.csv` · 375 samples · sha256 `c43a0abd94602a9883bc29d46178839f6ea3254ab8c48fcdc236fde0e970e371`

## Bench briefing

_No bench briefing was saved._

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

_None._
