# CertaRig extended bench | CR-EXT-R1

Dated10 November2026. Frozen requirements for sourcing; supplier-specific acceptance remains mandatory.


## What this order covers

One attended, recirculating room-temperature water bench with measured electrical and process response, protected actuation and retained evidence. It extends the preserved dry bench and supports the signed Phase3 capstone direction. The thermal plant remains a distinct simulator; no physical heater is ordered.


## Order status

CR-EXT-R1 is the final requirements and quantities list for sourcing. Availability and price do not change these requirements. It is not an unconditional purchase release for an unknown supplier assembly. S01/S02/S03 are finished engineered assemblies, including internal design, parts, fabrication, firmware and factory tests. A qualified builder must return actual schematics/BOM and a compliance matrix before their fabrication PO is released. No payment or order has been made.


## Design envelope

12V bounded centrifugal pump;24V true zero-differential NC valve with mechanical CLOSED feedback;3L preferred working inventory in a5L vented reservoir. Normal pressure<=0.12bar, software trip0.15bar, independent pressure switch0.25+/-0.02bar; relief cracks0.30+/-0.03bar and passes10L/min by0.45bar. Pump shutoff head<=0.60bar. These are not a4.2bar demonstration target.


## Why the pump and returns are matched

Pump free flow7–10L/min, >=6L/min at0.03bar and>=1L/min at0.12bar, with the full10.8–13.2V curve supplied. The complete permanent bypass must pass>=10L/min at0.10bar. A hose diameter alone does not establish this capacity. The branch is factory locked/calibrated at0.50–0.70L/min at0.10bar, <=1.5L/min at0.45bar and<=2L/min at0.60bar. Verify normal-pressure points on this bench; do not bypass its trips to set a higher-pressure calibration point.


## Power-up and authority sequence

Keep permit LOW. Healthy independent loops, two heartbeat edges and manual RESET arm the mechanical cutoffs. Then wait up to1.1s for S01 insertion/READY. READY cannot be a prerequisite for closing the cutoffs that power S01. READY must be observed with permit LOW before a fresh execution-permit edge is accepted. An early or held permit cannot start when READY appears. A READY timeout/loss during execution trips; recovery requires reset and a new application approval.


## What is independently measured

Two isolated bidirectional Hall current channels measure actual load conductors. Separate protected differential voltage channels measure across pump and valve, including negative valve flyback. Mechanical CLOSED feedback is an actual valve accessory, not inferred from current. Water flow measures process response. None alone proves seat sealing or precise relay/valve mechanical timing.


## Acquisition and refusal

At least100 source-timestamped samples/s per pressure/current/load-voltage channel, using two field ADCs and a documented conversion schedule. Pressure/current/voltage age>200ms, counter heartbeat>200ms, or temperature age>2s is invalid. Flow frequency can legitimately be zero with a healthy supervised acquisition source; use a>=2s rolling count interval and report quantization. Missing expected response after3s or CLOSED disagreement beyond1s trips according to the reviewed procedure; current thresholds remain blocked until measured commissioning baselines exist.


## Simulation result and limits

47 completed ngspice experiments, 6 RK4 hydraulic transients, 21 temporal safety/ready cases and 42 calculated checks form this revision. Unsafe controls are expected rejections. Full-horizon, finite-trace and saved-sample checks are mandatory. These are module-equivalent models, not manufacturer IC models, identified pump curves, CFD, valve mechanical models, EMC tests, or certification of an unknown PCB.


## Remaining supplier-specific verification

No declared model experiment is left failing after the stated mitigations. The actual S01 gate/choke overshoot, input hot-plug/reverse behavior, S03 differential/Hall conditioner and power-off component design, S02 relay wiring/contact timing, actual fuses, valve suppression/low-head closure and arrestor/relief curves are not component-level qualified yet. These cannot be completed from an unspecified supplier schematic. Obtain Q01 drawings and exact article data, check them against this pack, rerun affected electrical/hydraulic cases, then release the custom fabrication PO. A supplier claiming compliance without those records does not close this gate.


## Pressure transients

The minimum-compliance reduced branch model peaks near0.759bar; with failed arrestor and the required50ms valve closure it peaks near1.174bar. This pressure may exceed the ordinary trip thresholds briefly; neither ADC polling nor the pressure switch is claimed to stop a fast wave. Passive arrestors and the closing-time bound protect that transient. Fast1ms closure plus failed arrestor is deliberately rejected at about14.18bar before cavitation; the negative model stops at203.2ms before leaving its single-phase domain. It is not an acceptable dual-fault operating condition.


## Electrical and thermal bounds

Main regulator power<=25W, fault interval<=60ms and case<=75C give a78.5C junction bound under the specified thermal path. Short overshoot is a separate procurement bound <=8A, <=20us, VDS<=30V; its real waveform must meet datasheet FBSOA. Worst specified valve stored energy is1.8J, so suppression requires>=5J with its real pulse-duration/temperature curve. Use30W maximum heat-to-water, not only pump heat. At ambient30C and3L, the60min energy model remains below40C. At2L or ambient35C, a temperature trip can be required;60min acquisition does not mean60min continuous actuation.


## Measurement uncertainty

