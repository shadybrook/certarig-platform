# CertaRig: cost reduction and eight rejection mitigations

10 November 2026. The user has removed the earlier Rs15,000 spending ceiling. Cost reduction remains desirable; no new budget ceiling or purchase authorization is inferred.

**Recommendation:** retain the selected low-energy pump/water-loop increment, commission one NC valve with real pressure/flow/temperature and measured electrical feedback, and complete the reviewed commissioning software. Reduce avoidable purchasing and choose electronics for the actual duty. The signed Phase3 report makes the reusable reviewed workflow the product; it does not require a larger or higher-pressure industrial rig.

## What the phase documents actually commit to

The retained Phase1 proposal and Phase2 final report were checked against their recorded hashes. The supervisor-approved signed Phase3 PDF was read directly, especially pages 3, 18–19 and 21. It is newer and more authoritative for the current capstone than the older retained Phase3 draft. Full paths/hashes are in `scope_trace.json`.

- Phase1 proposes four to five sensor channels, a normally closed solenoid valve and an optional pump/motor. It requires calibrated acquisition, a trustworthy system map, bounded plans, deterministic control, revalidation and independent safeguards.
- Phase2 develops the mapping, planning, refusal and evidence workflow. Its simulated valve-position input is not evidence of a physically instrumented valve.
- The approved Phase3 sets seven capstone missions: reviewed commissioning interview; a distinct second simulator; complete raw-data export; measured electrical feedback/current; live-provider qualification; broader observe-only connectors; calibrated sensing and protected actuation. Water-loop hardware is one validation case. An optional servo, expensive DAQ, high pressure, second physical rig or physical heater is not a minimum requirement.
- Keep position feedback explicitly unknown unless measured. Electrical current, load voltage and process flow do not establish mechanical valve-position accuracy. If a procedure or assessor requires that specific Phase1 objective, add actual position sensing or obtain an explicit approved scope variation.
- The fixture path remains useful, but live-provider qualification is still a separate outstanding mission. This review does not conduct or fund it.

## Cost options that preserve the selected workflow

The earlier Rs25,394.89 number was a candidate estimate including reserves, not a delivered purchase quote. It included an unconfirmed 30m hose minimum and a more expensive adapter; it already excluded the SEN0262 comparison board and expensive imported fuse-holder alternatives.

1. Quote only the required ~5m of matched reinforced hose. If supplied at the earlier per-metre rate, the planning saving versus the 30m roll is Rs1,770 including the previous conservative tax reserve. Offcut availability is unconfirmed.
2. A properly qualified Pro-Range 12V5A adapter was listed at Rs1,049 versus Rs2,713 for the Mean Well candidate: potential Rs1,664 saving. Exact variant, compliance, pump startup/current-limit behavior and delivered stock must be verified. Retain the better documented supply if the cheaper one cannot satisfy those checks.
3. Those two provisional substitutions alone give Rs21,960.89 on the OLD basket. The revised protection/power stage changes that total: its complete assembly cost is not yet quoted. This is not a firm Rs22,000 offer or a new agreed cap.
4. Use the existing Pi/ADS1115/tool inventory after checking what is still available; keep the Phase3 card and evidence intact. Consolidate shipping and buy a matched fitting schedule rather than spare incompatible adapters. Calibrated institution-owned references can replace purchases only after actual access is confirmed.
5. A gravity-fed water test is a lower-complexity alternative permitted by the optional-pump proposal, but it requires its own pressure range, flow and transient review. It is not an automatic replacement for the user-selected pumped loop. Do not delete independent pressure protection merely because static head is low.

A one-direction on/off stage fits this duty better than an H-bridge. This is a functional/thermal improvement, not a verified cost saving until the complete driver, soft-start protection, shunt, thermal mounting and assembly are priced. Keep references, fuses, independent cutoff, pressure protection and enclosure in the quote.

## What the eight rejections mean

They are eight deliberately adverse scenarios, not eight physically broken products. The original unsafe experiments remain unchanged and still reject. The paired mitigations below demonstrate either successful operation under stated bounds or correct fault containment/refusal. An open resistor must not be relabelled as a healthy sensor.

### 1. Receiver fault above 3.3V input budget

