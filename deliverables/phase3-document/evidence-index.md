# Evidence Index — CertaRig Phase 3 Document

Maps every factual claim in `CertaRig_Phase3_Document.md` to its evidence source in this repository. Paths are relative to the repo root.

## Architecture and design claims

| Claim | Evidence source |
| --- | --- |
| Agent interprets natural language; deterministic kernel measures, compares, latches, owns the output; agent reaches the rig only via the Edge API filtered by a capability manifest | `README.md` (intro + "What is deterministic vs what is the model" table); `certarig/edge/commissioning.py` (`ProcessGuardrail`, `DryBenchInterlock`) |
| Edge API is the product control plane; SSH GPIO commands and operator gpiozero are not the product path; gpiozero is the kernel's internal Pi driver (`GPIOZERO_PIN_FACTORY=lgpio`) | `README.md` (opening paragraph); `docs/platform-lab/product-state.md` ("Lab host facts"); `skills/ops/safe_powerdown/SKILL.md` (12 Sep SSH improvisation vs procedure) |
| Output invariant: OUTPUT = enabled AND permit AND not-tripped AND E-stop-closed AND healthy; unsafe state clears permit and latches safe; recovery = healthy → reset → permit | `docs/explainer/2026-09-13-gates-0-to-5-analysis.md` ("The problem CertaRig is solving", `ProcessGuardrail.drive_high` condition); `certarig/edge/commissioning.py` |
| GPIO23 is the relay output pin, owned exclusively by the kernel | `README.md` (Safety notes); `certarig/edge/live.py`, `certarig/edge/ops.py`; `docs/platform-lab/product-state.md` ("Two kernels must not both own GPIO23 / ADS1115") |
| `bypass_interlock` and `override_limits` do not exist as callable tools | `README.md` ("What is deterministic vs what is the model") |
| Evidence bundles with checksums are first-class outputs (CSV, `run.json`, `report.md`, SHA-256; adapter class + hostname; outcomes ledger) | `README.md` (kernel/agent table; step 7 "Evidence"); `certarig/edge/evidence.py` |
| `reset_trip` / `shutdown` require human approval; agent gets HTTP 428 deep-link | `README.md` (step 5 "Approvals"); `tests/contract/test_ops_api.py`, `tests/contract/test_agent_api.py` |
| Approved shutdown path is `safe_powerdown` (kernel forces safe first) then human-approved `shutdown` (refuse if a run is active, force safe, flush evidence, then power-off). 12 Sep halt was still SSH; the procedure is implemented and software-tested, not a Gate 4 hardware run | `skills/ops/safe_powerdown/SKILL.md` and `procedure.yaml` (`force_safe` then hold); `certarig/edge/ops.py` (`shutdown` forces `command("safe")`); `README.md` (Raspberry Pi section); `certarig/agent/policy.py` (after `safe_powerdown` passed → export → shutdown) |
| Studio views: Live, Onboard, Author, Procedures, Approvals, Agent, Evidence; SDK; sim serve / Docker path; under-ten-minutes stranger path | `README.md` ("Clone to a simulated run"); `studio/` |
| Dry-bench hardware: two potentiometers (pressure/flow), ADS1115 ADC, physical E-stop, low-voltage relay; Raspberry Pi 3 Model A+ | `docs/explainer/phase3-film/script.md` (2:20–3:20 customer section); `docs/platform-lab/product-state.md` ("Lab host facts"); as-built circuit `docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png` |
| Guardrail limits 4.2 bar and 15.0 L/min | `config/rig.example.json` (`pressure_abort_bar: 4.2`, `safe_max: 4.2` / `15.0`); `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` ("Keep these facts") |
| Cover identity: Course Title Study Project; Student ID 2023EB03005; Advisor Professor Raj Kumar | Submitted Phase 2 report (Google Doc `1d3Xguv-8qeDTHnpuTDTPGu-XgSUYmM6fnER9rABAyp4`); `docs/PHASE2_SUBMISSION.md` in the PoC tree. GBrain has no separate identity page; advisor name also on `projects/certarig-phase3-professor-scope-2026-09-07` |
| 7 Sep advisor freeze: dry Wave 1 bench is Phase 3 proof; water loop deferred; circuit/architecture/photographs/live demo/video required | GBrain `projects/certarig-phase3-professor-scope-2026-09-07` |
| 16 Sep video brief: beginner-friendly film, end customer, AI choice + benchmark + fallback, stitched PoC, capstone | GBrain `projects/certarig-video-production-brief-2026-09-16` |
| As-built pin map, red/green indicators, GPIO25 unused, broken-NC1 not tested | GBrain `projects/certarig-phase3-integrated-bench-pass-2026-09-12`; `docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.svg` |
| BOM / inventory IDs R01–R17, Robu INV2627/225826 dated 4 Sep 2026 | `docs/phase3/CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.md` |

