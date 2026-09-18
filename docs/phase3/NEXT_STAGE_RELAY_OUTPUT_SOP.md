# CertaRig next-stage SOP: fail-safe relay and indicator output

Document date: 11 September 2026
Revision: 1.2
Scope: Phase 3 low-voltage dry bench only

Commissioning status: **Passed on 12 September 2026.** This remains the construction and test SOP; the submission-facing canonical circuit is the [final as-built diagram](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png).

## 1. Purpose and controlled scope

This SOP adds one physical output channel to the already verified CertaRig bench. GPIO23 commands relay channel 1 through a BC547B transistor. The second normally-closed E-stop contact removes power from the relay coil. The relay contacts select a red inhibited indicator or a green permitted indicator. Revision 1.1 recorded the as-built substitution of red for the originally planned yellow indicator. Revision 1.2 removes the former pin-17-to-relay-control-COM connection after the powered isolation test showed that branch collapsed the Pi power indication.

This stage uses only the Raspberry Pi power-input rail and low-voltage indicators. Do not connect mains voltage, a pump, a solenoid, a servo, water, or any pressure-bearing equipment.

The Pi must be powered only through its normal PWR IN micro-USB connector. Physical pin 2 is used only as a fused 5 V branch source after the Pi supply has entered the board. Never connect a second 5 V supply to physical pin 2 or pin 4 while PWR IN is connected.

This SOP supersedes only the separate-supply version of Circuit B in the 7 September Wave 1 wiring guide. The separate-supply design remains the preferred later design for motors, pumps, valves, servos, or capstone hardware.

## 2. Verified circuits that must not be disturbed

| Function | Raspberry Pi physical pin | BCM or rail | Current state |
|---|---:|---|---|
| ADS1115 VDD | 1 | 3V3 | Verified |
| ADS1115 SDA | 3 | GPIO2 / SDA1 | Verified |
| ADS1115 SCL | 5 | GPIO3 / SCL1 | Verified |
| ADS1115 GND | 6 | GND | Verified |
| Potentiometer P2 ground | 9 | GND | Verified |
| Potentiometer P1 ground | 14 | GND | Verified |
| Potentiometer 3.3 V splitter | 17 | 3V3 | Verified |
| E-stop sense NC1-A | 18 | GPIO24 | Verified |
| E-stop sense NC1-B | 20 | GND | Verified |
| Relay feedback | 22 | GPIO25 | Disabled; leave unconnected |

Do not move any of these wires. Physical pin 16 is GPIO23, not ground. Physical pin 25 is a separate ground pin selected for the new control circuit.

## 3. New wiring contract

| New function | Exact connection |
|---|---|
| Relay command | Pi physical pin 16 / GPIO23 -> 1 kohm -> BC547B base |
| Boot-safe pull-down | 10 kohm from BC547B base to emitter |
| Control ground | Pi physical pin 25 / GND -> breadboard ground rail -> BC547B emitter |
| Relay trigger | BC547B collector -> relay `CH1 / IN1` |
| Trigger reference | Relay S1 jumper on `COM-LOW`; lower control `COM` has no external wire |
| Relay power source | Pi physical pin 2 / 5V -> 1 A fuse -> fused 5 V node |
| Hardwired inhibit | Fused 5 V node -> E-stop `NC2-A` -> `NC2-B` -> relay `DC+ / VCC` |
| Relay power return | Relay `DC- / GND` -> common ground node |
| Bulk decoupling | 100 uF capacitor from fused 5 V node to common ground, before NC2 |
| Red state | Fused 5 V node -> relay K1 `COM` -> K1 `NC` -> 1 kohm -> red indicator positive |
| Green state | Relay K1 `NO` -> 1 kohm -> green indicator positive |
| Indicator return | Both indicator negative leads -> common ground node |

The two indicator resistors are protective current limiters. Keep them even if the 3-9 V panel indicators contain internal resistors.

### Wire-by-wire schedule

