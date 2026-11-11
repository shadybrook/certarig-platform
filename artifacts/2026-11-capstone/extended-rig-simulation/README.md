# CertaRig R1 electrical simulation evidence

9 November 2026. **48 required scenarios pass; 6 deliberately unsafe comparison cases are detected.** All accepted runs reached their requested end time. ngspice 47 performs the electrical solve; Python generates cases and evaluates sampled results. Numerical failure is an invalid experiment, never a successful fault detection.

This validates a declared candidate model envelope. It does not validate a selected-parts assembly, certify a safety function, release a purchase basket, or qualify the physical water loop. The original Phase 3 circuit/card and historical evidence were not changed or operated.

## Open the results

- `CertaRig_Circuit_Simulation_R1.pdf`: four rendered sheets, including candidate circuit diagrams, findings and waveforms.
- `02-power-schematic.svg` and `03-sensor-schematic.svg`: editable vector circuit drawings.
- `summary.json` and `scenario-results.csv`: checks, measurements and expected failures.
- `cases/<scenario>/circuit.cir`, `ngspice.log`, `trace.csv.gz`, `result.json`: exact numerical evidence.
- `SHA256SUMS`: evidence-file integrity, not an external authenticity signature.

These diagrams use model node names rather than Raspberry Pi header/terminal pin assignments. They are candidate simulation schematics, not a construction wiring schedule. Complete netlists are the authoritative circuit topology for these experiments. The prior R0 functional diagrams are retained separately and are superseded for the modeled portions only.

## Reproduce and verify

Requires Python standard library and ngspice 47 on PATH; no paid calls or physical I/O.

```sh
python3 run_spice.py --out ./fresh-run
python3 verify_evidence.py .
```

A fresh run solves all circuits. `--select receiver` limits scenarios. `--reuse` replays complete traces only when the engine version and exact generated netlist match; partial/nonfinite/nonconverged traces are excluded. A selected subset is not the complete gate. The supplied summary contains all 54 scenarios.

Offline verification hashes the manifest's files and recomputes all reported metrics and acceptance decisions from the saved samples. It does not solve SPICE again or independently qualify the behavioral IC models. Manifests cannot establish authenticity if both data and manifest are deliberately replaced.

## Problems found and revised candidate

1. **12 V + 150 ohm burden:** the proposed transmitter needs at least 10 V. The burden would consume 3 V at 20 mA, leaving only 9 V. A compliance-limited transmitter model cannot reach the requested current. R1 uses 24 V +/-10% instrumentation and a 100 ohm burden. At 20 mA the minimum-supply margin, including 45 ohm protector resistance and 100.1 ohm burden, is 21.6 - 10 - 0.020*(45+100.1) = 8.698 V before cable loss. This is an arithmetic bound; the circuit model uses 25 ohm protector resistance.
2. **ADC overrange / off-state backfeed:** unprotected 150 ohm inputs exceed normal rail range at 24 mA and backfeed the unpowered ADC. R1 adds a 33 mA upper-bound loop protector, 10 kohm series resistor, 2.5 V shunt-reference clamp, 10 nF filter before the isolator, power-off-protected switch, 33 kohm pin discharge and 10 pF ADC-side equivalent. The persistent discharge resistor attenuates the input; it must be included in end-to-end calibration.
3. **Inductive turn-off:** unclamped negative control reaches the **assumed 100 V avalanche envelope**. R1 uses an opposed rectifier/20 V avalanche equivalent across each load. An actual TVS part must be selected by its clamp curve at the measured current, not by its name or nominal voltage. The 70 V acceptance ceiling is a model design criterion, not a device qualification.
4. **Restart authority:** deliberately unsafe automatic-arm logic restarts after E-stop release; R1 requires a new reset edge with permit low, healthy heartbeat and valid power supplies. Lost heartbeat or power clears the arm state. An E-stop held/reset-held/stuck-command test is included.
5. **Fault boundary:** a shorted output MOSFET alone and a welded permit contact alone are contained. Their combination fails the permit-off check and is deliberately recorded as an unsafe diagnostic. The separate E-stop cutoff test removes current under that combination. No general multiple-fault tolerance is claimed.

## Electrical model assumptions

