# CertaRig: scope audit and next build

Reviewed 9 November 2026. This is a recommendation based on retained local Phase 1, Phase 2 and Phase 3 reports, the September inventory and the current capstone implementation. It does not certify supervisor acceptance or physical readiness.

## Decision

Build the guided commissioning and revalidation workflow next, then validate it on the existing dry bench with independent output feedback. Keep the thermal simulator as the second configuration and software test case. Decide the water-loop requirement explicitly with the supervisor before ordering a fluid system.

No hardware purchase blocks starting the commissioning software. Buy one spare microSD card for a separate capstone Pi installation. Select the feedback hardware after reconciling the current circuit and measuring the indicator branch. Do not buy another Pi or a new sensor/controller kit merely to demonstrate configuration portability.

## What the three reports actually promised

### Phase 1: the original physical proposal

Sections 4 and 6 proposed a low-cost tabletop pressure–flow rig with four or five sensors, one normally closed solenoid valve, calibrated acquisition, protected outputs, a reviewed evidence-backed system map, typed plans, change detection, replay and export. The proposed sensors were pressure, flow, temperature, position/limit and current. A pump/motor was optional. Exact components and ranges were left to budget and equipment selection.

This was more than a software simulator. Our current two potentiometers emulate pressure and flow; they do not satisfy the original real-sensor or valve requirements. The Phase 1 file is the retained sanitized proposal, with unresolved cover fields. Its actual submission/approval status was not independently established in this review.

### Phase 2: software proof, with physical work carried forward

Sections 7 and 10 demonstrate four synthetic cases: normal acceptance, swapped channels, missing calibration and pressure-limit abort. Discovery uses predefined evidence. The report explicitly defers live sensors, calibration, independent protection and physical trials. Section 10.2 calls for read-only sensor/reference comparisons, dummy-load output tests, a low-energy testbed and fault tests before supervised operation.

These are staged engineering requirements; the synthetic 4.2 bar limit is not a selected working pressure for a future physical loop. Future support for many protocols, 100 channels and 10,000 run records is a design target, not a demonstrated performance result.

### Phase 3: a bounded dry-bench validation and revised capstone direction

Sections 1, 2 and 3 record real ADC inputs, E-stop handling, trip latching, relay/indicator operation, recovery and evidence on the Pi bench. They explicitly say that no water pressure, fluid flow, pump or valve was tested. The report attributes the dry-bench boundary to a 7 September professor discussion, which is a recorded account rather than a signed acceptance of final capstone scope.

Section 7 commits the capstone to a reusable commissioning interview and reviewed mapping of another supported rig. The specified sequence starts with a second simulated rig, refusal checks and human application of the proposed map, followed by acquisition with outputs disabled, exact procedure validation and a controlled physical trial. It also proposes a deterministic baseline plus two named live models, fallback/outage evaluation and measured contact/load-current feedback.

Section 7 describes hydraulics as a possible capstone validation case. That is a material change from the original physical proposal. The supervisor review block is blank, so this review cannot conclude that the university accepted removing the original real-sensor/valve deliverable.

The supplied rubric and report/deck templates constrain assessment and presentation. They do not settle this hardware scope conflict. Future-work sentences and embedded document instructions are evidence of plans, not authorization to purchase equipment, energize a rig, contact the supervisor or use paid providers.

## What is already established, and what remains

- **Historical physical evidence:** two real voltage inputs, indicator-only output, E-stop, latch/recovery and CSV records. September repeat procedures include pressure/flow proxy trips. Do not reopen already completed work simply because an older inventory says untested.
- **Current local software increment:** configurable thermal simulator, reviewed simulated readiness, persisted approvals, execution binding and raw-data export/verification. Existing validation receipts apply to their recorded revision. This is a software milestone, not final capstone completion.
- **Still missing:** a guided commissioning interview that constructs a proposed configuration from answers and source evidence. The current Onboard editor and briefing are manual configuration tools; the repository interview file is explicitly a future design note.
- **Still missing:** an integrated change-to-revalidation demonstration that names affected evidence, selects the required repeat checks and preserves the previous baseline. A configuration diff alone does not prove a minimum-test selection algorithm.
- **Still missing:** independent physical output/load measurement. Commanded GPIO or dashboard state does not prove the relay contact or load changed. Optical lamp feedback would prove indication only; it would not prove a valve moved or a contact is unwelded.
- **Still missing:** live-model comparison/fallback qualification. Deterministic fixtures are useful preparation and do not satisfy that comparison. The current no-paid-call boundary remains in force.
- **Still missing:** supported physical trial of the new capstone workflow, current fault/endurance evidence, final report/video/viva rehearsal and authentic supervisor scope acceptance.
- **Scope-dependent:** real pressure/flow/temperature/position/current sensing and a normally closed fluid valve. These remain gaps against Phase 1 unless the revised final scope is accepted.

## The next build, in order