| Wire | From | Through | To | Colour / label |
|---|---|---|---|---|
| W15 | Pi physical pin 16 / GPIO23 | 1 kohm base resistor | BC547B base | Green, `CMD_23` |
| W16 | BC547B base | 10 kohm pull-down | BC547B emitter | Label `B-E 10K` |
| W17 | Pi physical pin 25 / GND | Ground distribution point | BC547B emitter | Black, `0V` |
| W18 | BC547B collector | Direct signal wire | Relay `CH1 / IN1` | Green, `CH1` |
| W19 | Relay lower/control `COM` | No wire | Leave externally disconnected while S1 bridges `COM-LOW` | `NO EXT WIRE` |
| W20 | Pi physical pin 2 / 5V | Direct wire | 1 A fuse-holder input | Red, `PI_5V` |
| W21 | Fuse-holder output | Distribution splice | `FUSED_5V` node | Red, `FUSED_5V` |
| W22 | `FUSED_5V` | Direct wire | E-stop `NC2-A` | Red, `NC2_IN` |
| W23 | E-stop `NC2-B` | Direct wire | Relay `DC+ / VCC` | Red, `RELAY_5V` |
| W24 | Common ground | Direct wire | Relay `DC- / GND` | Black, `RELAY_0V` |
| W25 | `FUSED_5V` | Direct wire | K1 contact `COM` | Red, `K1_COM_5V` |
| W26 | K1 contact `NC` | 1 kohm indicator resistor | Red indicator positive | Red, `SAFE` |
| W27 | K1 contact `NO` | 1 kohm indicator resistor | Green indicator positive | Green, `PERMIT` |
| W28 | Both indicator negative leads | Ground distribution point | Pi physical pin 25 / GND | Black, `IND_0V` |
| W29 | `FUSED_5V` | Direct wire | 100 uF capacitor positive | Red, `CAP_PLUS` |
| W30 | 100 uF capacitor negative stripe | Ground distribution point | Pi physical pin 25 / GND | Black, `CAP_MINUS` |

[Open the final full-system as-built diagram](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png). The earlier [single-rail relay subsystem diagram](diagrams/CertaRig_Relay_Output_Single_Rail_Wiring.svg) is retained for detailed relay-stage reference.

## 4. Actual relay-module map from the supplied close-ups

The module is fitted with two `SLA-05VDC-SL-C` relays and two trigger-selection jumpers marked `S1` and `S2`.

With the five low-voltage screw terminals on the right and the `S1/S2` jumper bank below them, the printed terminal order from top to bottom is:

1. `DC+ / VCC`
2. `DC- / GND`
3. `CH1 / IN1`
4. `CH2 / IN2`
5. `COM`

The first three screws happen to be in a green block and the last two in an orange block. Do not use block colour as a wiring rule.

The six large contact screws are printed in two groups of:

1. `NC`
2. `NO`
3. `COM`

Use only the group belonging to relay `K1`. Confirm K1 by the PCB marking and by the unpowered continuity test in Gate C; do not choose a group only because it appears upper or lower in a photograph.

For channel 1, fit the S1 jumper across the pins marked `LOW` and `COM`. Leave CH2 unconnected. Keep the lower/control `COM` screw externally disconnected. It is not either of the K1/K2 contact `COM` screws.

This rule is hardware-derived. With all power removed, the operator measured the lower/control `COM` close to `DC-` in the `COM-LOW` jumper position. During staged isolation, adding only the physical-pin-17-to-lower-COM branch extinguished the Pi red PWR indication; removing only that branch restored normal PWR indication. Never reconnect physical pin 17, physical pin 1, or any other 3.3 V source to this lower/control `COM` terminal.

### 4.1 Physical pin 17 distribution clarification

Physical pin 17 supplies only the two verified potentiometers. Do not stack another connector or loose wire directly onto that occupied Pi header pin. Pin 17 has one outgoing conductor to the existing 3.3 V distribution splitter. The splitter provides exactly two branches:

1. Potentiometer P1 high terminal.
2. Potentiometer P2 high terminal.

