# CertaRig Phase 3 E-stop input evidence

## Result

**PASS for repeatable fail-safe input sensing.** Raspberry Pi physical pin 18 / BCM GPIO24 repeatedly distinguished the closed NC1 loop from the open state. The input-only logger did not command GPIO23 or energize a relay.

## As-built circuit

| Connection | Raspberry Pi mapping | E-stop terminal |
|---|---|---|
| Sense | Physical pin 18 / BCM GPIO24 | Measured and labelled NC1-A |
| Ground | Physical pin 20 / GND | Measured and labelled NC1-B |

NC2, physical pin 16 / GPIO23, physical pin 22 / GPIO25, the relay and the separate 5 V output supply remained disconnected.

Before power was applied, the user reported approximately 0.4 to 1.0 ohm across the verified NC pairs when reset/released and `OL` with no continuity beep when latched. The attached photograph records the general as-built arrangement, but the header numbering is obscured; pin identity therefore rests on the reported physical-pin trace and continuity gate rather than photograph interpretation alone.

## Powered checks

- Pi hostname and SSH session: passed.
- ADS1115 retained at I2C address `0x48`.
- Repository revision on the Pi: `eb928d1`.
- Python safety tests on the Pi: 14 passed.
- E-stop contract under test: LOW is healthy; HIGH/open is active.
- GPIO backend: Raspberry Pi OS system Python with the installed `lgpio` backend. The isolated project virtual environment lacked a GPIO backend and stopped before capture; no data from that failed attempt was used.

## Capture quality

- Raw samples: 3,934.
- Duration: 196.650086 seconds.
- Nominal rate: 20 Hz.
- Median interval: 0.049999 seconds.
- Maximum interval: 0.050206 seconds.
- Missing sample indexes: 0.
- Duplicate sample indexes: 0.
- GPIO/polarity inconsistencies: 0.
- Observed transitions: 8.
- Healthy/LOW windows: 4.
- Active/HIGH-or-open windows: 5.

The long initial HIGH interval is retained in the raw evidence and represents the waiting period before physical operation began. No smoothing or retrospective state relabelling was applied.

## Evidence files

- [`estop_gpio24_raw.csv`](estop_gpio24_raw.csv): immutable raw 20 Hz capture.
- [`estop_gpio24_analysis.md`](estop_gpio24_analysis.md): integrity checks and every consecutive state window.
- [`estop_gpio24_state_timeline.png`](estop_gpio24_state_timeline.png): full state timeline.
- [`estop_nc1_as_built.png`](estop_nc1_as_built.png): as-built bench photograph.
- [`../../tools/phase3_analyze_estop.py`](../../tools/phase3_analyze_estop.py): reproducible validation and chart generator.

## Reproduce the analysis

Install the optional evidence dependency with `python3 -m pip install -e '.[evidence]'`, then run:

```bash
python3 tools/phase3_analyze_estop.py \
  phase3_evidence/2026-09-10_estop/estop_gpio24_raw.csv \
  --output-dir phase3_evidence/2026-09-10_estop
```

## Interpretation boundary

This proves low-voltage dry-bench GPIO input behavior, not a certified safety function. The raw state alone cannot distinguish a button latch from an intentionally disconnected wire because both correctly appear as HIGH/active. A synchronized video or explicitly marked repeat is required to present broken-wire handling as a separately identifiable test case.
