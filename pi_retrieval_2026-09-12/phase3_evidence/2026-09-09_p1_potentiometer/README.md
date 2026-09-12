# CertaRig P1 Potentiometer Characterisation

Evidence ID: `CERT-P3-IN-P1-001`

## Device

- Inventory ID: R15
- Robu code: 1163662
- Manufacturer part: TE Connectivity 23ESA103MMF50AF
- Nominal value: 10 kohm linear potentiometer
- Intended function: P1 pressure-sensor emulator for ADS1115 A0

## Operator-measured resistance sweep

The following measurements were reported by Chintan on 9 September 2026. Values are interpreted as kohms based on the selected component and approximately 10 kohm fixed-end result.

| Pair | Shaft left | Shaft centre | Shaft right |
|---|---:|---:|---:|
| A-B | 10.0 | 4.5 | 0.0 |
| B-C | 0.0 | 5.6 | 10.0 |
| A-C | 10.0 | 9.9 | 10.0 |

## Interpretation

- A and C are the fixed resistance-track ends because A-C remains approximately 10 kohm across the full rotation.
- B is the wiper because both A-B and B-C vary with shaft position.
- The centre values sum to approximately 10.1 kohm, consistent with the fixed-end measurement and ordinary meter/contact tolerance.
- For voltage to increase as the shaft moves from left to right, connect A to 3.3 V, C to ground, and B to ADS1115 A0.

## Acceptance

Result: PASS for offline potentiometer identification and sweep.

The measurement demonstrates terminal identity and a continuous resistive sweep. It does not yet demonstrate powered A0 voltage, ADS1115 acquisition, calibration, or stability. Those remain the next commissioning gate.

## As-built correction before energisation

During assembly, the potentiometer ground was initially placed on Raspberry Pi physical pin 16. This was identified before energisation and moved to physical pin 14. Physical pin 14 is GND. Physical pin 16 is BCM GPIO23 and is reserved for the later relay command; it is not a ground pin.

Correct Stage 4 allocation:

- Pot terminal A to Raspberry Pi physical pin 17, 3.3 V.
- Pot terminal B, the wiper, to ADS1115 A0.
- Pot terminal C to Raspberry Pi physical pin 14, GND.
- Raspberry Pi physical pin 16 left unconnected at this stage.

## Pre-power as-built photograph

- File: `IMG_1878_p1_as_built_pre_power.png`
- SHA-256: `540f87788e14cca33103601a09ae383dd2e3f4a4093736b9b645c1a8b2b4cd39`
- Visual interpretation: yellow is connected to ADS1115 A0; red and orange appear to terminate at Raspberry Pi physical pins 17 and 14 respectively; physical pin 16 appears unused.
- Evidence limitation: the angled photograph is not sufficient to prove electrical continuity or rule out a one-pin offset. Confirm all three endpoints with the Pi unpowered and a multimeter before energisation.
- Safety observation: the three potentiometer solder joints are exposed. Insulate each joint separately and provide strain relief before power is applied.
- Decoupling observation: no external 100 nF capacitor is visible across ADS1115 VDD and GND. A controlled baseline test may be recorded as a temporary deviation, but the capacitor should be fitted before final analogue stability evidence.