A0–2bar transmitter at0.25%FS contributes0.005bar; a0.002bar reference gives about0.0054bar by RSS before height, calibration fit and temperature effects. A1cm water height is about0.00098bar. Record sensor heights. Example1L/120s flow reference with10mL volume,0.2s timing and1count/1000pulse uncertainty gives about1.02% RSS before repeatability and calibration-fit contributions. These are uncertainty-budget examples, not measured performance.


## Preservation and software work

Keep the original Phase3 card, harness and historical evidence intact. Use a separate development card and new documented harness. Next code increment: read-only mixed-sensing adapter with timestamps/quality, supervised counter protocol and explicit load feedback; local trip latch/ready handshake; commissioning/calibration provenance and configuration-hash binding; approval/revalidation and complete evidence replay. Firmware and adapter integration are required before physical commissioning; this pack adds offline validation tools, not deployed control code.


## Genuine release tests after delivery

Passive continuity/polarity/ground/isolation checks; unpowered contact/EDM tests; sensor reference comparisons; passive leak test with pressure-limited calibrated source; supervised read-only acquisition; output tests into dummy loads; low-pressure attended pump/valve trials; repeated E-stop/no-auto-restart and source-loss trials; a60min recording session and repeated controlled cycles. Do not energize the wet bench from this simulation pack alone. Retain actual measurements, uncertainty, as-built wiring revision and reviewer acceptance.


## How to source and what to do next

Send the63-line list plusS01/S02/S03 contracts to your supplier/assembler and ask for a line-by-line compliance response with exact part numbers, deviations, datasheets, matched ports and internal drawings. Mark each as stock item, built assembly or service; do not replace a requirement merely because a cheaper available item looks similar. Return the proposed basket and drawings for compatibility checks before custom fabrication. Then order approved items, retain the Phase3 card, and arrange attended commissioning sessions. No new budget ceiling is assumed.


## Evidence access

Open index.html directly in a browser; it needs no running demo server or internet. The PDF contains the full list and contracts. verify.py functionality is in validate.py: python3 validate.py verify . replays saved electrical metrics and deterministic hydraulic/thermal/safety checks without ngspice or paid calls. Rerunning electrical solves uses ngspice47: python3 validate.py run <new-evidence-folder>. Raw traces are compressed CSV; checksums show consistency, not authenticity if both files and manifest are replaced. GBrain was unavailable; a Codex restart may load it.


## New development harness

Proposed interface allocation, not the frozen Phase3 as-built schedule. Supplier terminal numbers remain part of Q01.

| Signal | Physical pin | Function |

|---|---|---|

| 3.3V | 1 | Host pullups only |

| GND | 6 | Host logic only; no field-ground tie |

| BCM2 SDA | 3 | Isolated host I2C |

| BCM3 SCL | 5 | Isolated host I2C |

| BCM4 | 7 | Two powered1-Wire probes;4.7k pullup |

| BCM23 | 16 | Isolated EXECUTION_PERMIT;47k physical pulldown |

| BCM12 | 32 | Isolated10Hz heartbeat;47k pulldown |

| BCM24 | 18 | Panel healthy status, activeLOW; new harness role |

| BCM17 | 11 | Valve CLOSED contact, isolated activeLOW |

| BCM27 | 13 | Cutoff EDM status, isolated activeLOW |

| BCM22 | 15 | Acquisition healthy, isolated activeLOW |


## Eight earlier rejection controls

Original unsafe traces are preserved. The new requirements supersede the provisional higher-current stage; no old board is retroactively qualified.

- **33mA receiver fault**: S03:100ohm burden, bounded loop supply/current, protected input; fault is invalid, not normal. Evidence: `afe_21.6_0.033 / afe_26.4_0.033`.

- **Back-powering Pi/ADC**: Field ADC isolation, hold-up and power-off input disconnect; no host field-ground tie. Evidence: `afe_rail_loss / negative_afe_no_hold_no_isolation`.

- **12V transmitter compliance**: Separate permanent24V loop supply, minimum21.6V tested. Evidence: `afe_21.6_0.02`.

- **Open burden**: Bound input and refuse calibrated invalid observation; repair/requalify before use. Evidence: `afe_open_burden`.

- **3.6A driver headline rating**: Do not order the old DRV8871 board; bounded smaller pump and S01 engineered stage. Evidence: `power_13.2_2.268 / thermal_pass_junction_bound`.

- **Hot-board driver failure**: Linear-rated pass device, case monitoring/cutout, current/power limit and SOA requirement. Evidence: `power_short / linear_FET_short_overshoot`.

- **Weak supply/startup**: 12V5A source, <=0.30ohm loop and explicit <=1.5A/60ms pump startup contract. Evidence: `power_10.8_1.752 / power_low_limit_fast_timer`.

- **Old startup latch**: Revised lower-power matched pump, bounded softstart and latched fault handling; not an unqualified old3A pump. Evidence: `power_max_cap_low_limit / power_restore`.


## Full order list - 63 lines

BUY lines are requirements; REUSE lines require an inventory check. Assemblies include their internal components. Quantities cover one complete bench. No prices/availability are assumed.


### C01 | 1 unit | Raspberry Pi 3 Model A+ or existing compatible Pi

**REUSE / REPLACE IF MISSING** - Controller

Existing controller; separate capstone development card, preserved Phase3 card and harness; no software install onto frozen card.

