# Extended bench requirements CR-EXT-R1

Frozen sourcing requirements, not an unconditional fabrication release. Start with ORDER_LIST.md. S01/S02/S03 include complete engineered assemblies; actual supplier schematics and selected hydraulic data must be reviewed before custom fabrication.

Offline tools are in tools/bench_spec_validation/. Full raw traces and portable PDF/HTML pack are stored in the task outputs/final-bench-order folder and ZIP, outside this source checkout. No physical qualification or deployed control changes are claimed.

Focused validation: ruff check tools/bench_spec_validation; python3 tools/bench_spec_validation/validate.py verify /absolute/path/to/final-bench-order. Rerun with ngspice47: python3 tools/bench_spec_validation/validate.py run /absolute/path/to/new-evidence. No paid model/provider calls.
