# Water-loop design and procurement review — HOLD

9 November 2026. Budget ceiling ₹15,000 including delivered parts, protection, references and fittings. No orders placed. This is a concrete candidate design and sourcing record, **not yet a purchase-ready basket**: the transducer specification conflicts with itself, the matched zero-differential valve/pump lack a delivered Indian quote, reference/protection parts remain unpriced, and current as-built wiring needs review. Buying a collection of cheap substitutes would not complete this design.

## What to obtain now

One separate 32 GB microSD card for capstone development. Keep the existing Phase 3 card and wiring intact. Reuse the owned Pi, ADS1115 boards, controls and tools after an inventory check. Do not connect new motors to the old 5 V indicator circuit.

## Matched architecture to review

Open reservoir → flooded-suction 12 V pump → pressure tee (transducer + reference + independently effective protection) → split. Branch A is a permanent unobstructed return/bypass to the reservoir. Branch B contains pulse flow measurement and a spring-return normally closed, zero-differential direct-acting valve → reservoir. Temperature probe stays immersed at a documented location. All wet parts sit in a containment tray; pump stays below the minimum water level. No heater, sealed reservoir, compressed gas or deliberate dead-head test.

Separate fused actuator supply → independent manually reset emergency cutoff → protected pump and valve drivers. A single deterministic permit enables the power stage. Safe removes pump power and deenergizes the NC valve. Pi and sensor recording stay powered separately. Record command, measured switched-load voltage/feedback and current separately. The existing Pi GPIO is a control signal only; it cannot power a pump or coil. Suppression, supply transient control, wire/fuse sizing and DC contact ratings must match the actual loads. New pin assignments and a wiring schedule are withheld until the as-built check; distinguish BCM from physical header numbers.

A permanent bypass reduces normal back-pressure but does not replace independently effective pressure protection. A low-head centrifugal pump is preferred to a high-pressure diaphragm pump. A higher advertised working pressure is not permission to raise the operating target.

## Candidate basket and sourcing decisions

Prices below are visible listing observations, not delivered quotations. Stock, tax, delivery and exact variants need checkout/supplier confirmation. Budget allocations later in this document are **not** vendor quotes.

| Item / quantity | Exact candidate / interface | Evidence and decision |
|---|---|---|
| Pump ×1 | TOPSFLO TL-B10-A12-0703, 12 V, nominal 7 W/0.6 A, low-head flooded suction | Manufacturer sheet lists 3 m maximum head and 7 L/min maximum flow, different curve endpoints. Indian delivered price/availability and connection variant unverified. HOLD pending quote/curve/port drawing. Do not substitute the B12-0905 5 m, 16.6 W version silently. |
| Valve ×1 | FESCOLO 2W025-08, DC12V, NC direct acting, NBR, 1/4 inch PT; final coil/connector suffix on quotation | Manufacturer catalog shows water from zero differential, 2.5 mm orifice, Cv 0.23. This is a small restrictive valve, compatible with a low-flow branch in principle. Coil current/duty, exact thread, closure behavior, Indian availability and price need confirmation. HOLD. A generic part marked 2W025 is not proof it is this manufacturer's variant. |
| Pressure transmitter ×1 | PR19C-PA-050K, nominal 0–50 kPa gauge, G1/4, 10–32 V, 4–20 mA | Robu category lists ₹2,539. **HOLD:** supplier PDF says 0–50 kPa but table maps 20 kPa to 20 mA. Need corrected signed range/transfer/accuracy and wet-media compatibility. No calibration coefficient may be derived from the conflicting sheet. |
| Flow ×1 | YF-S302, nominal G1/4, 0.3–6 L/min pulse output | Zbotic listing ₹297.36 including GST; generic-brand listing is not manufacturer traceability. Confirm exact supply/output levels, pulse curve, pressure and threads. Budget pulse conditioning and timed-volume calibration. Do not feed a >3.3 V pulse directly to Pi. HOLD until exact variant confirmed. |
| Temperature ×1 + reference ×1 | Genuine DS18B20-based water-compatible probe; separate reference thermometer | Sensor electrical interface supported in code, but probe sealing/material, supplier, reference uncertainty and cost not verified. HOLD. 1-Wire IDs and conversion cadence must be recorded. |
| Current ×1 / voltage feedback ×1 | INA219-based shunt monitor sized to measured pump/coil currents; independently conditioned switched-load voltage/GPIO feedback | TI supports the chip function; a generic board does not establish shunt rating or isolation. Module/shunt tolerance, common mode and interface must be reviewed. Additional current/voltage comparison against a reference meter required. HOLD. |
| Pressure reference/protection ×1 each | Low-range water-compatible reference gauge or reviewed water-column reference; independently effective low-pressure protection with return to open reservoir | Exact models, resolution, uncertainty, setpoint tolerance and flow capacity unverified. This is a major Gate A hold. A 0–10 bar gauge is poorly matched to a sub-bar experiment. |
| Electrical protection set ×1 | Enclosed certified low-voltage supply, branch fuses, DC-rated manually reset cutoff/contactor, suppression, protected drivers, 3.3 V interfaces, terminals/enclosures | Select after pump/coil normal and start/stall current are confirmed. Existing relay indicators are not accepted power protection. No mains fabrication instructions or unverified ratings supplied. |
| Plumbing set ×1 | Water-rated compatible tubing/barbs/tees/clamps/seals, permanently open bypass, reservoir, containment tray and secure mounting | Match actual PT/BSP/NPT threads with documented adapters; never force unlike threads. Count from approved layout and obtain delivered quotation. |
| Development storage ×1 | Separate 32 GB microSD | Obtain now; image for capstone only after preserving Phase 3 card. |

