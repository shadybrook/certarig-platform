# CertaRig emergency stop GPIO24 analysis

## Evidence result

**PASS:** The capture contains both the healthy closed-loop state and the active/open state with repeatable transitions. The logger only observed the GPIO input and did not command the relay output.

## Data quality checks

- Raw source: `estop_gpio24_raw.csv`
- SHA256: `ed622dee797e5b10f1fd51723cfc1185b6a2295937ce13483fe9571f4365319b`
- Samples: 3,934
- Duration: 196.650086 seconds
- Sample index range: 0 to 3933
- Duplicate sample indexes: 0
- Missing sample indexes: 0
- Strictly increasing elapsed time: True
- Median sample interval: 0.049999 seconds
- Maximum sample interval: 0.050206 seconds
- Unexpected GPIO numbers: none
- Unexpected raw levels: none
- HIGH/active polarity mismatches: 0
- State transitions: 8
- Healthy windows: 4
- Active/open windows: 5

## Consecutive state windows

| Window | Start s | End s | Duration s | Interpreted state | Samples |
|---:|---:|---:|---:|---|---:|
| 1 | 0.001 | 117.300 | 117.299 | ACTIVE / HIGH or open | 2,347 |
| 2 | 117.350 | 124.550 | 7.200 | HEALTHY / LOW closed loop | 145 |
| 3 | 124.600 | 135.700 | 11.100 | ACTIVE / HIGH or open | 223 |
| 4 | 135.750 | 144.650 | 8.900 | HEALTHY / LOW closed loop | 179 |
| 5 | 144.700 | 151.900 | 7.200 | ACTIVE / HIGH or open | 145 |
| 6 | 151.950 | 158.600 | 6.650 | HEALTHY / LOW closed loop | 134 |
| 7 | 158.650 | 164.950 | 6.300 | ACTIVE / HIGH or open | 127 |
| 8 | 165.000 | 170.500 | 5.500 | HEALTHY / LOW closed loop | 111 |
| 9 | 170.550 | 196.650 | 26.100 | ACTIVE / HIGH or open | 523 |

## Interpretation boundary

The electrical observation proves that BCM24 repeatedly distinguishes a closed NC1 loop from an open loop. Because the capture contains no operator event markers, the CSV alone cannot distinguish a button latch from a deliberately disconnected wire; both correctly appear as HIGH/active by fail-safe design. A labelled repeat or synchronized video is required if broken-wire handling must be evidenced as a separate test case.
