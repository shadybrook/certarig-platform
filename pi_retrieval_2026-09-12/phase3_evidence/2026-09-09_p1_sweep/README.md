# CertaRig P1 ADS1115 Voltage Sweep

Evidence ID: `CERT-P3-IN-P1-002`

## Acquisition

- Host: Raspberry Pi 3 Model A+ (`certarig-pi`)
- ADC: ADS1115 detected at I2C address `0x48`
- Channel: A0
- Rate: 10 Hz
- Samples: 794
- Duration: 79.3 seconds
- Repository commit on Pi: `6cc4e75`

## Results

- Minimum raw reading: -0.240 V
- Maximum raw reading: 3.296 V
- Mean across the complete mixed-position run: 0.406 V
- Stable high plateau: approximately 3.2 to 3.3 V
- Zero/off or left baseline: approximately 0 V
- Intermediate plateaus demonstrate that A0 responds to shaft movement.

The retry demonstrates a real physical input path from the potentiometer through ADS1115 A0 to Python running on the Raspberry Pi. Shaft-position labels in the graph are inferred from plateaus because position-change markers were not synchronised into the CSV.

## Follow-up gate

The raw trace includes negative transition values, with a minimum of -0.240 V, and the centre position was not held at one repeatable plateau. Treat this run as functional-path evidence, not final calibration evidence. Before calibration acceptance, inspect the switched potentiometer contacts and repeat a marked left-centre-right acquisition without switching the track off during the recording.

## Files and integrity

- `p1_a0_voltage_sweep_retry.csv` - SHA-256 `9cc6182e2b503896e17b2083fe9d0292a5d54391f1d23a1a326a8d8a267cf5f7`
- `p1_a0_voltage_sweep_time_plot.png` - SHA-256 `3865b4c072b8852a447f47bc785447c4db22823b067a89e3dbe37d1bd6135058`
- `phase3_ads_sweep_logger.py` - acquisition source
- `plot_phase3_p1_sweep.py` - reproducible static chart source
