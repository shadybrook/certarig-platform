# CertaRig Phase 3 Stage 2 sensor guardrail shadow run

Date: 12 September 2026

## Purpose

This run exercised the real Raspberry Pi, ADS1115, two potentiometer sensor emulators and dual-channel E-stop while physical actuation was disabled. The dashboard sampled the real bench and evaluated the guardrail, but the software was not authorised to energise GPIO23 or K1.

## Configuration and final state

- Rig: `certarig-wave1-dry-bench`
- Configuration hash: `e9922ec2e77b1006a336b4739b200d6c5372b02b457446b1b44b9c45bfed29ed`
- Hardware mode: `raspberry_pi`
- Actuation enabled: `false`
- Samples: 7,591 over 758.70 seconds
- Final GPIO23 command: LOW
- Final trip latch: set
- Final recording state: stopped
- Pi final temperature: 40.8 C
- Pi throttling status: `0x0`
- ADS1115 detected on I2C bus 1 at `0x48`

## Formal acceptance observations

| Case | Evidence | Result |
| --- | --- | --- |
| Off-position sensor validity | Negative values at the exact switched-off boundary produced `sensor_invalid_forced_safe`. | Pass |
| Monitor-only authority | Dashboard health reported `actuation_enabled: false`; the permit API rejected actuation during the session. | Pass |
| Pressure high | CSV sample 4,614 recorded 4.31859 bar and `pressure_high_forced_safe`. | Pass |
| Pressure recovery | Returning P1 below 4.2 bar left the trip latched and produced `process_safe_reset_required`. | Pass |
| Flow high | CSV sample 6,332 recorded 15.16364 L/min and `flow_high_forced_safe` while P1 was 0.0 bar. | Pass |
| Flow recovery | Returning P2 below 15 L/min left the trip latched and produced `process_safe_reset_required`. | Pass |
| E-stop | CSV sample 7,272 recorded `estop_open_forced_safe` with the E-stop input active. | Pass |
| E-stop recovery | Releasing the E-stop did not clear the trip; the final safe state remained reset-required. | Pass |
| Final explicit safe command | `stage2_final_state.json` records `operator_safe`, GPIO23 LOW and recording stopped. | Pass |

The operator directly observed during the formal pressure case that K1 did not click, the red panel indicator remained on and the green panel indicator remained off. The operator also reported completing the prescribed E-stop latch and release cycle. The relay and panel-light fields inside the CSV and dashboard are command/contact-model expectations because no dedicated relay feedback sensor is fitted.

The CSV includes preliminary control movements before the formal cases. Consequently, the aggregate event counts contain additional pressure, flow and invalid-boundary transitions. The formal acceptance rows above identify the clean events used for the Phase 3 claim.

## Artifacts

- `stage2_shadow_guardrail.csv`: immutable raw sample log
- `stage2_shadow_guardrail_analysis.json`: machine-readable summary
- `stage2_shadow_guardrail_analysis.md`: compact human-readable summary
- `stage2_shadow_guardrail_plot.svg`: pressure and flow plot
- `stage2_dashboard_health.json`: dashboard mode and configuration evidence
- `stage2_final_state.json`: final safe-state evidence
- `stage2_pi_health.txt`: Pi, OS, temperature, throttling and I2C evidence

## Claim boundary

This is evidence consistent with a university low-voltage dry hardware-in-the-loop proof of concept. It does not validate hydraulic performance, mains switching, pumps, valves, wet sensors, leakage, priming, cavitation, surge, EMI or long-duration industrial reliability.