Interface: 40-pin header; 3.3V GPIO/I2C; Wi-Fi

Acceptance: Confirm identity, supply health and current as-built wiring before reuse.


### C02 | 1 unit | Development microSD

**BUY** - Controller

32GB minimum, genuine Class10/UHS-I A1 or better, manufacturer warranty; blank card.

Interface: Existing reader/Pi compatible

Acceptance: Full read/write capacity test; clean reproducible installation.


### C03 | 1 unit | Pi power adapter

**REUSE / REPLACE IF MISSING** - Controller

Manufacturer-approved 5V/2.5A micro-USB supply for Pi3A+; separate from actuator cutoff.

Interface: Pi PWR IN

Acceptance: Confirm rated supply and cable; recording remains powered on E-stop.


### C04 | 1 unit | microSD reader and USB console cable set

**REUSE / REPLACE IF MISSING** - Controller

Compatible with development computer and Pi; data cable, not charge-only.

Interface: USB

Acceptance: Confirm read/write and console connectivity.


### P01 | 1 unit | 12V pump desktop supply

**BUY** - Power

Enclosed certified SELV adapter, 12V/5A continuous, regulated; operating envelope 10.8–13.2V including cable drop. Document current limit and startup. Reference Mean Well GST60A12-P1J.

Interface: Matching 5.5/2.1mm or specified factory connector and >=5A breakout

Acceptance: Genuine model, local required approvals, no exposed mains; module startup transient support.


### P02 | 1 unit | 24V field/valve desktop supply

**BUY** - Power

Enclosed certified SELV 24V/2.5A continuous adapter; 21.6–26.4V. Reference Mean Well GST60A24-P1J. Remains on during actuator cutoff.

Interface: Matching factory DC connector

Acceptance: Includes pressure loop, valve, safety relays and field logic budget; document regulation/foldback.


### P03 | 2 units | Factory mating DC power harnesses

**BUY** - Power

Matched polarity and connector sizes for P01/P02, >=5A DC; keyed and strain relieved.

Interface: Supply to labelled fused terminals

Acceptance: No guessed 2.1/2.5mm fit; continuity/polarity documented.


### P04 | 1 unit | Commercial protected mains distribution

**BUY** - Power

Grounded16A/230V50Hz commercial power strip plus30mA TypeA portable RCD with test button and Indian-compatible factory plugs/cords; local required approvals. Reuse an institution-verified RCD only with its test record. All adapters and cords enclosed and mounted dry.

Interface: Appropriate Indian plugs/IEC leads

Acceptance: No user-built exposed-mains wiring; any valve PE requirement supplied as a compliant factory harness.


### S01 | 1 complete assembly | Dual-channel protected actuator power assembly

**BUY** - Assemblies

BUILT TO SPECIFICATION S01 below; includes engineering, populated PCB, power devices, shunts, gate drive, protection, heatsinks, discharge, terminals and factory tests. No substitutions by a bare motor-driver board.

Interface: Independent 12V pump and 24V valve inputs; named output/sense/control terminals

Acceptance: Supplier schematic/BOM, SOA report, thermal/pulse proof and test record supplied before accepting assembly.


### S02 | 1 complete assembly | Independent safety/control panel

**BUY** - Assemblies

BUILT TO SPECIFICATION S02 below; includes safety relay, two independent power cutoffs, monitored manual reset, hardware pulse watchdog, EDM and all coil wiring.

Interface: Two-channel E-stop; pressure/level/leak/thermal/field-power loops; isolated Pi status

Acceptance: Mechanical cutoffs operate without Pi software; one welded cutoff prevents reset and the other cuts power.


### S03 | 1 complete assembly | Isolated acquisition and signal-conditioning assembly

**BUY** - Assemblies

BUILT TO SPECIFICATION S03 below; includes two ADCs, 2 isolated current channels, I2C isolation, protected loop receiver, supervised pulse counter, firmware, hold-up, converters and labelled connectors.

Interface: Host 3.3V I2C isolated from 5V field bus; read-only counter interface

Acceptance: Includes all internal components and firmware. Existing spare ADS1115 may be supplied to assembler after verification; no double-purchase assumption.


### S04 | 1 unit | Latching emergency-stop switch

**BUY** - Safety devices

22mm industrial mushroom, turn release, two independent positively opening NC contacts, IEC60947-5-1 component data; contacts rated for panel DC duty.

Interface: Two channels to S02, not directly to actuator load

Acceptance: Contact/wire break opens safety loop; release cannot restart.


### S05 | 1 unit | Momentary RESET button

**BUY** - Safety devices

Industrial momentary NO, clearly labelled RESET; monitored rising edge.

Interface: S02 reset terminals

Acceptance: Held reset or permit already high cannot arm.


### S06 | 1 unit | Normal STOP button

**BUY** - Safety devices

Industrial momentary NC, separate from E-stop, labelled STOP.

Interface: S02 stop loop

Acceptance: Stops outputs; does not interrupt Pi recording.


### S07 | 1 unit | Independent pressure switch

**BUY** - Safety devices

Water compatible, adjustable NC contact opens at 0.25bar gauge with total set uncertainty <=0.02bar; port working >=6bar.

Interface: G1/4 male BSPP; isolated contact into S02

Acceptance: Set with reference instrument; operates without ADC/Pi; reset does not occur automatically.