Do not add a third branch for the relay. The two potentiometers draw less than 1 mA together. Relay power comes only through `DC+` from the fused 5 V branch; relay `DC-` returns to common ground; CH1 is the only command input used.

## 5. Parts required

- Raspberry Pi 3 Model A+ with official 5 V, 2.5 A PWR IN supply
- 2-channel 5 V relay module, Robu item R260139
- One BC547B NPN transistor, Robu item R224115
- One 1 kohm resistor for the transistor base
- One 10 kohm resistor for the base-to-emitter pull-down
- Two additional 1 kohm resistors for the panel indicators
- One 1 A fast-acting fuse and holder
- One 100 uF electrolytic capacitor rated 25 V or higher
- Green and red 3-9 V panel indicators
- E-stop NC2 contact pair already identified and labelled
- MB102 breadboard for the transistor and low-current control connections
- Dupont wires for signal wiring and 24 AWG wire for the fused 5 V and indicator wiring
- Digital multimeter

The 100 nF ceramic capacitor is optional for this first relay test. If it is later fitted, place it in parallel with the 100 uF capacitor on the fused 5 V node before NC2. It has no polarity. Do not place either capacitor after NC2, because stored charge there could delay relay drop-out when the E-stop is latched.

The module's optocouplers do not provide full galvanic isolation in this single-rail arrangement because the Pi and relay power share a common 0 V reference. The optocoupler input and BC547B still form a controlled interface, but the separate-supply design is required if full isolation or a real actuator is introduced.

## 6. Gate A: make the bench electrically safe

Do all of the following before touching a wire:

1. Shut down the Pi through SSH with `sudo shutdown -h now`.
2. Wait until the SSH session closes and the green activity LED stops.
3. Remove the PWR IN plug from the Pi.
4. Remove the 1 A fuse from its holder.
5. Latch the E-stop.
6. Confirm the relay LEDs, panel indicators, and Pi LEDs are off.
7. Set the multimeter to DC voltage and verify approximately 0 V between Pi physical pin 2 and physical pin 25.
8. Keep the relay contact side free of mains and external loads.

If any voltage remains, stop and find its source. Never insert, remove, or tighten wires while the circuit is powered.

## 7. Gate B: identify and verify every loose component

### 7.1 Resistors

Measure each resistor out of circuit:

| Purpose | Nominal value | Acceptable bench reading |
|---|---:|---:|
| GPIO23 to base | 1 kohm | 0.95-1.05 kohm |
| Base to emitter | 10 kohm | 9.5-10.5 kohm |
| Red indicator limiter | 1 kohm | 0.95-1.05 kohm |
| Green indicator limiter | 1 kohm | 0.95-1.05 kohm |

Label them before inserting them into the breadboard.

### 7.2 BC547B lead identification

The supplied photograph shows a part marked `BC547 B`. With its flat marked face toward you and the leads pointing down, the onsemi BC547B TO-92 drawing numbers the leads from left to right:

1. Collector
2. Base
3. Emitter

Because parts from different factories can use different package drawings, verify the actual piece in diode mode before wiring:

1. Put the red probe on the centre/base lead.
2. Put the black probe on the left lead; expect a forward junction, commonly about 0.55-0.75 V.
3. Keep red on the centre/base and move black to the right lead; expect a similar forward junction.
4. Reverse the probes for both pairs; expect `OL`.
5. Record the readings and label the three leads `C`, `B`, and `E`.

Stop if the centre lead does not behave as the common base or if the result is ambiguous.

### 7.3 Fuse and holder

1. Remove the fuse.
2. Verify the fuse alone reads close to 0 ohm.
3. Insert it in the holder and verify the complete holder also reads close to 0 ohm.
4. Remove the fuse again until Gate F.

### 7.4 Capacitor

Identify the 100 uF capacitor:

- The long lead or `+` marking is positive.
- The stripe containing minus symbols marks the negative lead.
- Positive will go to the fused 5 V node.
- Negative will go to common ground.

Do not reverse it.

### 7.5 Indicator polarity

Do not rely only on wire colour. Preserve any manufacturer polarity marking. If the indicators are not marked, test them later through the extra 1 kohm series resistor, one at a time, and record which lead is positive.