## Phase 1 / Phase 2 recap

| Claim | Evidence source |
| --- | --- |
| Problem definition (audit-hard test records; LLM must not own the safety decision) | `docs/explainer/2026-09-13-gates-0-to-5-analysis.md` ("The problem CertaRig is solving"); `docs/explainer/phase3-film/script.md` (0:20–1:30) |
| Phase 2 PoC: `certarig_edge` package, live dashboard, imported at commit `23988a3`; what was imported; `mcp_server.py` dropped | `docs/PROVENANCE.md` |
| Incremental Phase 2 bench validation 9–12 Sep (ADS1115 commissioning, pot sweeps, E-stop, integrated bench) | `pi_retrieval_2026-09-12/phase3_evidence/` (dated run folders) |
| Phase 3 submission system frozen on the Pi, port 8080, observe-only, until 21 Sep | `README.md` (second paragraph); `docs/platform-lab/product-state.md` ("World A") |

## 12 September 2026 dry-bench lab (gates and hardware numbers)

| Claim | Evidence source |
| --- | --- |
| Six gates, Gate 0–5, and what each established | `docs/explainer/2026-09-13-gates-0-to-5-analysis.md` ("What each gate established"); `docs/platform-lab/2026-09-12-dry-bench.md` ("Gate results" table) |
| Gate 0: no `/opt/certarig`, no `/etc/certarig/edge.env` | `docs/platform-lab/2026-09-12-dry-bench.md` (Gate results); analysis doc, Gate 0 section |
| Gate 1: sidecar `~/certarig-platform`, port 8081, user-local env, `install_pi.sh` never run | `docs/platform-lab/2026-09-12-dry-bench.md`; `docs/platform-lab/product-state.md` (Lab host facts) |
| Gate 2 first attempt FAILED (P1 never raised; channel invalid; ADC dipped below 0); failure retained; run `run_20260912T162352_6515a9` | `docs/platform-lab/2026-09-12-dry-bench.md` ("Pulled bundles" table, first row) |
| Gate 2 pass: 1,291 samples over 129.0 s; peaks 8.10 bar / 17.67 L/min inside 10 bar / 20 L/min envelopes; run `run_20260912T164217_0362c1` | analysis doc (Gate 2 section); `docs/platform-lab/2026-09-12-dry-bench.md` (bundle table) |
| Gate 3: six exact procedure hashes passed in simulation; twin-gate mechanism (24-hour stamp) | analysis doc (Gate 3); `README.md` (Tests section); `tests/unit/test_twin_gate.py`, `tests/unit/test_stamp_gate.py` |
| Gate 4: Fake agent ran five approved procedures; per-procedure results (relay 5/5 checks; pressure peak 4.83 bar / 0.608 ms; flow peak 15.41 / 0.801 ms; dual 4.34 bar + 15.21 L/min, 9/9 checks; E-stop 0.867 ms, permit-before-reset rejected) | analysis doc (Gate 4 table); `docs/platform-lab/2026-09-12-dry-bench.md` (bundle table with run IDs and archive SHA-256s) |
| Gate 5: sidecar stopped, Phase 3 restored on 8080 observe-only, `test_phase3_untouched` passed, actuation disabled, Pi halted | `docs/platform-lab/2026-09-12-dry-bench.md`; `tests/hil/test_phase3_untouched.py` |
| Aggregate: after failed observation, six hardware runs passed; 3,422 samples; 34/34 evaluated checks | analysis doc (Executive summary) |
| Peaks vs guardrails: pressure 4.83 & 4.34 vs 4.2 bar; flow 15.41 & 15.21 vs 15.0 L/min; E-stop forced safe, no restart on release, permit-without-reset rejected | analysis doc (Executive summary, Gate 4); dry-bench doc |
| Sub-millisecond transitions are commanded-GPIO-state changes, NOT relay contact/electrical measurements (no contact feedback or current sensor) | analysis doc (Gate 4 caveat; "Relay state is command derived") |
| All seven exported archives and manifest files re-hashed successfully | analysis doc ("What the data says" point 5); archive SHA-256s in `docs/platform-lab/2026-09-12-dry-bench.md`; `docs/explainer/data/evidence_verification.json` |
| Agent transcripts show Fake agent reading skill, starting named procedure, waiting, reporting — never comparing | analysis doc ("What the data says" point 4) |

## Testing strategy and observed test results