### S08 | 1 unit | Low-water float switch

**BUY** - Safety devices

Water-compatible NC healthy contact, positive mounting and enough hysteresis to avoid slosh chatter; contact opens before suction loses flooding.

Interface: Reservoir bracket; S02 safety loop

Acceptance: Set at documented minimum inventory; open wire trips.


### S09 | 1 set | Leak detection sensor and interface

**BUY** - Safety devices

Tray-water detection; energized healthy output drops on leak, failed sensor or lost power. Compatible with tap water conductivity; no sensor electronics in unprotected mains zone.

Interface: S02 NC/energized-healthy input

Acceptance: Demonstrate leak detection and deenergized failure; dry reset requires operator.


### S10 | 2 units | NC thermal cutouts for power assembly

**BUY** - Safety devices

Normally closed, opening by 70C including tolerance; electrically isolated mounting. S01 normal arming case temperature <=65C, all SOA analysis case <=75C.

Interface: S01 heatsinks and S02 trip loop

Acceptance: Supplier contact/thermal mounting instructions and documented thermal-trip test.


### S11 | 1 set | Status indicators

**BUY** - Safety devices

24V green READY/ARMED, amber TRIP/RESET REQUIRED and red ACTUATOR POWER indicators; labelled.

Interface: S02 status terminals

Acceptance: Indicator states derive from actual panel feedback, not just software command.


### H01 | 1 unit | Low-voltage centrifugal water pump

**BUY** - Hydraulic

12V nominal; external flooded suction, no integral check valve; steady <=1A, startup <=1.5A for <=60ms; input capacitance <=470uF; documented acceptable 6–18V input. Maximum head <=6m and free flow7–10L/min at13.2V; delivers>=6L/min at0.03bar and>=1L/min at0.12bar; vendor curve must also cover10.8V. No dry-running.

Interface: Both ports G1/2 male BSPP; compatible pure water 15–35C

Acceptance: Manufacturer curve, polarity, startup/current/capacitance and on/off duty data. If thread adapters are needed, supplier revises matched fitting schedule without violating inertance/suction limits. A pump exceeding these bounds requires a design revision, not a silent substitution.


### H02 | 1 complete assembly | Normally closed water valve with matched connector/feedback

**BUY** - Hydraulic

24VDC, 100% duty, true zero-differential operation at 0–0.6bar; working >=6bar; cold current <=0.60A at 26.4V; coil R>=44ohm and L<=10H. No hidden suppression/economizer inconsistent with S01. Hydraulic closing 50–1000ms with specified suppression; mechanical CLOSED contact/indicator supplied and correlated to actual closure.

Interface: G1/2 female BSPP both ports; EPDM/brass or compatible stainless; Kv>=0.2m3/h

Acceptance: Manufacturer confirms low-head operation and closing envelope. Reference family Burkert6213 does not by itself establish exact article/low-pressure timing. Order feedback as a matched assembly; no coil-current proxy.


### H03 | 1 unit | Open reservoir

**BUY** - Hydraulic

5L stable open reservoir, marked 2–3L working total inventory; bottom outlet/flooded suction; removable cover remains vented.

Interface: G1/2 female bulkhead port

Acceptance: Not a pressure vessel; securely mounted below/at flooded pump inlet geometry.


### H04 | 1 unit | Reservoir bulkhead and seal kit

**BUY** - Hydraulic

Water-compatible G1/2 female bulkhead with matched gaskets, backing washers and retaining nut.

Interface: H03 outlet

Acceptance: No stress on thin tank wall; passive leak test.


### H05 | 1 unit | Suction service ball valve

**BUY** - Hydraulic

G1/2 female/female full bore, water working >=6bar; lock/tag in OPEN during operation.

Interface: Bulkhead to 12mm suction hose

Acceptance: Not in relief/bypass path. Position checked before arming.


### H06 | 1 unit | Low-loss filter/strainer

**BUY** - Hydraulic

Water-compatible cleanable 100–200um screen; working >=6bar; clean pressure drop <=0.02bar at 8L/min.

Interface: G1/2 female/female; after pump

Acceptance: Mount/clean without changing frozen safety returns; dirt/blocked condition is a refusal scenario.


### H07 | 1 unit | Main distribution manifold

**BUY** - Hydraulic

Six G1/2 female BSPP ports, water working >=6bar, bore/ports suitable for <=10L/min.

Interface: Pump/filter inlet, fixed bypass, relief, metered branch, instrument manifold, arrestor/vacuum accessory tee

Acceptance: Supplier matched sealing faces and mechanical mounting. Assembled unvalved bypass passes>=10L/min at0.10bar, including entry/return losses; no check valve or adjustment in this path.


### H08 | 1 unit | Instrument mini-manifold

**BUY** - Hydraulic

Four G1/4 female BSPP ports, working >=6bar; pressure-transmitter/switch/reference taps.

Interface: Main manifold through reducer

Acceptance: Keep taps free of trapped air; document height corrections.


### H09 | 1 unit | Independent full-flow water relief valve

**BUY** - Hydraulic

Spring-operated water relief; cracking 0.30bar +/-0.03bar; capacity >=10L/min by <=0.45bar including <=0.02bar outlet backpressure; response <=10ms or independently documented equivalent protection.

Interface: G1/2 female inlet/outlet; independent 12mm return