Rejected examples: DFRobot FIT0498 specifies a minimum 0.02 MPa (0.2 bar), so it is unsuitable as an assumed zero-differential valve. FIT0616/FIT0617 motor valves retain their state on power loss and do not satisfy deenergize-to-close. A generic 0–5 bar transducer and broad-range gauge would compromise low-pressure measurement resolution. These are explicit rejection reasons, not recommendations.

## Gate A pressure and uncertainty worksheet — complete before ordering

No operating pressure or executable physical trip is frozen in this pack. The simulated 4.2 bar threshold is irrelevant to the water-loop limit. A 3 m water head corresponds to roughly 0.29 bar static pressure by rho*g*h, but that endpoint is not a certified overpressure protection specification.

For each wet component record manufacturer, exact variant, permitted continuous pressure at room-temperature water, derating, fittings, burst/proof figures separately, flow restriction and pressure transient exposure. Then select operating limit < software trip < independent protection setting < weakest permitted working pressure, with explicit margin for sensor error, calibration uncertainty, protection tolerance, transient overshoot and elevation. Overlapping uncertainty intervals mean redesign, not rounding down the claim.

Pressure calibration: zero, multiple ascending/descending reference points within the proposed range, repeatability and hysteresis. Record reference uncertainty, height offsets, raw ADC voltage/current and fitted coefficients. A reviewed 150 ohm precision burden would nominally convert 4–20 mA to 0.6–3.0 V, **only a design candidate**: check worst-case loop current, resistor tolerance/power, wiring faults, supply compliance and clamps before selecting. A 3.3 V ADS1115 input must remain within its supply rails in normal operation; the PGA range does not confer overvoltage tolerance.

Flow calibration: collect a measured volume/mass over timed intervals at multiple operating flows; record pulse count, zero-flow behavior, repeatability, timer/volume uncertainty and pulses/litre. Distinguish zero pulses from a lost sensor. Current: compare zero and several loads with a reference instrument; preserve shunt voltage and resistance. Temperature: compare reference points and document immersion and response delay. Electrical feedback: test safe/commanded states and stuck/missing feedback using a reviewed low-energy fixture before wet operation.

## Budget allocation (planning ceilings, not a total quote)

| Group | Allocation |
|---|---:|
| Separate storage | ₹800 |
| Pump, NC valve and protected drivers | ₹2,200 |
| Pressure transmitter and reference | ₹3,000 |
| Flow, temperature and current instrumentation | ₹1,800 |
| Supply, independent cutoff, fuses and interfaces | ₹1,600 |
| Plumbing, bypass/protection, tray and mounting | ₹2,000 |
| Spares and delivery | ₹1,600 |
| Target | ₹13,000 |
| Contingency | ₹2,000 |
| Absolute ceiling | ₹15,000 |

These ceilings may be inadequate for traceable pressure protection/reference and a proven spring-return valve. Obtain the complete revised basket before committing any actuator purchase. If quotes exceed ₹15,000, defer the wet-loop build and complete dry measured-feedback work while reviewing a revised design; no silent removal of protection or reference measurement.

## Supplier inquiry draft — not sent

Please quote one exact 12 V NC direct-acting zero-differential water valve (2W025-08 candidate), with manufacturer datasheet, port standard, coil current/duty and spring-return behavior; one TL-B10-A12-0703 pump with actual curve/ports and supply-current limits; and a traceable 0–50 kPa water pressure transmitter. For PR19C-PA-050K, please resolve the 0–50 kPa label versus 0/10/20 kPa transfer table in your PDF. Include GST, shipping, stock, lead time, reference/protection recommendations and delivered total. No substitution without review.

## Gates B/C and attended sessions

Before wiring: current photographs and continuity schedule; freeze exact circuit, source identities, scaling, GPIO/I2C allocation, cutoff contact ratings and protection. Dry electrical feedback first. Passive leak/mechanical checks next. Then read-only sensing, calibration, protected actuator trial, integrated procedures. Use short attended cycles before the final 60-minute acquisition session. E-stop must physically remove actuator power while Pi records; release requires reset and fresh permit. Capture raw evidence, timing intervals and uncertainty. Electrical current does not prove valve position; flow establishes process response. No physical commissioning result is claimed yet.

## Sources inspected 9 November 2026

- TOPSFLO original pump sheet: https://m.topsflo.com/d/files/tl-b10h-topsflo-brushless-dc-pump.pdf
- Robu alternate TL-B10 variant sheet (not interchangeable): https://robu.in/wp-content/uploads/2025/11/Micro-DC-Brushless-Water-Pump-TL-B10-1-2.pdf
- FESCOLO original valve catalog: https://www.fescolo.com/uploadfile/2017/0406/20170406035327750.pdf
- Conflicting pressure sheet: https://robu.in/wp-content/uploads/2025/06/R222349-PR19C-PA-050K.pdf ; price category https://robu.in/product-category/pro-range-pressure-sensors/
- Flow manufacturer https://sunwoald.com/flow-sensor/plastic-flow-sensor/yf-s302/ ; listing https://zbotic.in/product/water-flow-sensor-sea-yf-s302-flowmeter-g1-4-0-3-6l-min-5-24v/
- TI ADS1115 Rev E, especially recommended operating conditions: https://www.ti.com/lit/ds/symlink/ads1115.pdf
- TI INA219: https://www.ti.com/product/INA219
- Valve guidance: https://www.burkert.com/en/products/solenoid-valves
- Rejected minimum-pressure valve: https://www.dfrobot.com/product-1530.html ; state-retaining valve https://wiki.dfrobot.com/fit0617/

The canonical dry circuit is docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.svg. It is historical reference, not the new power-stage design. The next Gate A revision needs current photographs and supplier answers before an exact signed wiring/purchase pack can be issued.
