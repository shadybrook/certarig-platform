# Provenance

`certarig/edge/` was imported on 2026-09-12 from the Phase 3 proof-of-concept repository
`https://github.com/shadybrook/certarig-phase-2-poc` at commit `23988a3`
("Add Phase 3 sensor guardrail shadow evidence"), package `certarig_edge` version 0.3.0.

The PoC repository is frozen as the evidence source for the Phase 3 submission and is not
modified by this project. All refactoring happens here.

What was imported unchanged (apart from typing fixes required by the stricter gates):

- `commissioning.py` (`ProcessGuardrail`, `DryBenchInterlock`)
- `live.py` (`LiveBenchRuntime`, live HTTP handler)
- `app.py`, `executor.py`, `safety.py`, `evidence.py`, `config.py`, `models.py`, `client.py`
- `hardware/{base,mock,raspberry_pi}.py`
- the seven `tests_py` suites, now under `tests/unit/`
- `config/rig.example.json`, `config/rig.wave1.json`, `config/edge.env.example`
- the vanilla ESM dashboard (`index.html`, `styles.css`, `src/*.mjs`) under `studio/`

Dropped: `mcp_server.py` (superseded by the manifest-driven agent tool registry).

Phase 3 submission artefacts retained in this tree (circuit, BOM, CSVs, photos, sidecar bundles) are mapped in `docs/phase3-submission/README.md`. They are copies for retrieval, not a licence to edit the frozen PoC.