- Actuator source: 10.8-13.2 V, 0.3 ohm source/wiring resistance; ideal-voltage-source supply beyond that. No actual SMPS current limiting, fuse I-t curve or connector heating is modeled.
- Pump: 20 ohm / 10 mH RL surrogate. This is **not** a selected brushless pump's electronic startup or hydraulic model. Valve: nominal 24 ohm / 200 mH; load corners 15-40 ohm / 50-500 mH.
- Per-load switch: 0.10 ohm ON, 1 nF output capacitance; 100 V generic avalanche path. Model gate: 5 V driver, 50+100 ohm series, 47 kohm pull-down, 3 nF capacitance. These are requirements/equivalents rather than a selected MOSFET/driver.
- K0 is a contact equivalent; the permit contact uses continuous conductance transition to avoid a numerical discontinuity. Deliberately unprotected comparisons also use a continuous K0 transition. RC relay-equivalent delay is about 10 ms; contact bounce, welding probability and coil-driver electronics are not modeled.
- Fast overcurrent: 0.05 ohm low-side shunt, nominal 4 A threshold, bounded RC latch and gate veto. The shunt measures switch current, **not the full flyback recirculation tail**. Real comparator tolerance, shunt pulse rating, MOSFET SOA and fuse coordination remain unqualified.
- Arm/reset/watchdog/rail-good are explicit RC-state plus behavioral logic equivalents. Hardware implementation, IC pin-level power sequencing and GPIO command translation are not complete. Watchdog envelope is 150-250 ms. No software-generated expected waveform is substituted for the electrical solution.
- ADC model: 6 Mohm effective input, 10 pF and ESD diodes; not a TI ADS1115 sampling/accuracy macromodel. Normal valid readings must remain within supply rails; fault transients are checked against GND-0.3 V / VDD+0.3 V. Rail-off cases include 100 us and 1 us fall times. The post-settling injection limit is 1 uA; brief turn-off injection is retained separately and is not claimed to be below 1 uA.
- Current-loop protection is a bounded equivalent inspired by MAX14626: 33 mA worst high limit, reverse blocking, 25 ohm modeled series resistance. No transistor-level thermal shutdown, surge/EMC or specified reverse leakage model. Short-transmitter current limiting is bounded, not device-certified.
- ADC power-off isolator equivalent: 4.5 ohm ON, conservative 2 uA off leakage, opens below 3.0 V ADC / 4.5 V conditioner power-good. Hardware thresholds and actual reference accuracy need selection. TMUX1511 is a candidate, not a finalized board.
- Flow optocoupler interface: 4.5-5.5 V, 560 ohm LED resistor, CTR 0.2-2.0, 10 kohm/1 nF logic pullup, 500 Hz test signal; voltage feedback uses 1.8 kohm LED resistor. Source is a driven pulse equivalent; the actual sensor output type/drive capacity remains unconfirmed. No pulses cannot distinguish true zero flow from broken wiring. A broken voltage-feedback channel stays high; the simulated receiver makes the disagreement observable but does not include a software feedback-trip controller.
- Default maximum power step 100 us; E-stop and short-load repeats use 20 us. The short-load repeat uses first-order integration to check the switching case. This checks numerical robustness only; it does not validate the assumed component models.

## Measured electrical gain and limits

The nominal 4 mA ADC voltage is 0.305838971 V and the nominal 20 mA voltage is 1.529191036 V. These are simulated circuit gain points; **no pressure calibration** is claimed. The candidate pressure sheet still conflicts between its 0-50 kPa label and a table ending at 20 kPa; do not encode a physical pressure range until resolved.

## Next engineering work

1. Select and verify exact pump/valve/sensor variants and output types. Resolve the pressure range discrepancy. Match the operating limit, protection setting, uncertainty, fittings and reference instrument.
2. Replace behavioral power-good, watchdog, latch, comparator, driver and isolation blocks with reviewed actual components and pin-level netlists. Validate GPIO/I2C/backfeed paths and tolerances. Re-run the changed model.
3. Review as-built bench photographs and continuity, issue a terminal-by-terminal wiring schedule and complete the delivered <=INR15,000 basket before purchase. Do not reuse the old 5 V indicator circuit to power actuators.
4. Perform unpowered electrical checks, dry electrical-feedback trials, passive leak checks, read-only sensing/calibration and attended protected actuator trials. Physical commissioning and a 60-minute acquisition run remain outstanding.

## Primary constraints consulted

- TI ADS1115 Rev E, recommended/absolute input limits and input equivalent: https://www.ti.com/lit/ds/symlink/ads1115.pdf
- ADI MAX14626 Rev 2, current limit, resistance and reverse-input protection: https://www.analog.com/media/en/technical-documentation/data-sheets/MAX14626.pdf
- TI TMUX1511, powered-off protection and on-resistance: https://www.ti.com/product/TMUX1511
- TI LM4040, reference candidate; generic reference model used: https://www.ti.com/lit/ds/symlink/lm4040.pdf
- TI INA219, current acquisition candidate; no INA219 internal model: https://www.ti.com/lit/ds/symlink/ina219.pdf
- Candidate sensor sheet, conflicting physical transfer specification: https://robu.in/wp-content/uploads/2025/06/R222349-PR19C-PA-050K.pdf
- ngspice documentation: https://ngspice.sourceforge.io/docs.html

GBrain tools were unavailable; the local project evidence and primary sources were used. Restarting Codex may load the registered server. No knowledge was written to GBrain or to the memory registry.