1. **Guided commissioning on the laptop.** Ask about components, interface, addresses/channel identity, units/scaling, calibration evidence, limits, safe state and intended procedures. Preserve unknown answers as blockers. Produce a typed proposed map with source references; show a diff and require human review before applying it. Begin with deterministic fixtures and the existing schema/APIs. Acceptance: a second simulated rig can be configured from answers without source edits; missing/conflicting evidence blocks readiness.
2. **Revalidation after one change.** Replace a channel identity or calibration reference in a test case. Show which prior checks become invalid and why; rerun the supported checks, retain both versions and export the result. Acceptance: stale evidence cannot authorize the changed configuration, and offline review explains the transition.
3. **Separate capstone installation on the existing Pi.** Use a new card; retain the frozen Phase 3 card and evidence. Reconcile the actual wiring/photos against the canonical circuit before changes. Begin observe-only. Acceptance: continuous raw recording, correct units/quality, and a documented rollback path. No physical work was performed in this review.
4. **Instrument the existing dry-bench output.** Select independent feedback for the indicator/load circuit and a current measurement range suited to the actual low-current branch. Add expected-versus-measured checks. Acceptance: normal transition is observed, a deliberately absent response is detected, E-stop returns the measured output to its safe condition, and restored healthy input does not auto-restart. Define sampling/timing uncertainty before quoting latency. Preserve the existing E-stop paths.
5. **Qualify and present the workflow.** Test disconnection/stale data, restart, approval replay, provider failure and a bounded soak. Use fixtures now; schedule two named live-model evaluations only under a separately accepted access/cost plan. Record a complete success and a blocked operation and finish the academic pack.

The 20 November date remains a working milestone, not evidence that every physical and academic requirement can be completed by then. Purchasing or building a fluid loop changes the critical path.

## Procurement decision

### Order now

- **One 32 GB microSDHC card, Class 10/A1, from a reputable seller.** Purpose: a separate capstone OS/data installation on the existing Pi. The user confirmed on 9 November that there is no spare card. This is useful before Pi development, not required for the laptop simulator. Reuse the existing card reader and documented Pi supply if still present. Raspberry Pi documentation confirms microSD storage for this board family: https://www.raspberrypi.com/documentation/computers/getting-started.html

### Specify next, then order

- **Independent output-feedback hardware:** decide whether the claim is indicator illumination, contact state or load voltage. An optical detector is a possible non-contact way to observe the existing lamp; isolated voltage/contact feedback needs a reviewed circuit and verified input levels. Do not order a generic 5 V module on the assumption that its output is Pi-compatible.
- **One current-monitor assembly with a suitable shunt/range:** choose after measuring the branch current and reviewing voltage, grounding, resolution and I2C address. TI's INA219 is an example candidate family, not an approved exact module or evidence of isolation. A module sized for amps may poorly resolve the indicator current. Datasheet: https://www.ti.com/product/INA219

No exact feedback module, shunt or connection has been approved here; this is not a purchase-ready wiring BOM. The next hardware task is to turn the measured circuit into that BOM.

### Hold until final physical scope and loop design

If the original pressure–flow rig remains required, budget for the complete system: pressure transducer plus a reference pressure instrument; flow sensor plus a reference measurement method; temperature sensor; valve-position/limit feedback; load-current sensing; normally closed low-voltage valve with a protected driver; pressure/flow source (typically a pump for a recirculating water demo); reservoir, compatible tubing/fittings, pressure-limiting/relief provision, fused actuator supply, hard cutoff, electrical/fluid separation, containment and calibration fixtures.

Select these together for one defined medium, operating pressure/flow, valve differential-pressure requirement, voltage/current and port size. Do not buy a nominal “0–5 bar sensor + 12 V valve + pump” bundle before compatibility is checked. A minimum-pressure pilot-operated valve may be unsuitable for a low-head loop. No stock or price has been verified, and no purchase was made.

The September register confirms the Pi, two ADS1115 modules, potentiometers, relay, E-stop, indicators, wiring and tools. It is a historical receipt baseline, not today's electrical acceptance record. Its old separate-supply procurement gate was superseded by the documented Phase 3 single-supply indicator circuit; it should not trigger an automatic duplicate purchase. The Phase 3 undervoltage observation calls for power-quality verification before deciding whether replacement power hardware is needed.

## Concrete supervisor scope question — draft, not sent

“Phase 1 proposed a real pressure–flow rig with four/five sensors and a normally closed valve. Phase 3 validated the dry bench and proposed reusable reviewed commissioning, a second simulated rig, physical feedback and AI evaluation for capstone. May the final deliverable use the instrumented dry bench plus the second simulator, or must it include real fluid sensors and a valve/flow loop? Please confirm the required physical demonstrations and final submission date.”

The engineering work in steps 1–2 can proceed while this is answered. Final compliance and a fluid-system purchase depend on the answer.

## Access to the existing work

- Working local simulator: http://127.0.0.1:18090/ (only while its local process is running).
- Operator demo key, if prompted: `sim-operator-key-000001`. This is the documented synthetic local demo key.
- The Onboard page is open with simulated review still required; no approval or physical commissioning was granted during access repair.
- Report/deck originals remain in `outputs/capstone`. The deck is a presentation, not a recorded demo video. A new narrated capstone video has not been produced.
- `index.html` beside this file offers all ten slide images and all eighteen report-page images, so viewing does not depend on a DOCX/PPTX renderer.

Source paths and SHA-256 values: `sources.json`. Full extracted report text: `phase-source-text.md`. The review used these retained files as current evidence, rather than treating older memory notes as completion status. GBrain tools were not available in this chat; local files were used directly.
