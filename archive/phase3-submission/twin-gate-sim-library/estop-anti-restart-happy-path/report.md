# E-stop trip and anti-restart verification

- Procedure `estop_anti_restart` hash `b312dca54cd03eed9164451cb73cc2809d9c2bacee93598a1a9ea7b6076f59b8`
- Run `run_20260912T120012_6190c8` · **passed** · all steps and checks passed
- Rig `certarig-wave1-sim` (simulator) config `9e6a03f94e6db04e`
- Contract `ac68338b687f7c9b`
- Hardware `SimulatedRig@Chintans-MacBook-Air.local config=9e6a03f94e6d`
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

- `estop_closed_reset_required`
- `trip_reset_output_safe`
- `permit_accepted`
- `estop_open_forced_safe`
- `estop_closed_reset_required`
- `permit_rejected_reset_required`

## Recording

`20260912T120012022193Z_estop_anti_restart.csv` · 97 samples · sha256 `80547dea4448b0ae598206238567eb54998881c3ec2ba9534737371c6fdf0a14`

## Bench briefing

_No bench briefing was saved._

## Agent narrative

The following text, if present, is the agent's explanation. It is **not** a measurement.

_No agent narrative was attached._

## Recovery

If the output stayed on with the E-stop pressed, remove the external relay supply immediately. Check NC1 wiring on GPIO24 and NC2 in the relay power branch.