**Mitigation tested:** Use the bounded protected 100ohm receiver and correct full-network scaling. The 33mA observation is invalid and must refuse execution.

**Evidence:** `sen0262_burden_33mA_fault` remains rejected; `receiver_33mA_contained_refusal` passes its declared mitigation checks.

**Still required:** The current-limit dynamics, clamp, power-good timing and actual PCB still need qualification.

### 2. Back-powering an unpowered Pi/ADC

**Mitigation tested:** Isolate the signal when the ADC rail is absent, discharge the ADC pin, and reject the observation.

**Evidence:** `unprotected_receiver_pi_off` remains rejected; `receiver_pi_off_isolated` passes its declared mitigation checks.

**Still required:** Actual power-off switch timing, rail sequencing and leakage require component/board verification.

### 3. Insufficient 12V loop compliance

**Mitigation tested:** Retain a separate 24V instrument supply; 21.6V and 26.4V corner checks also pass.

**Evidence:** `nishka_12V_insufficient_compliance` remains rejected; `receiver_24V_fullscale` passes its declared mitigation checks.

**Still required:** Confirm the exact transmitter revision, supply regulation and its calibration. This is not the actuator supply.

### 4. Open/missing receiver burden

**Mitigation tested:** Contain the input voltage and detect the invalid calibrated reading. Keep authority refused after the signal recovers until an explicit reset. Restore the resistor and requalify before running.

**Evidence:** `missing_burden_protected` remains rejected; `receiver_burden_open_refused` passes its declared mitigation checks.

**Still required:** A missing resistor is not made healthy by software. The guard exercised here is an offline reference, not deployed Edge integration.

### 5. DRV8871 advertised as 3.6A continuous

**Mitigation tested:** Use a one-direction power stage appropriate for an on/off pump/solenoid. A 0.154ohm hot bound and mounted thermal path no worse than 20C/W give 89.9C at 3.6A/50C ambient in the thermal analogy.

**Evidence:** `drv8871_3.6A_continuous_claim` remains rejected; `unidirectional_stage_3.6A_thermal` passes its declared mitigation checks.

**Still required:** Vishay IRL540 0.077ohm at 5V gate is the reference; 2x hot multiplier and 20C/W are design bounds, not measured assembly properties. Gate drive, SOA, suppression and heatsinking remain to qualify.

### 6. Hot-board driver thermal failure

**Mitigation tested:** The same one-direction stage gives 56.9C at 1.5A and 50C ambient under those declared thermal bounds.

**Evidence:** `drv8871_1.5A_hot_board_bound` remains rejected; `unidirectional_stage_hot_1.5A` passes its declared mitigation checks.

**Still required:** The DRV8871 control remains rejected. This demonstrates a different candidate design, not a retrofit qualification of that board.

### 7. Weak supply/wiring during startup

**Mitigation tested:** Specify adequate supply and total wiring/contact impedance, current-limit startup and sequence the valve after the pump settles. A 0.3ohm source envelope passes the previous weak-source startup test.

**Evidence:** `pump_weak_supply_startup` remains rejected; `supply_10.8V_0.3ohm_3x_start` passes its declared mitigation checks.

**Still required:** The new weak-source scenario deliberately latches a refusal. Actual adapter current limit, wiring resistance and pump startup must be measured; nameplate wattage alone is insufficient.

### 8. Startup trips the old 2.5A latch

**Mitigation tested:** Use bounded soft start/current limiting; measure pump current across a correctly sized 50milliohm shunt; retain a 5A fast veto plus an approximately 80ms sustained-overload timer above 2.5A. Add output discharge and reset-required fault latching.

**Evidence:** `integrated_unknown_startup_trip` remains rejected; `softstart_3A_100uF` passes its declared mitigation checks.

**Still required:** The 50milliohm circuit requires a suitable precision power shunt, Kelvin wiring and recalibration; an untouched R100 INA219 board is not this circuit. Actual eFuse SOA, fast response and pump internals remain unqualified.

## New simulation evidence

The new ngspice47 batch contains 31 experiments: 8 rerun original rejection controls and 23 revised normal, calibration, containment, fault and refinement cases. All 31 match their stated criteria. The original 39-experiment review is preserved separately. This is an additional batch, not 31 newly qualified physical devices.