| Claim | Evidence source |
| --- | --- |
| Test layers: unit (19 modules), contract, agent, property (Hypothesis), scenario, e2e Playwright, twin gate, HIL | `tests/unit/` (19 test modules), `tests/contract/`, `tests/agent/`, `tests/property/`, `tests/scenario/`, `studio/e2e/`, `tests/hil/`; `README.md` (Tests section); `Makefile` |
| 213 tests collected and all passed (unit+contract+agent+property+scenario) | Observed directly: `python3 -m pytest tests/unit tests/contract tests/agent tests/property tests/scenario` run 17 Sep 2026 in this environment (all passed; 213 collected) |
| 2 HIL tests, skip without bench; Phase 3 on :8080 checked only as "still the frozen dashboard" | `tests/hil/` (2 tests collected); `README.md` (Tests section) |
| 6 Playwright tests across 2 spec files; require Node 20; not run here | `studio/e2e/pressure_guardrail.spec.js` (2 `test(`), `studio/e2e/studio_honesty.spec.js` (4 `test(`); `README.md` |
| `make check` = lint, types, tests, 90% coverage; never requires the Pi; `make soak` = one simulated hour | `README.md` (Clone section + Tests section); `Makefile` |

## AI stack claims

| Claim | Evidence source |
| --- | --- |
| AI is used to translate varied operator language into approved procedures and explanations, while deterministic code performs arithmetic and safety decisions | `certarig/agent/orchestrator.py` (`SYSTEM_PROMPT`); `README.md` ("What is deterministic vs what is the model") |
| Runtime default is Fake: deterministic rule-based policy, no API key; used by CI and on the 12 Sep bench | `README.md` (LLM providers; step 6); `certarig/agent/providers/fake.py`; script.md (same section) |
| Claude Sonnet 4.5 is the first intended live choice because the adapter uses native tool-use blocks; exact model string is `claude-sonnet-4-5` | `certarig/agent/providers/anthropic_provider.py` (`DEFAULT_MODEL`, `to_anthropic_tools`, `parse_anthropic_response`); `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` (4:20–5:40) |
| OpenAI GPT-4.1-mini is the second choice; the adapter supports an OpenAI-compatible endpoint through `OPENAI_BASE_URL`; alternatives are configurable rather than automatic failover | `certarig/agent/providers/openai_provider.py` (`DEFAULT_MODEL = "gpt-4.1-mini"`, `base_url`); `README.md` (LLM providers) |
| Live adapters exist but are NOT the proven bench path; untested live | `README.md` ("Adapters are untested live in this tree; every CI path uses FakeProvider"); `docs/platform-lab/product-state.md` ("not proven") |
| Replay provider / exact transcript re-runs | `certarig/agent/transcript.py`, replay references in `certarig/agent/orchestrator.py`, `certarig/agent/cli.py`; script.md |
| Use-case benchmark criteria: approved-skill routing, manifest-limited tools, no numeric safety decision, approval stops, and reproducible replay | `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` (4:20–5:40 benchmark cards); `certarig/agent/orchestrator.py`; `config/capabilities.wave1.json`; `tests/agent/`; `tests/contract/test_agent_api.py`; `tests/contract/test_ops_api.py` |
| Fake has hardware-transcript and automated-test evidence; no live Claude/OpenAI comparative benchmark has been run | `docs/explainer/2026-09-13-gates-0-to-5-analysis.md` ("What the data says" point 4); `README.md` (LLM providers); `tests/agent/test_providers.py`, `tests/agent/test_policy.py`, `tests/agent/test_orchestrator.py` |
| Never claim a simulated trace is hardware; never claim an LLM tripped the relay | script.md ("Production grammar" rules) |

## Limitations claims

| Claim | Evidence source |
| --- | --- |
| Exported bundles reference raw hardware CSV by filename/rows/hash but the CSV is missing; fix = include recording + hash-verify contract test | analysis doc ("Raw hardware recordings are referenced but not exported" + Correction); `README.md` ("do not contain the referenced raw physical CSV recordings") |
| Commissioning interview not built; Onboard is a form (config table + typed bench briefing), not discovery | `docs/platform-lab/commissioning-interview.md` ("What already exists instead"); `docs/platform-lab/product-state.md` ("not proven / not built") |
| Fieldbus: MQTT/Modbus TCP observe-only real adapters; OPC UA, S7, EtherNet/IP, CAN observe-only examples/directions | `docs/platform-lab/product-state.md`; `README.md` (step 2); script.md (3:20–4:20 "Every fieldbus example ships observe-only") |
| WatchdogSec=30 is a supervisor heartbeat, not a SIL loop | `README.md` (Raspberry Pi section) |
| One kernel may own GPIO23/ADS1115 at a time | `docs/platform-lab/product-state.md` (Lab host facts) |
| Operator keys ≥ 12 chars, distinct from agent key; keys only in `.env` / `/etc/certarig/` / `~/.ssh` | `README.md` (Safety notes) |