## 8. Gate C: map the relay without power

1. Keep all five low-voltage relay screws disconnected.
2. Find the relay marked `K1` on the PCB.
3. Identify the adjacent three contact screws by their printed `NC`, `NO`, and `COM` labels.
4. With the relay de-energized, measure K1 `COM` to K1 `NC`; expect continuity or close to 0 ohm.
5. Measure K1 `COM` to K1 `NO`; expect `OL`.
6. Repeat three times while gently moving the meter probes, not the terminals.
7. Label the three wires before inserting them.
8. Set the `S1` jumper across `LOW` and `COM`.
9. Do not move S2 and do not connect CH2.

Stop if the contact truth table does not match. The measured contact behaviour is authoritative.

## 9. Gate D: prepare the breadboard control interface

The breadboard is used only for the transistor and its low-current resistors. Do not route the relay contact supply, a motor, a pump, or mains voltage through the breadboard.

1. Use the multimeter to map the MB102 rails. Some long power rails are split in the middle.
2. Select one rail as `CONTROL GND`. The existing 3.3 V splitter remains dedicated to P1 and P2 and is not extended onto the relay interface.
3. Connect Pi physical pin 25 to the `CONTROL GND` rail.
4. Confirm the existing physical-pin-17 splitter has only the two potentiometer high-terminal branches.
5. Confirm there is no continuity wire or jumper from the pin-17 splitter to the relay lower/control `COM`.
6. Leave the relay lower/control `COM` screw empty and label it `NO EXT WIRE`.
7. Insert the BC547B so collector, base, and emitter occupy three electrically separate breadboard rows.
8. Keep the flat face visible and label the rows `C`, `B`, and `E`.
9. Connect the emitter row to `CONTROL GND`.
10. Connect a 10 kohm resistor from the base row to the emitter row.
11. Connect Pi physical pin 16 / GPIO23 through the measured 1 kohm resistor to the base row.
12. Connect the collector row to relay `CH1 / IN1`.
13. Confirm relay lower/control `COM` is externally disconnected and S1 alone bridges `COM-LOW` on the module.
14. Leave `CH2 / IN2` empty.

Breadboard rule: holes in one five-hole strip are connected. No two transistor leads may share the same strip.

## 10. Gate E: build the fused 5 V branch with the fuse removed

Use secure screw terminals, lever connectors, or insulated splices for this branch.

1. Connect Pi physical pin 2 / 5V to the fuse-holder input.
2. Name the fuse-holder output `FUSED_5V`.
3. Connect capacitor positive to `FUSED_5V`.
4. Connect capacitor negative to the common ground node from physical pin 25.
5. Connect `FUSED_5V` to the labelled E-stop `NC2-A` terminal.
6. Connect `NC2-B` to relay `DC+ / VCC`.
7. Connect relay `DC- / GND` to the common ground node.
8. Connect `FUSED_5V` to K1 contact `COM`.
9. Connect K1 `NC` through a 1 kohm resistor to the red indicator positive lead.
10. Connect K1 `NO` through a 1 kohm resistor to the green indicator positive lead.
11. Connect both indicator negative leads to the common ground node.
12. Insulate every exposed conductor.

Only physical pin 2 supplies the new 5 V branch. Leave physical pin 4 unused.

## 11. Gate F: complete unpowered verification

Keep the fuse removed and the Pi unplugged.

### 11.1 Visual trace

Trace every new connection aloud from source to destination. Compare it with the diagram linked at the end of this SOP.

### 11.2 Required continuity checks