Acceptance: A differential bypass or 3bar appliance valve is not equivalent. Obtain factory set/capacity certificate.


### H10 | 2 units | Low-head water-hammer arrestors

**BUY** - Hydraulic

Commercial pressure-rated, minimum 0.25L nominal each; documented incremental compliance >=2e-10m3/Pa (=0.2mL/kPa) over 0.05–0.6bar; suitable factory low precharge <=0.02bar; working >=6bar.

Interface: G1/2 female; one at main manifold, one within 50mm of valve upstream tee

Acceptance: Appliance arrestors precharged at several bar do not qualify. Obtain pressure/compliance curve, vessel proof and precharge procedure; no home-made pressure vessel.


### H11 | 1 unit | Vacuum-break / anti-siphon assembly

**BUY** - Hydraulic

Water-compatible, opens before manifold pressure falls below -0.02bar gauge; capacity >=10L/min; pressure side working >=6bar; clean air inlet and spill containment.

Interface: Main manifold instrument/accessory port with included matched tee/adapters

Acceptance: Include mechanical admission flag with isolated contact or independently supervised air-admission sensor. Any admission trips/invalidates the run and requires reprime; no inferred software-only detection.


### H12 | 1 unit | Lockable branch metering valve

**BUY** - Hydraulic

Water-compatible needle/metering valve, working >=6bar; factory calibrated/locked complete-branch curve:0.50–0.70L/min at0.10bar, <=1.5L/min at0.45bar, <=2L/min at0.60bar; do not raise operating bench pressure to set it.

Interface: G1/2 female/female; verify at normal pressure, retain factory lock

Acceptance: Full assembled branch hydraulic inertance <=7.1e7 Pa s2/m3 including fittings, meter and valve.


### H13 | 1 unit | Near-valve arrestor tee

**BUY** - Hydraulic

G1/2 female/female/female, water working >=6bar.

Interface: 8mm branch inlet, H02 valve, local H10 arrestor

Acceptance: Mount arrestor close to valve; no intervening shutoff.


### H14 | 4 metres | Main/suction/bypass/relief tubing

**BUY** - Hydraulic

12mm ID reinforced water hose, nominal 18mm OD; manufacturer working >=6bar at 35C, burst >=18bar; suction segment kink/vacuum resistant.

Interface: Supplier matched 12mm barbs

Acceptance: Suction <=0.5m; pump/filter/manifold feed <=0.5m; bypass/relief return each <=1m. Actual cut layout in hose schedule; assembled bypass passes>=10L/min at0.10bar and main line inertance<=2e7Pa s2/m3.


### H15 | 2 metres | Metered branch tubing

**BUY** - Hydraulic

8mm ID reinforced water hose, nominal 14mm OD, working >=6bar at 35C, burst >=18bar.

Interface: Supplier matched 8mm barbs

Acceptance: Installed total <=2m and complete-branch inertance bound verified; no hidden shutoff in returns.


### H16 | 2 units | Pump female hose tails

**BUY** - Hydraulic fittings

G1/2 female BSPP to 12mm hose barb, matched pump seal face, working >=6bar.

Interface: H01 inlet/outlet

Acceptance: Confirm actual pump male thread and seal geometry.


### H17 | 6 units | Main male hose tails

**BUY** - Hydraulic fittings

G1/2 male BSPP to 12mm hose barb, working >=6bar.

Interface: Tank valve1, filter2, main inlet1, bypass1, relief outlet1

Acceptance: Matched bonded seal/flat-face geometry, not guessed thread tape.


### H18 | 3 units | Branch male hose tails

**BUY** - Hydraulic fittings

G1/2 male BSPP to 8mm hose barb, working >=6bar.

Interface: Metering outlet1, near-valve tee inlet1, valve outlet1

Acceptance: Flow passage accounted in inertance bound.


### H19 | 2 units | Flow-meter hose tails

**BUY** - Hydraulic fittings

G1/4 male BSPP to 8mm hose barb, working >=6bar.

Interface: Flow meter inlet/outlet

Acceptance: Meter must have matching female ports or supplier supplies an equivalent matched adapter schedule.


### H20 | 6 units | Main connecting nipples

**BUY** - Hydraulic fittings

G1/2 male/male BSPP nipples with compatible seals, working >=6bar.

Interface: Tank/ball1, manifold/relief1, manifold/metering1, local tee/valve1, local arrestor1, main arrestor1

Acceptance: H11 vacuum-break assembly includes its extra tee and connectors; no uncounted branch.


### H21 | 1 unit | Instrument reducer

**BUY** - Hydraulic fittings

G1/2 male to G1/4 female BSPP, working >=6bar.

Interface: H07 to H08

Acceptance: Compatible sealing faces.


### H22 | 1 unit | Instrument nipple

**BUY** - Hydraulic fittings

G1/4 male/male BSPP with seals, working >=6bar.

Interface: H21 to H08

Acceptance: Do not mix NPT/BSPT into fixed BSPP schedule.


### H23 | 1 unit | Spare manifold port plug

**BUY** - Hydraulic fittings

G1/2 male BSPP with bonded seal, working >=6bar.

Interface: Spare only: all six H07 ports are allocated; H11 supplies accessory tee/adapters

Acceptance: Keep capped during service; pressure-test complete port schedule.


