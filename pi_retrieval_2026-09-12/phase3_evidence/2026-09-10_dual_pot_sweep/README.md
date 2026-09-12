# Phase 3 dual potentiometer acquisition evidence

This evidence set records the two Wave 1 sensor emulators through the real hardware path:

`P1 -> ADS1115 A0 -> I2C -> Raspberry Pi 3 A+ -> Python CSV logger`

`P2 -> ADS1115 A1 -> I2C -> Raspberry Pi 3 A+ -> Python CSV logger`

## Result

- 4,457 paired raw samples captured at approximately 10 Hz over 445.6 seconds
- ADS1115 A0 observed range: 0 to 3.302 V
- ADS1115 A1 observed range: 0 to 3.300 V
- all meaningful activity occurred from 21.1 to 94.7 seconds
- the presentation copy ends at 100.0 seconds and excludes 345.6 seconds of idle zero tail
- no samples were smoothed or assigned inferred left, centre, or right labels

## Files

- `p1_p2_a0_a1_marked_sweep_raw.csv`: untouched source recording
- `p1_p2_a0_a1_marked_sweep_trimmed_0_to_100s.csv`: presentation window containing all observed activity
- `p1_p2_dual_voltage_sweep_0_to_100s.png`: overlaid A0 and A1 voltage versus elapsed time
- `p1_p2_dual_voltage_sweep_analysis.md`: quality checks, interpretation boundary, and SHA-256 hashes
- `dual_pot_wiring_as_built_2026-09-10.png`: as-built bench photograph

## Reproduce the analysis

From the repository root:

```bash
python3 tools/phase3_analyze_dual_pot_sweep.py \
  phase3_evidence/2026-09-10_dual_pot_sweep/p1_p2_a0_a1_marked_sweep_raw.csv \
  --output-dir phase3_evidence/2026-09-10_dual_pot_sweep
```

The analysis requires Pillow for static chart export. The acquisition logger is `tools/phase3_ads_dual_logger.py`.

## Claim boundary

This is evidence that two independent low-voltage emulators can be acquired through the ADS1115 and Raspberry Pi software path. It is not evidence of hydraulic sensor calibration or wet-loop performance.
