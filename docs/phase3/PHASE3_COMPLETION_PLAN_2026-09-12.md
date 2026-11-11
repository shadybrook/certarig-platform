# CertaRig Phase 3 completion plan

Date prepared: 12 September 2026  
Submission target: 20 September 2026

## Frozen claim

Phase 3 validates the CertaRig control and evidence architecture on a low-voltage dry hardware bench. Hydraulic commissioning is reserved for the capstone. The Phase 3 submission must not claim that a real reservoir, pump, valve, pressure vessel, mains load or production control system was commissioned.

## Current readiness

Completed:

- Pi boot, SSH, I2C and ADS1115 commissioning
- P1/A0 and P2/A1 acquisition and sweep evidence
- Physical E-stop sensing and corrected raw-level software logic
- Fused 5 V output branch and E-stop NC2 relay-supply interlock
- GPIO23 to BC547 to CH1 relay actuation
- Red/green K1 changeover indication
- Three repeatable permit/safe cycles
- E-stop during permit, forced-safe response and reset-required anti-restart
- Automated software check with 6 JavaScript tests and 30 Python tests
- WP1 circuit freeze and photographic record confirmed by the operator; five labelled pre-power photographs are versioned in the repository
- WP2 final as-built circuit diagram completed in SVG, PNG and PDF formats

Explicitly not completed:

- Broken-wire/open-circuit injection test: not performed
- Hydraulic loop and field sensors/actuators: capstone scope
- Mains or high-current load switching: outside this bench scope

## Work packages to submission

### WP1 - Freeze and photograph the as-built bench

Status: **Completed by operator confirmation.** Five labelled pre-power photographs are already versioned. The two final red/green operating-state image files must still be supplied if they are to appear in the public repository.

Do not change wiring before recording it. With power disconnected, take:

1. One full-bench overhead photograph.
2. One Pi GPIO close-up showing physical pins 2, 16, 17, 18 and 20.
3. One ADS1115 close-up showing A0, A1, SDA, SCL, VDD and GND.
4. One E-stop and fuse-holder close-up.
5. One relay/breadboard close-up showing DC+, DC-, CH1, S1 COM-LOW, K1 COM/NC/NO and both 1 kOhm branches.
6. One red-safe-state photograph and one green-permit-state photograph.

Each file should use a stable name and receive a one-line caption. Do not expose Wi-Fi passwords or private credentials.

Acceptance: every wire in the final schematic can be located in at least one photograph.

### WP2 - Update the canonical as-built circuit diagram

Status: **Completed.** See the [final PNG](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png), [editable SVG](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.svg) and [submission PDF](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.pdf).

Create one clean schematic and one physical-pin table. The diagram must distinguish:

- Pi physical pin number from BCM name
- 3.3 V analogue rail from fused 5 V output rail
- E-stop NC1 software-sense path from NC2 hardware power-interlock path
- Relay trigger terminals from K1 changeover contacts
- Red inhibited state from green permitted state
- P1/A0 and P2/A1 signal paths

Acceptance: the diagram matches the frozen configuration in the 12 September evidence report and contains no old pin-17-to-relay-COM connection.

### WP3 - Run the end-to-end sensor guardrail test

This is the most important remaining technical run. It links the analogue inputs to the control decision instead of demonstrating them as separate subsystems.

Test sequence:

1. Power the bench in the normal released-but-inhibited state.
2. Start a timestamped integrated logger and live dashboard.
3. Place P1 and P2 in a defined safe window.
4. Reset the trip latch and request permit; verify green/K1 on.
5. Move P1 beyond its configured safe threshold; verify forced safe, red/K1 off and a reason code.
6. Return P1 to range; prove that K1 does not automatically restart.
7. Reset and permit again.
8. Move P2 beyond its safe threshold; verify the same forced-safe and latched behaviour.
9. Return P2 to range, reset and run one final normal permit/safe cycle.
10. Stop logging and shut down cleanly.

Required outputs:

- raw CSV with A0, A1, GPIO24, GPIO23, latch state, decision and reason code
- voltage-versus-time plot with relay and E-stop states
- compact test-case table containing expected and observed results
- short screen recording showing the dashboard and physical indicators together

Acceptance: unsafe analogue input can never leave GPIO23 HIGH, and returning to range cannot restart the relay without a reset and a new permit.

### WP4 - Demonstrate the Pi-hosted software

Run the repository on the Raspberry Pi, not only on the Mac. Capture:

1. SSH connection and hostname.
2. OS/kernel and `vcgencmd get_throttled` output.
3. `i2cdetect` showing `0x48`.
4. Project commit hash.
5. Software tests passing on the Pi.
6. Service start command and listening address.
7. Dashboard opened on the Mac using the Pi's local-network address.
8. Live values changing as both potentiometers move.
9. E-stop and permit/safe events appearing in the UI or event log.

Acceptance: a reviewer can see that the dashboard is served by the Pi and responds to the physical bench.

### WP5 - Reliability and limitations evidence

Run a 20-30 minute low-voltage soak with the system mostly safe, including several planned transitions. Record:

- start and end timestamps
- sample count and missing/invalid sample count
- final Pi temperature and throttling flags
- process CPU and memory snapshot
- unexpected resets, I2C errors or relay changes

Do not leave the bench unattended. Stop on heat, smell, smoke, unstable power, unexpected clicking or loose wiring.

Acceptance: no unexplained output change, reboot, I2C loss or throttling. If an issue occurs, report it honestly and retain the log.

### WP6 - Complete the Phase 3 report

Fill the supplied template under these headings:

1. Introduction: dry-bench implementation-readiness purpose and Phase 1/2 recap.
2. Implementation Overview: clearly separate fully implemented, partially implemented and capstone-only items.
3. Validation and Testing: software tests, analogue sweeps, E-stop, relay truth table, sensor guardrails and dashboard demo.
4. Performance and Reliability: response observations, sample rate, soak result, temperature and throttling.
5. Risk Analysis: wiring error, incorrect GPIO polarity, connector failure and mitigations.
6. Limitations: potentiometers emulate sensors; indicators emulate actuators; no hydraulic or mains validation.
7. Future Enhancements: real transducers, valve/pump interface, reservoir loop, calibration and longer endurance testing.
8. Learning Outcomes: pin-number discipline, measurement-gated commissioning, fail-safe polarity, evidence integrity and troubleshooting.
9. Final Deliverables: GitHub repository, report, demo video, diagrams, photographs, CSVs, plots and test summaries.
10. Conclusion: ready for capstone hydraulic integration, not yet a field-certified controller.

Acceptance: every technical claim cites a file, screenshot, photograph, CSV, plot or test result in the repository.

### WP7 - Produce the Phase 3 demonstration video

Target 10-12 minutes unless the advisor specifies otherwise.

Suggested order:

1. Problem, user community and benefit
2. Phase 1 and Phase 2 development path
3. Frozen Phase 3 versus capstone scope
4. Architecture and technology stack
5. Circuit diagram and two E-stop channels
6. Live repository clone/start on the Pi
7. Pi-hosted dashboard
8. P1/P2 live movement
9. Normal permit/safe cycle
10. E-stop during permit and anti-restart
11. Sensor-guardrail test cases
12. Evidence files, limitations and capstone path

Use still diagrams and labels while explaining; use live footage when proving behaviour. Keep the presenter visible briefly at the beginning and end.

Acceptance: the video visibly proves the live PoC and does not rely only on plans, slides or simulation.

### WP8 - Repository freeze and submission check

Before publishing the final link:

1. Remove credentials, private network names and unredacted screenshots.
2. Run `npm run check` from a clean checkout.
3. Verify all relative links in the evidence index.
4. Add the final report, video link and Phase 3 evidence index to the repository README.
5. Commit the frozen as-built code, tests, diagrams and evidence.
6. Create a Phase 3 release/tag.
7. Test the GitHub, report and video links from a signed-out browser.

Acceptance: a reviewer can clone the repository, follow the instructions and inspect every submitted evidence item without private access.

## Recommended schedule

| Date | Primary outcome |
|---|---|
| 12 Sep | Freeze evidence, photographs, report this integrated truth-table pass |
| 13 Sep | Correct as-built diagram and implement sensor-guardrail capture |
| 14 Sep | Run guardrail cases and generate plots |
| 15 Sep | Pi-hosted dashboard and clean-clone reproduction |
| 16 Sep | Supervised soak test and reliability summary |
| 17 Sep | Complete Phase 3 template and assemble figures |
| 18 Sep | Record and edit the Phase 3 demonstration |
| 19 Sep | Final quality review, signed-out link test and release/tag |
| 20 Sep | Submit with contingency time; avoid first-time testing on submission day |

## Immediate next action

Keep the powered-down circuit unchanged. WP1 and WP2 are complete, subject only to copying the two operating-state photographs into the public evidence folder. The next powered experiment is WP3, the integrated P1/P2 sensor-guardrail run.
