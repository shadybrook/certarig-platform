# Sourced-component design review

This tooling evaluates bounded component-selection envelopes. It does not operate equipment or release a physical design. The source snapshot is `docs/capstone/INDIAN_PURCHASE_CANDIDATES.json`; the detailed limitations and procurement holds are in `docs/capstone/INDIAN_PURCHASE_REVIEW.md`.

From the repository root, with Python 3.11+ and ngspice on PATH:

```sh
python3 tools/procurement_validation/run_review.py run /absolute/path/to/new-review
cp docs/capstone/INDIAN_PURCHASE_CANDIDATES.json /absolute/path/to/new-review/basket.json
python3 tools/procurement_validation/render_review.py /absolute/path/to/new-review
# Optional figure: requires matplotlib; simulation and offline replay use stdlib only.
python3 tools/procurement_validation/plot_review.py /absolute/path/to/new-review
python3 tools/procurement_validation/run_review.py manifest /absolute/path/to/new-review
python3 tools/procurement_validation/run_review.py verify /absolute/path/to/new-review
```

Each experiment is solved by ngspice, with a complete finite transient, exact netlist, log and compressed samples. The verifier regenerates netlists, recomputes measurements and checks the complete declared case matrix. Deliberately unsuitable cases must reject their declared design criteria; they are not reported as safe operating cases. Invalid/incomplete numerical solves abort the run instead of counting as detected faults.

The earlier `circuit_validation/run_spice.py` supplies the behavioral control-state circuit. The integrated pump is replaced with an explicitly bounded input model, not an RL motor or a manufacturer-certified BLDC model. Nominal and startup-envelope results must be interpreted separately. The DRV8871 thermal comparison is a different circuit from the integrated generic MOSFET stage. The 120ohm receiver experiment represents a burden-input hazard, not the full buffered SEN0262 board. Hydraulic calculations are separately labelled assumed steady networks; they do not qualify a selected valve or bypass.

Stock, delivery, unknown parameters, assembly, calibration and budget remain separate release gates. Prices in the snapshot must be refreshed before any eventual order. No provider calls, orders or vendor messages occur in these tools.

## Paired rejection mitigations

`run_closure.py` preserves eight original unsafe controls and adds 23 mitigation, calibration, power-off, startup, overload, short, E-stop, capacitor and refinement cases. The focused power-stage model is an explicit proposal, not a TPS25940L macromodel or the complete independent-cutoff assembly. Its fault energy remains a device-SOA selection constraint. The receiver refusal/reset code is an offline reference, not deployed Edge behavior. The signed Phase3 scope and current cost choices are traced in `docs/capstone/REJECTION_MITIGATIONS.md`.

```sh
python3 tools/procurement_validation/run_closure.py run /absolute/path/to/new-closure-review
python3 tools/procurement_validation/run_closure.py verify /absolute/path/to/new-closure-review
```

A fault-containment counterpart uses its own declared refusal criteria. Original measurement/run criteria are retained and still fail for the corresponding unsafe controls. An open burden or unpowered ADC is never treated as a healthy observation to obtain a green result.
