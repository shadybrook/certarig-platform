# CertaRig extended-rig design review R0

This is a new review drawing, not a build-ready component schematic or accepted circuit. The earlier handover contained architecture and procurement holds; its pin-level circuit belonged to the original Phase 3 dry bench.

The three PDF sheets show electrical architecture, the water path, and desk-review findings. Editable SVG copies and rendered PNGs accompany the PDF. The original Phase 3 installation is preserved. No parts are released for purchase by this drawing. Budget remains a target of INR13,000 plus INR2,000 contingency; two separate current channels revise the candidate basket and need a new matched quote.

Checked: a candidate 10 V-minimum pressure sensor with a 150 ohm burden requires at least 13 V at 20 mA, before cable losses. A 12 V instrument loop fails this assumption. The same illustrative burden produces 3.6 V at 24 mA, beyond a 3.3 V ADC rail. These values reject that combination; they do not select a final supply, burden or protection circuit. Source: https://robu.in/wp-content/uploads/2025/06/R222349-PR19C-PA-050K.pdf ; ADC conditions: https://www.ti.com/lit/ds/symlink/ads1115.pdf . The pressure range itself remains contradictory in the sheet.

Proposed changes: separate pump and valve current channels, independent DC-rated actuator cutoff with manual restart prevention, conditioned measurements and preserved Pi recording power. Exact GPIO/header assignments, grounding/isolation, drivers, shunts, fuses, suppression, pressure protection and delivered quotes are open. Electrical current does not prove mechanical position. The prior valve catalogue URL was unavailable on this recheck; obtain the exact manufacturer variant and current datasheet before acceptance.

Needed next: current wide and close-up bench photographs, readable relay/E-stop/power labels, terminal/continuity review, and exact accepted components. Then produce the conductor-level schematic and wire schedule, perform electrical design checks and attend the staged physical tests. Construction release and physical acceptance are false in design-review-status.json.
