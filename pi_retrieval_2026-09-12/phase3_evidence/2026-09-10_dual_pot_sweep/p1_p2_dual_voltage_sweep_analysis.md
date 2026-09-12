# CertaRig P1 and P2 dual ADS1115 sweep analysis

## Evidence boundary

The raw source CSV is retained unchanged. The presentation CSV and chart use the first 100.0 seconds, ending 5.3 seconds after the last sample with either channel above 0.01 V. This removes 345.6 seconds (5.76 minutes) of idle zero tail without altering the retained samples.

## Data quality checks

- Raw rows: 4,457
- Plotted rows: 1,000
- Sample index range: 0 to 4456
- Duplicate sample indexes: 0
- Missing expected sample indexes: 0
- Strictly increasing elapsed time: True
- Median sample interval: 0.099999 s
- Maximum sample interval: 0.100341 s
- First observed activity: 21.100 s
- Last observed activity: 94.700 s
- A0 range in plotted window: 0.000000 to 3.302000 V
- A1 range in plotted window: 0.000000 to 3.300000 V
- Values above 3.35 V: 0
- Values below -0.005 V: 0

## Interpretation

Both independent ADS1115 channels traversed approximately the full 0 to 3.3 V bench range. The plot presents raw voltage against elapsed time with no smoothing and no inferred left, centre, or right labels. This is evidence for the two potentiometer to ADS1115 to Raspberry Pi acquisition path; it is not hydraulic sensor calibration evidence.

## Integrity hashes

- Raw CSV SHA-256: `c211510215978302a8286558ad5829e3173587c8f7647eb1eef374e191392390`
- Trimmed CSV SHA-256: `d0afad7c7d23d79e1608070d5845716df8cf77dcdc1f206d1fd0314ed46cc2f8`
- Chart PNG SHA-256: `55e40a6f0aae263cce95bfccfbb39f79d36c0bb2481f9be0d7818eadf3bbd891`
