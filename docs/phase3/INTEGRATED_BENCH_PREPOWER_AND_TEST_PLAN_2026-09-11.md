# CertaRig integrated bench pre-power review and evidence plan

Document date: 11 September 2026
Historical gate status: **SUPERSEDED BY PASS on 12 September 2026.** The listed unpowered checks were completed, the fuse-holder connector fault was repaired, and the integrated relay/indicator/E-stop truth table passed. See the [12 September evidence report](../../phase3_evidence/2026-09-12_integrated_bench/README.md).
Scope: low-voltage Phase 3 dry bench only

## 1. Evidence and authority boundary

The five supplied photographs and the separately supplied hole-coordinate text are inspection evidence, not proof of electrical continuity. The measured circuit behaviour, PCB silkscreen, component markings, current CertaRig wiring contract, and this gate register are authoritative.

The reported breadboard coordinates are:

- BC547B collector `C4`, base `C5`, emitter `C6`.
- GPIO23 input node `A2`, 1 kohm `B2-B5`, 10 kohm `D5-D6`, control ground `A6`, and collector-to-CH1 from `A4`.
- `FUSED_5V` on row 12 and common ground on row 13.
- Red inhibited indicator branch on rows 11, 15, and 16.
- Green permitted indicator branch on rows 14, 18, and 19.

These coordinates remain **reported, not verified**, until the meter checks below pass.

## 2. Photo review

Observed in the photographs:

- Raspberry Pi 3 Model A+, ADS1115, two potentiometers, dual-NC E-stop, BC547B interface area, relay module, 100 uF capacitor, glass fuse holder, and two panel indicators are present.
- ADS1115 A0/A1 and the previously verified Pi connections appear to remain installed.
- The relay low-voltage block is populated for DC+, DC-, and CH1; CH2 is unused. The former physical-pin-17 wire to lower/control COM has been removed after it reproduced the Pi power fault; cable colours do not certify identity.
- In the earlier photographs, only two wires were clearly visible on one three-screw relay contact group. The operator subsequently reported that `K1 NO` was connected to breadboard `F14`. An updated photograph and the U21-U23 continuity results are still required before this is accepted electrically.
- The S1 `LOW-COM` jumper position, fuse rating, capacitor polarity stripe, transistor C-B-E rows, indicator polarity, and hidden breadboard strips are not legible enough to approve from the photographs.
- The inhibited indicator is red in the as-built bench, replacing the yellow indicator named in the earlier design. Its function is unchanged.

The photographed variant routes the low-current 5 V dry-bench distribution through breadboard strips. This is a variance from the preferred secure-connector layout in the relay SOP. It is acceptable only for this indicator-only bench after the continuity, short-circuit, and voltage-drop checks pass. It is not approved for a motor, pump, valve, servo, mains load, or hydraulic capstone hardware.

## 3. Gate 0: mandatory unpowered acceptance

### 3.1 Safe state

1. Remove PWR IN from the Pi.
2. Remove the 1 A fuse from the holder.
3. Latch the E-stop.
4. Wait 30 seconds.
5. Measure DC voltage between Pi physical pin 2 and physical pin 25; accept less than 0.10 V.
6. Confirm all Pi, relay, and panel lights are off.

### 3.2 Identity checks

1. Read and photograph the fuse marking; it must be the 1 A fuse, not a 20 A fuse.
2. Photograph the S1 jumper closely enough to show that it bridges `LOW` and `COM`.
3. Meter-map the K1 contact group. Unpowered K1 COM-to-NC must be approximately 0-1 ohm and COM-to-NO must be `OL`.
4. Ensure three wires are installed on that same measured K1 group: `FUSED_5V -> COM`, `NC -> 1 kohm -> red +`, and `NO -> 1 kohm -> green +`.
5. Verify capacitor positive is on `FUSED_5V` and the negative stripe is on common ground.
6. Confirm physical pin 22 / GPIO25 is empty and CH2 is empty.

### 3.3 Point-to-point continuity register

For low-resistance continuity checks, first record the reading obtained by firmly shorting the meter probes on the same range. A connection passes when it reads no more than 1 ohm above that probe baseline. This avoids falsely assigning lead and probe-contact resistance to the circuit.

