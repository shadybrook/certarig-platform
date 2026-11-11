# Validation record -10 November2026

Model revision CR-EXT-R1. No connection to the physical rig. Existing Phase3 card/harness and earlier evidence packs were preserved.

- 47 ngspice47 electrical experiments:44 required normal/containment/refusal experiments and3 intentionally unsafe electrical controls. All match their declared outcomes.
- 6 RK4 branch-inertance/compliance transients:5 inside the stated observation envelope and1 intentionally unsafe overpressure comparison. Every integration sample is saved. The unsafe window is fixed at203.2ms and stops before the first vacuum/cavitation domain departure; no nonphysical negative-pressure result is presented as valid.
- 21 temporal safety/startup cases, including healthy execution, independent loop failures, static heartbeat, held/early permit, held RESET, welded EDM, a commanded-output bypass control and delayed/lost/never-arriving READY. They are a functional requirements model, not actual relay firmware or SIL/PL qualification.
- 42 calculated checks cover hydraulic envelopes, pressure protection, loop hold-up, current/timer corners, SOA/thermal requirements, stored coil energy and60min water heat balance. The declared30W heat includes both loads. A3L/30C case stays below40C; smaller inventory/higher ambient require the modeled trip.
- 3 smaller-time-step comparisons pass their declared tolerances. Numerical convergence does not validate hardware assumptions.

A startup dependency was corrected: the powered-down S01 cannot supply READY before its upstream K1/K2 close. Final sequence is arm with permit LOW, await READY, observe permit LOW while ready, then accept a fresh permit edge. The early/held-permit and READY-loss sequences are included.

The first pump SPICE prototype had an RC loading error that prevented arming. It was corrected with an explicit buffer, and fault criteria now require pre-fault actuation or an actually excited fault current/trip. A safe output caused merely by never starting does not pass the fault experiment. An open-burden startup numerical failure was corrected with explicit wiring capacitance; that aborted trace is not counted. Raw ngspice text at12 printed significant digits can contain adjacent equal timestamps at discontinuities; verifier requires nondecreasing time, correct vector shape, finite values, expected sample count and complete horizon.

The main power block is an explicit bounded equivalent. It does not simulate LM5069 internal dynamics or prove the separately specified8A/20us overshoot limit. Actual supplier gate/choke/PCB, S03 differential/Hall conditioners, power-off sequencing, fuse coordination and valve/relief/arrestor behavior need exact article/drawing review. These remain mandatory before custom fabrication, followed by physical commissioning. No unknown assembly is qualified by specifying a favorable bound.

Verification recomputes electrical metrics from recorded CSV; hydraulic extrema from every raw integration sample and an independent deterministic rerun; safety states and thermal/bound checks from recorded parameters. SHA256 proves consistency only. Missing/corrupt/partial-trace negative verification checks are recorded separately. Report generation and the static viewer use no network at open time and no paid provider.

Skill-capture review: the existing validate-bounded-spice-circuits workflow covers this verified method; reused it without creating a duplicate skill. GBrain MCP tools were unavailable.