### H24 | 12 units | Main hose clamps

**BUY** - Hydraulic fittings

Stainless, smooth band, suitable for actual 12mm hose OD; nominal 12–22mm range.

Interface: 10 installed ends plus2 spares

Acceptance: Correct torque, strain relief and inspect tubing damage.


### H25 | 10 units | Branch hose clamps

**BUY** - Hydraulic fittings

Stainless, suitable for actual 8mm hose OD; nominal 10–16mm range.

Interface: 6 installed ends plus4 spares

Acceptance: Correct fit on actual supplied hose.


### H26 | 1 set | BSPP seal and spare plug pack

**BUY** - Hydraulic fittings

30 G1/2 and12 G1/4 compatible bonded seals/O-rings;2 spare plugs each size.

Interface: All matched fittings

Acceptance: Supplier confirms seals compatible with every selected port; no NPT/BSPT substitution.


### M01 | 1 unit | Pressure transmitter

**BUY** - Measurement

Gauge 0–2bar, 4–20mA two-wire, supply minimum <=11V; accuracy <=0.25%FS over15–35C; proof>=6bar, burst>=12bar; response <=10ms.

Interface: G1/4 male BSPP, water compatible, sealed connector

Acceptance: Factory calibration certificate and points across0–2bar; bench recalibration0–0.30bar; exact transfer and units required.


### M02 | 1 unit | Pulse water flow meter

**BUY** - Measurement

Usable calibrated range0.1–3L/min, 5V open-collector NPN pulse output; >=1000 pulses/L; water working/proof>=6bar; supplier documented pressure drop/inertance.

Interface: G1/4 female BSPP both ports; 3-wire supply/signal/return

Acceptance: Calibrate0.3–1.5L/min. S03 remote EOL10k and2.2k series termination fitted at sensor; zero pulses remains a valid zero reading when supervised.


### M03 | 2 units | Digital temperature probes

**BUY** - Measurement

3.3V powered DS18B20-class 1-Wire, 3-wire, unique serial IDs, genuine sensor; water probe immersion-rated and case probe electrically insulated.

Interface: Pi BCM4 / physical7; 4.7kohm pull-up to host3.3V

Acceptance: Water/case role assignment and reference checks; no parasite power.


### M04 | 1 unit | Reference pressure gauge

**BUY** - Measurement

0–2bar digital gauge; proof pressure>=6bar; resolution<=0.001bar, calibration uncertainty<=0.002bar over0–0.30bar.

Interface: G1/4 male BSPP, water/air compatible

Acceptance: Current calibration certificate; static reference, not a claimed high-speed surge recorder.


### M05 | 1 set | Low-pressure calibration source

**BUY** - Measurement

Commercial hand bulb/pump0–350mbar, relief<=0.40bar, fine bleed and matched G1/4 test hose/selector.

Interface: Isolated instrument calibration connection

Acceptance: Disconnect/isolate rig during calibration; full-scale transmitter certificate is separate.


### M06 | 1 unit | Volumetric flow reference

**BUY** - Measurement

1L Class B graduated cylinder, stated error<=10mL, durable PP; optional100mL cylinder <=1mL error for short demonstrations.

Interface: Free return collection

Acceptance: Reference error, timing and count quantization included in calibration uncertainty.


### M07 | 1 unit | Reference thermometer

**BUY** - Measurement

Non-mercury, 0–50C or wider, resolution<=0.1C, documented uncertainty<=0.2C near20–40C.

Interface: Water bath comparison

Acceptance: Calibration certificate or institution loan with confirmed access; no assumed free reference.


### M08 | 1 unit | Timing reference

**REUSE / REPLACE IF MISSING** - Measurement

Stopwatch resolution<=0.01s; operator method with total timing uncertainty <=0.2s for >=60s collection.

Interface: Flow calibration

Acceptance: Record human timing contribution; software timestamps do not remove it.


### E01 | 1 set | DC fuse/holder set

**BUY** - Electrical installation

Covered DC-rated holders>=32V/10A: 12V main T3.15A, pump T2.5A, 24V main T2A, valve T1A, instrument T0.5A; 3 fuses per value.

Interface: Five labelled branches, touch-safe terminals

Acceptance: Supplier DC interrupt rating and time/current/I2t curves; coordinated with S01 and source current limits.


### E02 | 1 lot | Power and signal cable

**BUY** - Electrical installation

10m red +10m black 1.0mm2 copper for power;10m4-core0.5mm2 shielded sensor cable;10m 0.25mm2 logic cable; approved protective-earth harness where required.

Interface: Labelled terminals; separate signal/power routes

Acceptance: Temperature/current ratings, ferrules, strain relief; do not infer function from wire colour.


### E03 | 1 lot | Terminals/connectors/labels

**BUY** - Electrical installation

80 DC terminal positions with touch-safe covers,10A power rating;300 ferrules (100 each0.25/0.5/1.0mm2);8 keyed mating sensor plug/socket sets;4 keyed2-pole>=5A DC power connector sets;20 strain-relief glands (14xM12,4xM16,2xM20, chosen for actual cable OD);100 permanent wire labels,20 end stops and20 cable clamps. Factory module connectors remain included in assembly price; this is the installation/spare pack.

Interface: S01/S02/S03 factory terminal schedule