| ID | Test points | Required result |
|---|---|---|
| U01 | Pi physical pin 2 to fuse input | 0-1 ohm |
| U02 | Removed 1 A fuse, end to end | 0-1 ohm |
| U03 | Fuse-holder output to reported row-12 `FUSED_5V` | 0-1 ohm |
| U04 | `FUSED_5V` to capacitor positive | 0-1 ohm |
| U05 | `FUSED_5V` to measured K1 COM | 0-1 ohm |
| U06 | Pi physical pin 25 to reported row-13 ground | 0-1 ohm |
| U07 | Pi pin 25 to relay DC- | 0-1 ohm |
| U08 | Pi pin 25 to BC547B emitter row C6 | 0-1 ohm |
| U09 | Pi pin 25 to capacitor negative stripe | 0-1 ohm |
| U10 | Pi pin 25 to both indicator negative leads | 0-1 ohm each |
| U11 | Pi pin 16 through installed base resistor to BC547B base C5 | 0.95-1.05 kohm |
| U12 | BC547B base-row resistor to emitter row | Installed 10 kohm path; record actual reading and probe direction |
| U13 | BC547B collector C4 to relay CH1 | 0-1 ohm |
| U14 | Shared pin-17 3.3 V hub to relay lower/control COM | `OL`; no installed conductor |
| U15 | `FUSED_5V` to relay DC+, E-stop reset | 0-1 ohm through NC2 |
| U16 | `FUSED_5V` to relay DC+, E-stop latched | `OL` |
| U17 | Pi pin 18 to pin 20, E-stop reset | 0-1 ohm through NC1 |
| U18 | Pi pin 18 to pin 20, E-stop latched | `OL` |
| U19 | Measured K1 COM to K1 NC, relay unpowered | No more than 1 ohm above shorted-probe baseline |
| U20 | Measured K1 COM to K1 NO, relay unpowered | `OL` |
| U21 | Measured K1 NO terminal to breadboard F14 | 0-1 ohm |
| U22 | Measured K1 NO terminal through the installed branch resistor to green indicator positive | 0.95-1.05 kohm |
| U23 | Measured K1 NC terminal through the installed branch resistor to red indicator positive | 0.95-1.05 kohm |
| U24 | Pin-17 splitter to P1 high terminal | 0-1 ohm |
| U25 | Pin-17 splitter to P2 high terminal | 0-1 ohm |
| U26 | Relay lower/control COM to DC- with S1 on COM-LOW | Record actual module-specific resistance; never feed this terminal from 3.3 V |

### 3.4 No-short register

With the E-stop latched and fuse removed:

| ID | Test points | Required result |
|---|---|---|
| S01 | `FUSED_5V` to common ground | No sustained continuity beep; a capacitor-charge transient is acceptable |
| S02 | Pi 3.3 V hub to Pi 5 V | No continuity beep |
| S03 | Pi physical pin 16 / GPIO23 to Pi 5 V | No continuity beep |
| S04 | BC547B collector to emitter | No sustained continuity beep |
| S05 | E-stop NC1 pair to NC2 pair | No cross-continuity |
| S06 | Shared pin-17 3.3 V hub to common ground | No sustained continuity beep; with only the measured 10 kohm and 8.4 kohm pot tracks connected, approximately 4.5 kohm is expected |
| S07 | Pi-side fuse-holder input to common ground | No sustained continuity beep |
| S08 | Shared pin-17 3.3 V hub to relay lower/control COM | No continuity; `OL` |

Any failure keeps the status at HOLD. Do not install the fuse or power the Pi.

The earlier 9 ohm S06 failure followed the physical-pin-17-to-relay-lower-COM branch during isolation. That branch is now prohibited. Before retrying Gate 1, repeat S06 and S08 with the branch removed. If S06 is still low, isolate P1 and P2 one at a time and verify each potentiometer only across its two fixed end terminals: P1 should remain approximately 10 kohm and P2 approximately 8.4 kohm throughout shaft travel. The wiper must connect only to ADS1115 A0 or A1.

## 4. Gate 1: Pi-only baseline, fuse removed

After Gate 0 is accepted:

1. Keep the fuse removed and reset the E-stop.
2. Power the Pi only through PWR IN.
3. Connect through SSH and capture hostname, date, OS, kernel, repository commit, running CertaRig processes, `vcgencmd get_throttled`, temperature, I2C address `0x48`, GPIO23/GPIO24 state, and the full software test result.
4. Run the integrated logger in monitor-only mode. It must reject `permit` and keep GPIO23 LOW.
5. Measure pin 2 to pin 25 and pin 17 to pin 25. Accept 4.75-5.25 V and 3.20-3.35 V respectively.
6. Shut down through SSH, wait for activity to stop, and remove PWR IN.

## 5. Gate 2: relay characterization and hardwired inhibit