The revised startup envelope tests a 10ms controlled target rise, 4A nominal current limit with +/-8% corners (3.68–4.32A), a 5A fast veto and an approximately 80ms sustained-overload timer above 2.5A. The valve is enabled after the pump startup window and inhibited immediately during pump overcurrent; this keeps the combined supply draw bounded even at the high current-limit corner. The new startup block does not include the whole relay/watchdog architecture; an independent upstream cutoff remains required. A 50milliohm pump shunt keeps the modeled current signal inside the INA219 +/-320mV range; the stock 0.1ohm board requires replacement/modification, Kelvin wiring, power derating and recalibration. Fast cutoff is independent of ADC/software reporting.

The reference receiver guard reconstructs current from the whole 10kohm/33kohm/ADC input network. Simply dividing ADC voltage by 100ohm would be wrong. Overrange, power-off and open-burden observations refuse authority; a restored good reading does not clear the reference trip latch until explicitly reset. This guard is an offline reference exercise, NOT deployed Edge behavior or a human approval grant. The actual runtime still needs integration and acceptance tests against the reviewed configuration.

A switched 47ohm discharge path removes residual output-capacitor charge after cutoff. Its transistor, resistor pulse rating, isolation and backfeed behavior require actual component design. The input supply is assumed settled before permit; adapter hot-plug and its own rise/foldback are not qualified by this model.

Crucially, the eFuse is a behavioral envelope inspired by TI TPS25940L functions, not a vendor macromodel. Fault/starting energy is reported but **not accepted against an invented silicon safe-operating-area (SOA) limit**. The shorted-output model dissipates about 0.42J in the modeled pass element before latching; normal startup also has finite energy. Device SOA, transient thermal behavior and the actual PCB must support the complete voltage/current/time waveform before this becomes a hardware-ready fix. If they do not, change the controller/FET, reduce fault energy or change the timing and rerun.

The MOSFET thermal comparison uses Vishay IRL540's 0.077ohm maximum at 5V gate, an explicitly assumed 2x hot multiplier and a required effective mounted thermal resistance <=20C/W. It is not an assertion about a purchased board's cooling, linear-mode SOA or real trip latency. The named Vishay IRL540 must not be silently replaced with another manufacturer's IRL540N based on its name.

No physical pressure setpoint is frozen. Valve water compatibility, zero-differential operation, Kv, coil behavior and pressure-protection capacity still need exact documentation. Air-only valves remain rejected; conflicting pressure-sensor transfer sheets require clarification or a different part. Stock failures require another available seller/part; simulation cannot establish availability.

## Exact next work

1. Retain the full pump-loop as the preferred scope; price its matched design rather than targeting the obsolete Rs15,000 ceiling. Keep the gravity-fed design as an explicit alternative.
2. Finish exact water-valve and pressure-protection selection and resolve pump revision/inrush data. Earlier supplier questions remain unsent; this review sends nothing externally.
3. Freeze a construction-level power/receiver/feedback schematic and quote its whole assembly, including the startup/discharge changes. Check SOA and measured-signal ranges before selecting parts. Configuration/calibration changes invalidate old approvals and qualification evidence.
4. Integrate the tested refusal/reset reference into the actual readiness/control path, together with exact-profile twin qualification and fresh human approval. Repeat scenario tests for the actual model/parts and retain both success and refusal evidence.
5. Finalize the delivered basket, then carry out attended dry feedback, passive leak/mechanical, read-only sensing, calibration and protected actuator commissioning gates. A board-level simulation is not physical acceptance.

## Replay

`python3 run_closure.py verify .` replays checks from the recorded samples without ngspice or API access. With ngspice installed, use `python3 run_closure.py run /absolute/path/to/a/new-folder` for a fresh matrix. Python standard library only. Exact netlists, logs and compressed traces are under `cases/`; the manifest proves consistency, not independent authenticity. `verification_checks.json` records offline replay, corruption rejection and refinement checks.

GBrain tools were unavailable. The review uses the local documents and source plus manufacturer information. Restarting Codex may load the registered GBrain server. No hardware was operated, purchased or changed; no paid model was used.