Acceptance: Each wire has both-end identifier; no actuator current through solderless breadboard.


### E04 | 1 unit | Dry electrical enclosure

**BUY** - Electrical installation

ABS or equivalent IP54 minimum, about500x400x200mm; DIN rail, internal backplate, guarded heatsinks, controlled ventilation with splash-safe baffles and cable segregation.

Interface: Mounted outside wet tray and above spill level

Acceptance: Internal ambient<=50C; no exposed mains; supplier verifies selected assemblies physically fit.


### E05 | 1 set | Factory board/relay/heatsink mounting kit

**INCLUDED WITH S01/S02/S03** - Electrical installation

All standoffs, insulators, captive fasteners, thermal pads, cable supports and panel drawings.

Interface: S01/S02/S03 to E04

Acceptance: Included in assembly supply; bare ICs, unsupported boards and unguarded hot resistors are not finished modules.


### B01 | 1 unit | Containment tray

**BUY** - Mechanical/support

Effective usable capacity>=8L after equipment displacement; internal dimensions at least700x450x100mm; stable walls and drain plan.

Interface: All reservoir/pump/wet fittings inside tray

Acceptance: Maximum water inventory3L; prove usable containment with equipment installed.


### B02 | 1 set | Bench base and supports

**BUY** - Mechanical/support

Rigid nonconductive base>=1400x750mm with an upright dry panel; reservoir/pump/manifold/valve brackets, return retainers and labelled hose clips. Accommodate700x450mm tray,500mm-wide dry enclosure and>=100mm horizontal separation; dry enclosure above spill level.

Interface: Wet tray separated from dry enclosure

Acceptance: No load carried by sensor ports; protect hose bend radius and maintain flooded suction.


### B03 | 1 lot | Commissioning consumables

**BUY** - Mechanical/support

3L clean tap water, absorbent pads, collection container, tubing caps, cable ties, heat-shrink and spill cleanup materials.

Interface: Attended bench sessions

Acceptance: No additives/hazardous fluids; meet flow-meter conductivity/material limits if applicable.


### B04 | 1 set | Existing tools

**REUSE / REPLACE IF MISSING** - Mechanical/support

Multimeter, insulated wire tools, screwdrivers, soldering equipment for signal work, continuity leads; torque tool appropriate for fittings.

Interface: Passive checks only until commissioning

Acceptance: Reuse existing verified tools; obtain missing calibrated measurement capability.


### Q01 | 1 package | Supplier engineering and factory acceptance pack

**BUY** - Services/documents

As-built terminal/schematic drawings, complete internal BOM for custom assemblies, firmware/source and protocol, component datasheets, calibration/relief certificates, SOA/thermal/fuse analysis, factory test records, configuration files and substitution list.

Interface: CR-EXT-R1 compliance matrix

Acceptance: This is a purchase line/service deliverable, not optional paperwork; actual supplier drawings checked before final PO release for custom modules.


## Assembly contracts


### S01

Two independent protected channels, pump12V and valve24V, upstream of command outputs and behind S02 cutoffs. Pump load contract: <=1A continuous, <=1.5A/60ms startup, <=470uF; current-limit1.752–2.268A, total pump source/wiring/shunt impedance<=0.30ohm, output rise about20ms, output discharge47ohm equivalent and <=1V within120ms after disable. Valve cold current<=0.60A, L<=10H; channel limit0.705–0.913A; unidirectional coil switching and suppression energy>=5J, reverse coil clamp<=30V, switching device>=100V with peak drain<80V. Current/power limiting failure latches; no automatic retry. Regulated pass power12–25W, timeout20–60ms, case<=75C, transient overshoot<=8A for<=20us at VDS<=30V; source/choke/damping design must demonstrate that bound. Separate actual load-voltage feedback, isolated current channels and power-good/fault outputs; insertion delay<=1.1s and ready-low/fresh-permit interlock supplied; a command is not feedback. Include input inrush/hot-plug protection, reverse/backfeed protection, appropriate inductive clamps and power-off behavior. Reference controller LM5069-1 (latched version), reference linear-rated pass device IXTK90N25L2; reference Rs27.4mohm/68.1mohm1%, CT680nF5%; adjust complete design to actual thresholds, PWR resistor, gate charge and PCB. Main/regulated and short-overshoot waveforms must be checked against actual datasheet FBSOA at75C, not avalanche energy or headline wattage. Entire internal BOM/design/assembly/test supplied; reference values are not a standalone construction circuit.


### S02

Two-channel E-stop and monitored edge RESET. Reset allowed only when permit is low, all E-stop/STOP/pressure/low-level/leak/thermal/vacuum-admission/field-power inputs are healthy, hardware heartbeat10Hz has at least two edges, and both cutoffs are proved open by mirror/forcibly guided contacts. Hardware watchdog detection<=200ms plus cutoff contact release<=40ms; complete missing/static-heartbeat-to-power-removal<=250ms including internal sampling/jitter. Record measured factory timings. Two independent normally-open power cutoffs K1/K2 in series with BOTH12V pump and24V valve positive rails; 24V coils, each with adequate documented DC-inductive rating (>=3A at24V for this bounded load) and EDM contacts. E-stop/pressure/leak/water/thermal faults drop actuator authority; no Pi, agent or network required. One welded cutoff is contained by the other and prevents reset. Supply restore, E-stop release or held RESET never restarts. Reset first arms the cutoffs with permit LOW; then wait up to1.1s for S01 initial insertion/READY. S01 READY is not a prerequisite for closing its upstream cutoffs. Only after READY has been observed with permit LOW may a fresh rising execution permit enable outputs. Early/held permit must not start upon READY. A READY timeout or loss during execution trips; a fresh reviewed application approval remains required. Separate permanent power feeds keep Pi and instrumentation recording during a trip. Supply a true hardware implementation and factory fault tests; this contract/model is not a claim of SIL/PL certification for the assembled bench.


