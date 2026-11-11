# CertaRig next-stage SOP: fail-safe E-stop input

## Purpose

Prove that the emergency-stop input fails safe before any relay, indicator or separate 5 V output circuit is connected.

## Fixed circuit contract

- Physical pin 18 is BCM GPIO24, the E-stop sense input.
- Physical pin 20 is GND for the E-stop sense loop.
- The Pi uses its internal pull-up.
- Reset/released and electrically closed means GPIO LOW and healthy.
- Latched, open contact or broken wire means GPIO HIGH and E-stop active.
- Physical pin 16 / GPIO23, physical pin 22 / GPIO25, the relay and the external 5 V supply remain disconnected during this stage.

## Gate A: offline contact mapping

1. Keep the Pi shut down and remove the PWR IN cable.
2. Keep the separate 5 V supply disconnected.
3. Remove the E-stop from every circuit.
4. Set the multimeter to continuity or the lowest resistance range.
5. Find the first terminal pair that reads approximately 0-1 ohm when the E-stop is reset and `OL` when it is latched.
6. Label those actual terminals `NC1-A` and `NC1-B`.
7. Find the second independent pair with the same behaviour and label it `NC2-A` and `NC2-B`.
8. Confirm every cross-pair combination remains open in both switch states.
9. Reset and latch the switch five times and record all ten readings.
10. Stop if either pair is intermittent, reads closed when latched, or cannot be identified unambiguously.

Do not infer contact identity from physical position or a marketplace description. The measured pair is authoritative.

## Gate B: wire only the sense loop

With all power removed:

| Wire | From | To |
|---|---|---|
| W13 | Pi physical pin 18 / BCM GPIO24 | `NC1-A` |
| W14 | `NC1-B` | Pi physical pin 20 / GND |

Either end of a passive NC pair may be called A or B. The circuit behaviour is unchanged if W13 and W14 are exchanged across the same verified pair.

Insulate `NC2-A` and `NC2-B` separately. Do not connect the relay, transistor, fuse, indicators or external 5 V supply. Leave physical pins 16 and 22 unconnected.

## Gate C: unpowered verification

1. Visually trace W13 from physical pin 18 to `NC1-A`.
2. Visually trace W14 from `NC1-B` to physical pin 20.
3. Confirm neither wire touches physical pin 17, pin 16, pin 22, or either 5 V pin.
4. Across physical pins 18 and 20, measure continuity with the E-stop reset.
5. Across the same pins, verify open circuit with the E-stop latched.
6. Repeat three times.
7. Photograph the entire unpowered build and a close-up of the E-stop terminal labels.

## Gate D: powered evidence run

Only after Gates A-C pass:

1. Reset the E-stop.
2. Power the Pi only through PWR IN.
3. Connect by SSH.
4. Pull the latest repository revision and run the complete tests.
5. Start the input-only logger:

```bash
cd ~/certarig-phase-2-poc
python3 tools/phase3_estop_logger.py --output phase3-estop-input.csv
```

On Raspberry Pi OS, use the system Python so `gpiozero` can use the OS-installed `lgpio` backend. If the logger reports that no GPIO pin factory can be loaded, stop and repair the environment; do not substitute mock data or reverse the safety polarity.

6. Hold reset/released for 5 seconds.
7. Latch the E-stop for 5 seconds.
8. Reset it for 5 seconds.
9. Remove one W13 or W14 connection for 5 seconds to represent a broken wire.
10. Restore the wire, hold reset for 5 seconds, then stop the logger with Control-C.

Expected truth table:

| Physical state | Raw GPIO24 | Interpreted state |
|---|---:|---|
| Reset and NC1 closed | LOW | healthy |
| E-stop latched and NC1 open | HIGH | active |
| W13 or W14 disconnected | HIGH | active |

Any disagreement is a failed gate. Shut down and inspect the measured pair, wire placement and software revision. Do not reverse the safety meaning merely to make a test pass.

## Evidence to retain

- Offline five-cycle contact truth table.
- Labelled contact and wiring photographs.
- Software commit hash and complete test output.
- Logger CSV containing normal, latched, reset and broken-wire states.
- Short video showing the physical switch and corresponding software state.
- A limitations statement: this is a low-voltage dry-bench safety-input test, not a certified safety function.
