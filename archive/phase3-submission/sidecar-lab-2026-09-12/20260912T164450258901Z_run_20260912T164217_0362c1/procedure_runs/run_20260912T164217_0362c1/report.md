# ADC channel validation sweep

- Procedure `adc_validation` hash `c8a138df2e810a9bbabc6d8ba64317f54e9e0ae5b48006aadfb522eeeaae8a9b`
- Run `run_20260912T164217_0362c1` · **passed** · all steps and checks passed
- Rig `certarig-wave1-dry-bench` (raspberry_pi) config `e9922ec2e77b1006`
- Contract `9e144a0f814cb072`
- Hardware `RaspberryPiHardware@certarig-pi config=e9922ec2e77b`
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

- `csv_recording_stopped`
- `csv_recording_started`
- `pressure_high_forced_safe`
- `process_safe_reset_required`
- `flow_high_forced_safe`
- `process_safe_reset_required`

## Recording

`20260912T164217928048Z_observe-adc-3.csv` · 1291 samples · sha256 `0b01e6ab8a4af1e90b4eda63e983f456a039932ec7cee7b368af582717ef008d`

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