### S03

Field bus powered5V; host I2C3.3V isolated, <=100kHz, host cable<=0.3m. Host-off leakage<=1uA per signal; no direct field5/24V connection to Pi pins. Two ADS1115-class16bit ADCs atfield4.5–5.2V, addresses0x48/0x49; pressure, two load voltages and two Hall currents, with a separate supervised flow window/counter. Deliver >=100 timestamped samples/s per pressure/current/load-voltage channel, actual conversion order/delay and uncertainty included. Choose conversion scheduling/gain so aggregate rate is feasible; no simultaneous-sampling claim. Pressure input0–33mA: loop protector36V with DC limit<=33mA,100ohm0.1%>=0.5W shunt, input-fault clamp, protected sense input. Include full-network scaling/calibration. Analog signals reaching powered-off input switches<=3.6V; power-good opens all affected signal paths within50us, while local isolated hold-up>=100uF with load<=20mA retains ADC rail margin. Two galvanically isolated bidirectional Hall current channels, +/-5A range, >=1kHz bandwidth, calibrated uncertainty<=0.05A over0–2.5A; each conductor/sensor rated>=5A DC, isolation and connector ratings supplied. Locate in actual load conductor; valve placement includes flyback current path when feasible. Pump differential load-voltage range0–18V, valve-30..+30V including flyback, conditioner common-mode withstand>=60V. Shift/scale to protected ADC input range0–3.3V; include gain/offset calibration and overrange indication. No INA226 common-mode assumption during negative flyback. Hall0.5–4.5V output must be scaled nominally0.65 to0.325–2.925V before protected ADC. Suggested calibrated voltage transfers: pump0.15+0.16xVload (0–18V), valve1.65+0.05xVload (-30..+30V); supplier proves actual topology/CM range and timing. Actual current/voltage inputs separate from commands; values/quality/source timestamps and saturation must be preserved. Pressure/current/voltage source age<=200ms; temperature age<=2s; counter heartbeat<=100ms and stale after200ms. Zero pulse frequency is valid when acquisition is healthy. Missing flow response after3s with command ON or CLOSED feedback disagreement beyond1s trips under the reviewed procedure; commissioning must establish expected current bands. Supervise NPN flow line with remote10kohmEOL plus2.2kohm series sensor resistor, controller4.7kohm pullup, window comparator/ADC with ratio bandsLOW0.250–0.295,HIGH0.655–0.705; open/short/24V miswire are invalid. Statically low OR high can be valid zero. Hardware pulse counter>=32bit,>=5kHz capability; field timestamp/sequence/heartbeat at<=100ms, reset detectable, read-only register contract at0x42. Counter firmware/source/protocol included and has no actuator authority. At least two4-channel power-off-protected analog switches (reference TMUX1511) or a documented equivalent protect every affected ADC input; pressure/voltage/current sources remain isolated on field power loss. All analog conditioners/clamps/line terminations, digital isolators, field5V converter, power-off protections, plugs and labels included.


## Primary references

- [Raspberry Pi3A+ official reduced schematic](https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-a-plus-reduced-schematics.pdf): J8 header identities checked for the proposed new harness. Supplier terminal numbers and current physical wiring must still be checked before installation.

- [TI LM5069 Rev G](https://www.ti.com/lit/ds/symlink/lm5069.pdf): Latched LM5069-1, current and TIMER bounds. Behavioral controller used in SPICE; manufacturer macromodel not used.

- [TI ADS1115 Rev E](https://www.ti.com/lit/ds/symlink/ads1115.pdf): Supply-relative analog limits, multiplexed conversion and data-rate constraints. Two ADCs are specified; no simultaneous-sampling claim.

- [Littelfuse IXTK90N25L2](https://www.littelfuse.com/assetdocs/Littelfuse-Discrete-MOSFETs-N-Channel-Linear-IXT-90N25-Datasheet.PDF?assetguid=85B50793-C43C-4B40-A84C-3DCCA3D22A7B): 75C FBSOA graph and 250V/2.3A/5s SOA reference. Main waveforms are bounded; a separate overshoot contract still requires the real gate/choke design.

- [Mean Well GST60A specification](https://www.meanwell.com/Upload/PDF/GST60A/GST60A-SPEC.PDF): Reference 12V5A and24V2.5A adapters; manufacturer P1J connector dimensions. Confirm exact supplied model/cable.

- [Burkert6213 manufacturer data](https://www.burkert.com/en/Media/plm/DTS/DS/ds6213-standard-eu-en.pdf?id=DTS0000000000000001000115690ENAF): Family reference only. Timing table is measured at6bar inlet, not this low-head loop; exact low-pressure timing and mechanical CLOSED accessory remain supplier requirements.
