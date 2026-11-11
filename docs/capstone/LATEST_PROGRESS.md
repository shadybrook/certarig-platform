# CertaRig capstone progress - 11 November 2026

Start with the [extended-bench electrical connection diagram](../hardware/extended-rig/CR-EXT-R1/CertaRig_Extended_Bench_Circuit_CR-EXT-R1.pdf),
the [completed commissioning workflow](EXTENSION.md), and the
[complete deliverable index](../../artifacts/2026-11-capstone/README.md).

## Completed source milestones

- `bbebcea`, `df05bc3`, `2f25d66`: reviewed simulator runs, approval history,
  raw-data evidence exports, reproducible demo and Studio fixes.
- `7279765`, `0f00140`: resumable source-backed commissioning interviews,
  a distinct thermal model, configuration revalidation, observe-only MQTT,
  mixed-sensor/feedback foundations, and separated structured interview routing.
- `a7f8795`: mapping from the approved project missions to evidence and the
  physical-development sequence.
- `f6b0c3a`, `69ca4ca`, `a46c6df`: bounded SPICE experiments, reproducible fault
  evidence, supplier review and rejection-mitigation comparisons.
- `9412482`: CR-EXT-R1 extended-water-bench requirements, electrical and hydraulic
  connection plans, acquisition contracts, protection and bounded fault models.

The customer journey is to describe a supported rig, resolve missing information,
review a configuration, rehearse a procedure, approve execution and export the
results with raw evidence. Current completed demonstrations use simulated plants
and deterministic agent fixtures.

## Recorded validation

The [9 November receipt](../../artifacts/2026-11-capstone/capstone-extension/validation-summary.json)
records 283 software tests, eight browser tests, two explicit loopback broker
tests and 90.40% coverage. These are dated checkpoint results, not a new test run
of later sandbox work. The [CR-EXT-R1 pack](../../artifacts/2026-11-capstone/final-bench-order/README.md)
contains the electrical/hydraulic model evidence and offline verification tools.
No new physical bench, physical calibration, safety certification or live-model
qualification is claimed.

## Extended-bench diagram and next physical steps

The [PDF](../hardware/extended-rig/CR-EXT-R1/CertaRig_Extended_Bench_Circuit_CR-EXT-R1.pdf)
and [editable SVG](../hardware/extended-rig/CR-EXT-R1/CertaRig_Extended_Bench_Electrical_CR-EXT-R1.svg)
show power domains, independent cutoff, acquisition and host isolation. This is
a module/interface diagram. Internal component-level supplier schematics for
S01/S02/S03, exact articles and physical tests remain required before fabrication
release. Drawing layout/labels were clarified without changing circuit topology.

Next: obtain supplier drawings and exact component data, review compatibility,
assemble the accepted design, calibrate sensors and perform attended cutoff,
restart and integrated-loop trials. CR-EXT-R1 supersedes the older candidate
baskets and budget assumptions preserved in the archived draft reports.

## Current development

A local sandbox for Python/SPICE analysis and trusted rehearsal is in progress.
The [development snapshot](../../artifacts/2026-11-capstone/sandbox-development/README.md) is
published separately from the completed source, with its qualification boundary.

Publication source base: `9412482a15dfa4459edff2437c9d619656e0dcf5`. Generated deliverables retain their original
contents and file names; the outer publication manifest records SHA-256 hashes.