1. With power removed, isolate the K1 contact load by disconnecting the row-12-to-K1-contact-COM wire; disconnect CH1 from the transistor at the relay screw.
2. Keep lower/control COM externally disconnected, S1 on COM-LOW, CH2 empty, and insert the verified 1 A fuse.
3. Latch the E-stop, power through PWR IN, and verify `FUSED_5V` is 4.75-5.25 V while relay DC+ is approximately 0 V.
4. Reset the E-stop and verify relay DC+ is 4.75-5.25 V with no unsolicited K1 click.
5. Record lower/control COM-to-DC- and CH1-to-DC- voltages.
6. Probe the documented low-trigger behaviour by connecting CH1 to DC- through a measured 1 kohm resistor. If K1 does not click, stop and report; do not move S1 under power or apply 5 V to CH1.
7. Remove the temporary resistor and confirm K1 releases. Preserve the module LED and audible/mechanical observations. Do not use resistance or continuity mode while the module is powered; contact transfer is verified later by the powered indicator truth table.
8. Remove the temporary resistor, reconnect CH1 to the BC547 collector, and perform one transistor-controlled click test while the K1 contact load remains isolated.
9. Only after that passes, power down and restore row 12 to K1 contact COM for the red/green truth-table test.
10. Recheck `vcgencmd get_throttled`; preferred result `0x0`.

Stop immediately for a Pi reset, undervoltage, unexpected relay click, green light without a permit, wrong voltage, unstable wiring, warmth, smell, spark, or smoke.

## 6. Gate 3: explicitly armed relay truth-table capture

Only after Gates 0-2 pass, run the integrated logger with both `--allow-output` and `--acknowledge-dry-bench`.

1. Start in safe state and record red on, green off.
2. Send `reset`; output must remain safe.
3. Send `permit`; GPIO23 goes HIGH, K1 should energize, red should turn off, and green should turn on.
4. Send `safe`; GPIO23 goes LOW, K1 should de-energize, red should turn on, and green should turn off.
5. Repeat three cycles while video and CSV run.
6. During one permitted state, latch the E-stop. NC2 must remove relay power and GPIO24 must force the software command safe. Red must return on and green off.
7. Release the E-stop. The relay must remain off until a new `reset` followed by a new `permit`; automatic re-energization is forbidden.
8. With output safe, temporarily open only the NC1 sense wire. Software must detect active/open and reject `permit`; NC2 is not disturbed in this case.
9. Restore NC1, reset the trip, and verify one final permit/safe cycle.
10. Stop the logger; it forces GPIO23 LOW in its cleanup path.

The CSV records GPIO23 command state but not independent relay-contact feedback. Physical relay and indicator observations require synchronized video and the meter truth table.

## 7. Gate 4: analogue and interlock test cases

Record A0, A1, GPIO24, the safety latch, and GPIO23 at 10 paired samples per second. Do not assign hydraulic accuracy to the potentiometers.

1. **Nominal acquisition:** start both potentiometers near their measured mid-voltage and hold 10 seconds.
2. **Pressure traversal:** move P1 slowly toward increasing A0 voltage, hold near low, middle, and high for 10 seconds each, then return to a safe mid-voltage. We will use live voltage, not assumed shaft direction.
3. **Flow traversal:** hold P1 safe; move P2 through low, middle, and high A1 voltage with 10-second holds.
4. **Pressure interlock:** while permitted, raise A0 past the configured 4.2 bar equivalent, approximately 1.387 V with the current 0-3.302 V to 0-10 bar mapping. The deterministic runtime must de-energize and record the reason.
5. **E-stop interlock:** with both channels nominal and a valid permit, latch the E-stop and verify the hardware and software safe state.
6. **Broken-wire interlock:** open NC1 only; permit must be rejected and the fault recorded.
7. **Restart default:** restart the logger/service with the E-stop healthy; GPIO23 must start LOW and no previous permit may be restored.

P2's configured 15 L/min safe maximum corresponds to approximately 2.475 V with the current 0-3.3 V to 0-20 L/min mapping. It is a bench test threshold, not flow-sensor calibration.

## 8. Evidence package

Store under `phase3_evidence/2026-09-11_integrated_bench/`:

- original and labelled as-built photographs;
- completed unpowered meter register;
- baseline SSH transcript and software-test transcript;
- raw integrated CSV with UTC timestamps and event markers;
- voltage and state-transition graphs;
- rail-voltage table for E-stop latched/reset states;
- relay/indicator truth table;
- synchronized video notes;
- SHA-256 hashes, interpretation, deviations, and stop conditions;
- final PASS/FAIL/PARTIAL result for every test case.

Passing this plan supports a claim of evidence consistent with laboratory breadboard readiness. It does not validate a hydraulic system, real sensors, a pump, a valve, mains loads, EMC, long-duration reliability, or capstone commissioning.
