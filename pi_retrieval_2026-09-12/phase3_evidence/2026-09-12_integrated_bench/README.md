# CertaRig integrated dry-bench validation - 12 September 2026

## Result

**PASS for the Phase 3 low-voltage dry-bench scope.** The Raspberry Pi, ADS1115, two analogue emulators, physical E-stop, transistor relay driver, fused 5 V indicator circuit, software trip latch, reset gate and anti-restart behaviour operated together as intended.

This result demonstrates implementation readiness of the CertaRig control and evidence architecture. It does not demonstrate hydraulic performance, water compatibility, pressure containment, pump or valve sizing, mains switching, or field certification. Those items remain reserved for the capstone build.

The optional broken-wire/open-circuit injection test was not performed at the operator's request. It is recorded as **not tested**, not as a pass.

## Frozen as-built configuration

| Function | Connection |
|---|---|
| ADS1115 | I2C bus 1, address `0x48` |
| Pressure emulator P1 | ADS1115 A0, 0-3.3 V dry analogue input |
| Flow emulator P2 | ADS1115 A1, 0-3.3 V dry analogue input |
| E-stop NC1 sense | Pi physical pin 18, BCM GPIO24; LOW healthy/released, HIGH open/active |
| Relay command | Pi physical pin 16, BCM GPIO23, through the BC547 interface to CH1 |
| E-stop sense ground | Pi physical pin 20, GND |
| Potentiometer supply | Pi physical pin 17, 3.3 V hub for P1 and P2 only |
| Fused output supply | Pi physical pin 2, 5 V, through a 1 A fuse to `FUSED_5V` |
| Relay-board supply interlock | E-stop NC2 interrupts relay `DC+`; `DC-` is common ground |
| Relay trigger configuration | S1 bridges control `COM` to `LOW`; lower/control COM has no external wire; CH2 is unused |
| Indicator changeover | K1 contact COM receives `FUSED_5V`; NC feeds red through 1 kOhm; NO feeds green through 1 kOhm |

Physical pin 16 is GPIO23 and is not ground. Physical pin 17 is not connected to the relay lower/control COM. ADS1115 and Pi GPIO inputs must never receive 5 V.

## Corrected software interpretation

During Gate 1, direct GPIO inspection showed that `gpiozero.DigitalInputDevice.value` represents the device's logical active/inactive state and is inverted when `pull_up=True`; it is not the raw electrical pin level. The hardware adapter and both Phase 3 loggers were corrected to use `DigitalInputDevice.pin.state`. A regression test was added.

After the correction, the full project check passed with 6 JavaScript tests, 20 Python tests, the dashboard build and four evidence-bundle checks.

## Gate 2 - relay control characterization

### Safe boot

`gate2_transistor_boot_safe.csv` contains 1,318 samples over 131.7 seconds. GPIO24 remained LOW/healthy, GPIO23 remained LOW and the trip latch remained set. With relay-board power available, the small board-power LED was on while K1 and its channel indicator remained off.

### Permit and safe command

`gate2_transistor_permit_safe.csv` contains 817 samples over 81.6 seconds. After a reset, a permit command drove GPIO23 HIGH for 131 samples and produced an observed K1 click and channel-light activation. The safe command returned GPIO23 LOW and produced a second click with the K1 light off.

| Event | Elapsed time | Observed result |
|---|---:|---|
| Reset | 4.10 s | Output remained safe; trip latch cleared |
| Permit | 44.10 s | GPIO23 HIGH; K1 energized with click |
| Safe | 57.20 s | GPIO23 LOW; K1 released with click |
| Operator mark | 81.60 s | Permit/safe observation recorded as pass |

## Gate 3 - integrated truth table

`gate3_integrated_truth_table.csv` contains 3,160 samples over 315.9 seconds. GPIO24 was LOW/healthy for 2,484 samples and HIGH/E-stop-active for 676 samples. GPIO23 was LOW for 2,559 samples and HIGH for 601 samples.

| Test state | Expected physical result | Observed result | Status |
|---|---|---|---|
| Power-up with E-stop latched | Board supply interrupted; K1 off; red on; green off | Board-power LED off, K1 off with no click, red on, green off | Pass |
| E-stop released before reset | Board supply available but output inhibited | Board-power LED on, K1 off, red on, green off | Pass |
| Reset then permit | K1 energized; red off; green on | K1 clicked on, channel LED on, red off, green on | Pass |
| Operator safe | K1 released; red on; green off | K1 clicked off, channel LED off, red on, green off | Pass |
| Three permit/safe cycles | Same changeover on every cycle | All three cycles matched the expected result | Pass |
| E-stop latched during permit | Hardware supply removed and software forces GPIO23 LOW | K1 released immediately; board and channel LEDs off; green off; red on; `estop_open_forced_safe` recorded | Pass |
| E-stop released after trip | No automatic restart | Board power returned but K1 remained off; red stayed on; `estop_closed_reset_required` recorded | Pass |
| Permit attempted without reset | Command rejected | `permit_rejected_reset_required`; GPIO23 remained LOW | Pass |
| Broken NC1 sensing wire | Open circuit must force safe | Not performed | Not tested |

The initial indicator failure was traced to a broken connector between Pi physical pin 2 and the fuse holder. After the connector was repaired, continuity checks passed and the integrated truth table behaved correctly. This repair is part of the evidence and should be discussed as a practical reliability lesson, not hidden.

## Runtime health

After relay characterization, the Pi reported `throttled=0x0` and 37.6 C. After the integrated truth-table run, it reported `throttled=0x0` and 38.1 C. No undervoltage or thermal-throttling flag was present in either final check.

The Pi was shut down cleanly over SSH after evidence capture.

## Evidence integrity

| File | SHA-256 |
|---|---|
| `gate2_transistor_boot_safe.csv` | `97a534833d2832eae3da2994a08b32da62d4b54480aa808346e35aeeb55d8c3f` |
| `gate2_transistor_permit_safe.csv` | `b539cd2f9ff1b80482da95f9ab7d4b643024f1089a906e71879f790b1cb73a0a` |
| `gate3_integrated_truth_table.csv` | `a419534ae5678850255b8682de8e3010e435134d89376da38f674542eccbeea2` |

## Submission diagram and photographs

- [Final as-built circuit diagram, PNG](../../docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png)
- [Final as-built circuit diagram, editable SVG](../../docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.svg)
- [Final as-built circuit diagram, PDF](../../docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.pdf)
- [Five labelled pre-power photographs](../2026-09-11_integrated_bench/pre_power_photos/)

The operator confirmed that the circuit was preserved and the final photograph task was completed. At the time of this repository update, the versioned folder contains the five labelled pre-power photographs. Any separately captured red-safe and green-permit photographs must be copied into this evidence folder before they can be published.

## Remaining Phase 3 evidence

The hardware truth table is complete. Before submission, the project still needs:

1. Copy the separately captured red-safe and green-permit photographs into the evidence folder if they are to be included publicly.
2. Run one sensor-guardrail sequence that moves P1 and P2 through safe and unsafe values and proves that the decision layer permits or inhibits K1 accordingly.
3. Demonstrate the Pi-hosted dashboard from the Mac, with terminal, dashboard and physical bench visible in the evidence set.
4. Run a short stability test and capture a compact resource-usage snapshot.
5. Complete the Phase 3 template, final demonstration video and GitHub release/tag.