## Capstone / future-work claims

| Claim | Evidence source |
| --- | --- |
| Capstone: deployable agentic test-operations layer for someone else's mapped rig; interview proposes map, human applies, twin rehearses, explicit arm. Not photo-to-control: a diagram/photo may be sidecar context, never permission to energize | `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` (Capstone note); script.md (11:00–11:50); `docs/platform-lab/commissioning-interview.md`; analysis doc ("does not yet discover an unknown bench from a photograph or circuit diagram") |
| End customer: owner/commissioner of a test bench (lab engineer, technician, team needing auditable records); tomorrow anyone with a mapped rig (hydraulic cart, battery pack on CAN, Siemens/Allen-Bradley cell, Modbus skid) | script.md (2:20–3:20 "Who is the end customer" and 3:20–4:20 industries) |
| Target growth areas and enabling advances: electrified/connected/software-defined equipment; low-cost edge computing, structured industrial protocols, tool-using model APIs, digital twins, and hashing | Product-direction rationale in `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` (3:20–5:40); presented in the document as an unquantified hypothesis requiring capstone customer validation |
| Governing invariant: no unreviewed mapping can reach an output | analysis doc ("Recommended next milestone") |
| Second simulated plant (e.g. thermal) before another physical output | analysis doc ("The bench is mapped, not discovered" Correction); `docs/platform-lab/product-state.md` ("Next product step"); thermal skill: `config/rig.thermal.sim.json`, `README.md` step 4 |
| Relay feedback / current sensing next | analysis doc ("Relay state is command derived" Correction) |
| Interview questions (modules, bus, pin/register/tag mapping, trip numbers/units, observe-only scope) | `docs/platform-lab/commissioning-interview.md` (Interview section); script.md (11:00–11:50) |
| Capstone readiness is bounded: core platform and one hardware path are proven, while live-provider qualification, second-rig validation, complete exports, and electrical feedback remain gates | Phase 3 document Sections 3, 6, and 7; analysis doc ("Recommended next milestone"); `docs/platform-lab/product-state.md` |

## Deliverables claims

| Claim | Evidence source |
| --- | --- |
| Gates 0–5 evidence & product-direction report (PDF + DOCX) | `deliverables/CertaRig_Gates_0_to_5_Evidence_and_Product_Direction.pdf` / `.docx` |
| Phase 3 submission film v4 (13.4 min, paper explainer motion + Studio\|bench split; atelier retired) | https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Film.mp4 ; cut list `tools/phase3_edit/edl/phase3_film_v4.json`; rebuild `python3 tools/render_phase3_explainer.py` |
| Uncut clap-synced bench run (29.6 min, 1310\|608 split) | https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Bench_Run.mp4 |
| Action windows only (no VO) | https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Action.mp4 |
| As-built circuit map (SVG/PNG/PDF) | `docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png` (also `.svg`, `.pdf`) |
| Hardware inventory register / BOM | `docs/phase3/CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.md` (+ PDF) |
| Derived data: hardware run summary, evidence verification record | `docs/explainer/data/hardware_run_summary.csv`, `docs/explainer/data/evidence_verification.json` |
| Source footage Drive folder | https://drive.google.com/drive/folders/1mlegZnq_AQurnBIKY-Ckh1S6TyZ_Q8Bk |

## Items NOT verifiable in this repository

- `docs/platform-lab/shoot-handoff-20260917.md` — listed as research input but does not exist in the tree.
- `evidence/` folder (lab-pulled bundles, sim-library, agent transcripts) — gitignored per `docs/platform-lab/2026-09-12-dry-bench.md`; hardware numbers are cited from the committed lab record and analysis instead.
- Course title, student ID, and advisor are filled from the submitted Phase 2 report (Study Project / 2023EB03005 / Professor Raj Kumar). GBrain has no dedicated identity page for those three fields.
- `.cursor/skills/professor-bench-demo/SKILL.md` — cited as a professor-brief source in the 18 Sep plan; not present in this tree. Professor-brief checks used GBrain `projects/certarig-phase3-professor-scope-2026-09-07`, `projects/certarig-video-production-brief-2026-09-16`, `docs/platform-lab/product-state.md`, `README.md`, `skills/ops/safe_powerdown/`, and `docs/platform-lab/commissioning-interview.md`.
- Comparative live-LLM benchmark requested on 16 Sep remains unrun.
- Nothing was written onto `certarig-phase3-*` GBrain pages from this session.