| Check | E-stop state | Expected result |
|---|---|---|
| Pi pin 2 to fuse input | Either | Continuity |
| Fuse output to `FUSED_5V` | Either | Continuity |
| `FUSED_5V` to relay `DC+` | Reset | Continuity through NC2 |
| `FUSED_5V` to relay `DC+` | Latched | `OL` |
| Pi pin 25 to relay `DC-` | Either | Continuity |
| Pi pin 25 to BC547 emitter | Either | Continuity |
| K1 `COM` to K1 `NC` | Relay unpowered | Continuity |
| K1 `COM` to K1 `NO` | Relay unpowered | `OL` |
| GPIO23 side of 1 kohm to BC547 base | Either | Approximately 1 kohm |
| BC547 base to emitter | Either | Approximately 10 kohm in the appropriate meter direction after allowing for junction effects |
| Pin-17 splitter to P1 and P2 high terminals | Either | Continuity to each potentiometer high terminal |
| Pin-17 splitter to relay lower/control `COM` | Either | `OL`; no installed conductor |
| Relay lower/control `COM` to `DC-` with S1 on `COM-LOW` | Either | Record the actual module-specific reading; do not use it as a power input |

### 11.3 Short-circuit checks

1. Confirm no steady near-zero resistance from `FUSED_5V` to ground. A capacitor can make the reading move briefly while it charges.
2. Confirm physical pin 16 has no continuity to 5 V.
3. Confirm physical pin 18 remains connected only to NC1-A.
4. Confirm physical pin 22 remains empty.
5. Confirm the capacitor stripe is on ground.
6. Confirm the E-stop NC1 sense pair and NC2 power pair have no cross-continuity.
7. Confirm physical pin 17 has no installed path to relay lower/control `COM`.

If any result disagrees, do not install the fuse and do not power the Pi.

## 12. Gate G: staged first power-up

No live wiring changes are allowed in this gate.

### 12.1 Pi-only baseline

1. Keep the 1 A branch fuse removed.
2. Reset the E-stop.
3. Power the Pi only through PWR IN.
4. Connect by SSH.
5. Confirm the host is healthy and run:

```bash
vcgencmd get_throttled
```

The preferred result is `throttled=0x0`.

6. Measure physical pin 2 to physical pin 25. Accept 4.75-5.25 V.
7. Shut down and remove PWR IN.

### 12.2 Relay-module characterization with contact load isolated

This gate resolves the remaining module-specific trigger ambiguity without energizing the indicator contact circuit.

1. With all power removed, disconnect and label only the wire from `FUSED_5V` row 12 to K1 contact `COM`. Leave the relay contact load isolated.
2. Disconnect CH1 from the BC547 collector at the relay screw. Leave the lower/control `COM` screw empty and S1 on `COM-LOW`.
3. Insert the verified 1 A fuse and latch the E-stop.
4. Power the Pi through PWR IN. Do not touch wiring.
5. Measure `FUSED_5V` to ground; accept 4.75-5.25 V. Measure relay `DC+` to ground; expect approximately 0 V while latched.
6. Reset the E-stop. Measure relay `DC+` to ground; accept 4.75-5.25 V. Confirm K1 does not click merely because module power was applied.
7. Measure lower/control `COM` to `DC-`, then CH1 to `DC-`, in DC-voltage mode. Record both values and the relay state.
8. Use a temporary measured 1 kohm resistor to connect CH1 to `DC-`. This is a current-limited low-trigger probe. Do not connect CH1 directly to a Pi rail.
9. If K1 clicks, remove the temporary resistor and confirm it releases. Record the module K1 LED and audible/mechanical response. The contact transfer will be verified later by the powered red/green indicator truth table; never use resistance or continuity mode on a powered circuit. If K1 does not click, remove power and report the readings; do not move S1 or try a 5 V drive without review.
10. Shut down the Pi, remove PWR IN, remove the fuse, and remove the temporary resistor.

The expected family-level behaviour in `COM-LOW` is that a low CH1 level energizes K1, but the measured response of this exact module is authoritative. This characterization must pass before the BC547 is reconnected.

### 12.3 Relay power with output forced safe

