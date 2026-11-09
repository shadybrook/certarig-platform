# Electrical extension: bounded simulation R1

The extension has a reproducible ngspice 47 electrical model. It is a candidate design experiment, not a construction or procurement release. The preserved Phase 3 circuit and Pi installation were not operated or changed.

The matrix contains 54 scenarios: 48 required passing cases and six unsafe comparison cases that must fail their acceptance checks. Required cases cover startup, reset/E-stop behavior, missing heartbeat, power loss, single output faults, load/supply corners, ADC power-off/overrange protection and pulse level conversion. A combined welded permit contact plus shorted output remains unsafe until the separately modeled cutoff opens. Two smaller-step repeats examine numerical sensitivity.

```sh
python3 tools/circuit_validation/run_spice.py --out /path/to/new-evidence
python3 tools/circuit_validation/verify_evidence.py /path/to/new-evidence
```

Only Python stdlib and ngspice are required. `--select` limits cases; a subset is not the complete gate. `--reuse` requires the same engine version and exact circuit identity, then replays acceptance from complete saved samples. A fresh output directory performs fresh numerical solves.

Each case retains a netlist, engine log, compressed trace and result JSON. The runner rejects incomplete/nonconverged transients even when ngspice exits zero. It emits a checksum manifest; the verifier reproduces generated circuit identities, reported measurements and acceptance decisions without ngspice. This establishes evidence consistency, not authenticated provenance or independent qualification of the component models.

The delivered review pack, alongside this implementation workspace, contains the four-sheet PDF, editable SVGs, primary-source links, model inventory, missing/corrupt-evidence tests and all saved traces. In the originating Codex task it is under `outputs/extended-rig-simulation`.

The candidate replaces the rejected 12 V/150 ohm current-loop combination with a 24 V instrumentation/100 ohm receiver envelope and input isolation/protection. It separates current channels and adds modeled inductive suppression, reset authority and independent interruption paths. These are behavioral IC equivalents, not selected vendor macromodels. No transistor-level hardware latch, GPIO translation, actual BLDC pump, fuse coordination, pressure protection, EMC or thermal qualification is claimed. Pulse absence remains ambiguous between zero flow and source failure. Voltage-feedback reception is modeled; closed-loop software feedback-trip response is outside this matrix.

Before building, freeze exact component variants and ratings, replace functional blocks with actual reviewed circuits, resolve the pressure sensor's conflicting range data, complete the pin/terminal wire schedule and matched delivered basket, then perform the physical commissioning gates. Do not connect new loads through the old indicator-only circuit.

Validation for this increment: targeted Ruff format/lint; complete 54-scenario gate; saved-sample replay; missing/corrupt-evidence rejection; fresh single-case CLI reproduction. Application code is unchanged, so historical application regressions were not rerun for this standalone simulation addition.
