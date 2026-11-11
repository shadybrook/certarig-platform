# ADC channel validation sweep

- Procedure `adc_validation` hash `c8a138df2e810a9bbabc6d8ba64317f54e9e0ae5b48006aadfb522eeeaae8a9b`
- Run `run_20260912T162352_6515a9` · **failed** · step pressure_high failed: sensor invalid during step: pressure, pressure_emulator
- Rig `certarig-wave1-dry-bench` (raspberry_pi) config `e9922ec2e77b1006`
- Contract `9e144a0f814cb072`
- Hardware `RaspberryPiHardware@certarig-pi config=e9922ec2e77b`
- CertaRig 0.4.0

## Deterministic results

| Step | Type | Status | Detail |
| --- | --- | --- | --- |
| baseline | expect | passed |  |
| pressure_low | trigger | passed | Turn P1 fully anticlockwise (minimum pressure). |
| pressure_high | trigger | failed | Turn P1 slowly to maximum. Expect the trip indicator; the output is not armed. |
| pressure_mid | trigger | skipped |  |
| flow_low | trigger | skipped |  |
| flow_high | trigger | skipped |  |
| flow_mid | trigger | skipped |  |
| settle | expect | skipped |  |
| output_never_armed | expect | skipped |  |

## Checks

- PASS: {'event_not_observed': 'permit_accepted'}
- FAIL: {'step_passed': 'settle'}
- PASS: {'signal': 'pressure', 'peak_below': 10.0}
- PASS: {'signal': 'flow', 'peak_below': 20.0}

## Kernel events

- `operator_safe`
- `csv_recording_started`
- `sensor_invalid_forced_safe`

## Recording

`20260912T162352039157Z_observe-adc.csv` · 169 samples · sha256 `fbabf42bf15716bb561907504adb0a66c92c47ae35decb4b00815786d14f65d1`

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