1. With power removed and the fuse removed, reconnect CH1 to the verified BC547 collector. Keep lower/control `COM` externally disconnected.
2. Keep K1 contact `COM` disconnected from `FUSED_5V` for the first transistor-controlled click test.
3. Confirm GPIO23 will be held LOW by the dedicated hardware test program before it is configured as an output.
4. Insert the fuse, latch the E-stop, power through PWR IN, then verify relay `DC+` is approximately 0 V.
5. Reset the E-stop and verify relay `DC+` is 4.75-5.25 V. K1 must remain de-energized while GPIO23 is LOW.
6. Run the purpose-built command test for one `permit` then `safe` cycle. K1 should energize only for `permit` and must release for `safe`.
7. Recheck `vcgencmd get_throttled`; preferred result remains `0x0`.
8. Shut down, remove PWR IN, and remove the fuse before restoring the K1 contact `COM` wire.

Stop immediately if the Pi resets, an undervoltage warning appears, the measured 5 V rail is below 4.75 V, the wrong indicator lights, the relay activates without a command, a wire becomes warm, or there is smell or smoke.

### 12.4 Integrated indicator command test

After the isolated relay-characterization and transistor-controlled click tests pass, restore `FUSED_5V` to K1 contact `COM` while power is removed. The integrated command test will be run through SSH with a purpose-built logger so each transition is timestamped. Do not manually connect GPIO23 to a power rail.

Expected behaviour:

| State | GPIO23 command | E-stop NC2 | Relay K1 | Red | Green |
|---|---|---|---|---|---|
| Boot or safe command | LOW | Closed | De-energized | On | Off |
| Valid permit | HIGH | Closed | Energized | Off | On |
| E-stop latched during permit | HIGH request | Open | Forced de-energized | On | Off |
| Broken NC1 sense wire | Blocked by software | Closed | De-energized | On | Off |
| Pi power lost | Undefined/unpowered | Unpowered | De-energized | Off | Off |

The final row is an important limitation: because the indicators share the Pi supply, neither indicator can remain illuminated after total Pi power loss.

## 13. Evidence to retain

Capture all of the following for the Phase 3 report and video:

1. BC547B marking and diode-mode readings.
2. Measured 1 kohm and 10 kohm resistor values.
3. K1 unpowered NC/NO continuity truth table.
4. S1 jumper close-up showing `LOW-COM`.
5. E-stop NC2 reset/latched continuity readings.
6. Labelled overhead photograph of the complete unpowered bench.
7. Close-up of Pi pins 2, 16, 17, 18, 20, 22, and 25.
8. Fused-node and relay-DC+ voltage readings in both E-stop states.
9. `vcgencmd get_throttled` before and after relay power is added.
10. Timestamped command, E-stop, broken-wire, restart, and safe-default logs.
11. A short video showing the physical action and corresponding dashboard/event state.

## 14. Stop conditions

Stop, remove PWR IN, and ask for review if any of these occurs:

- A terminal label cannot be read with certainty.
- The BC547B diode test is ambiguous.
- K1 COM/NC/NO does not match the unpowered truth table.
- GPIO23 has any path to 5 V.
- Fused 5 V to ground remains near 0 ohm.
- NC2 does not open when the E-stop is latched.
- The relay energizes at boot or with GPIO23 LOW.
- The Pi reports undervoltage, resets, or loses SSH when the relay changes state.
- Any component heats, smells, sparks, or behaves intermittently.

## 15. Immediate stopping point for the user

For the next interaction, complete only Gates A, B, and C. Do not connect the Pi, breadboard, or fuse yet. Send:

- BC547B diode-mode readings for base-to-left and base-to-right in both probe directions.
- K1 COM-NC and COM-NO readings with the relay unpowered.
- One close-up showing which S1 pins the jumper bridges.

After those three checks are reviewed, proceed to Gate D one wire at a time.

## References

- Raspberry Pi GPIO and voltage guidance: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio-and-the-40-pin-header
- onsemi BC546/BC547/BC548/BC549/BC550 data sheet: https://www.onsemi.com/pdf/datasheet/bc550-d.pdf
- Robu product page for the supplied relay module: https://robu.in/product/2-channel-relay-module-30a-5v-supports-high-and-low-trigger-optocoupler/

Relay-module instructions from marketplace and third-party listings were treated only as supporting information. The supplied PCB labels and the required meter tests are authoritative for this build.
