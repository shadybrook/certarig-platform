# Phase 3 — Implementation Readiness & Validation

---

## Cover Page

| Field | Value |
| --- | --- |
| Course Title | [Course Title — to be filled] |
| Project Title | CertaRig — An Evidence-First, Agent-Guided Test-Operations Platform |
| Student Name | Chintan Dedhia |
| Student ID | [Student ID — placeholder] |
| Project Advisor / Supervisor | [Advisor / Supervisor name — placeholder] |
| Date of Submission | 20 September 2026 |

---

## 1. Introduction

### 1.1 Purpose of Phase 3

Phase 3 asks whether CertaRig is ready to move from proof of concept to capstone development. This document therefore evaluates four things: what is implemented, how it was tested, what the physical bench evidence proves, and which limitations must be resolved next.

CertaRig is a test-operations platform for instrumented test benches ("rigs"). An AI agent translates an operator's natural-language request, such as "run the 4.2 bar pressure test," into an approved procedure. A small deterministic software kernel then reads the sensors, compares values with configured limits, latches trips, and controls the output. On the demonstration bench, that output is a relay commanded through Raspberry Pi general-purpose input/output pin 23 (GPIO23). Every run produces checksummed evidence. The central design question is therefore not "can an AI operate a rig?" but "who is allowed to authorize a physical output?" CertaRig's answer is the kernel, never the language model.

### 1.2 Summary of Work Completed So Far

**Phase 1 — problem definition and planning.** Phase 1 defined the problem: modern test benches combine sensors, manual procedures, relay outputs, spreadsheets, and screenshots; test records are hard to audit, and inserting a language model directly into the safety decision would be unacceptable. Phase 1 scoped a low-voltage dry bench (two potentiometers emulating pressure and flow, an ADS1115 analog-to-digital converter, a physical emergency stop, and a relay) as the demonstration target, and planned a staged path from observation to controlled actuation.

**Phase 2 — design and proof of concept.** Phase 2 produced the design and the proof-of-concept implementation: the `certarig_edge` package with the `ProcessGuardrail` safety kernel, the `DryBenchInterlock`, a live observe-only dashboard, procedure execution, and evidence writing. That proof of concept was validated incrementally on the bench (ADS1115 commissioning, potentiometer sweeps, dual-potentiometer sweeps, E-stop tests, and integrated bench runs recorded between 9 and 12 September 2026, retained under `pi_retrieval_2026-09-12/phase3_evidence/`). The PoC repository is frozen as the Phase 3 evidence source; the platform repository documented here was imported from it at commit `23988a3` and is where all further engineering happens (see `docs/PROVENANCE.md`).

**Phase 3 — implementation and validation (this document).** The PoC was developed into a deployable platform: Edge API, Studio operator console, digital twin, provider-neutral agent, and evidence pipeline. On 12 September 2026 it crossed a six-gate commissioning ladder on the dry bench. Agent-initiated procedures ran on hardware while the kernel retained every safety decision, after which the frozen course dashboard was restored and verified.

---

## 2. Implementation Overview

### 2.1 Implementation Status

**Fully implemented and validated:**

- Deterministic safety kernel (`certarig/edge/`): sensor quality checks, numeric limit comparison, trip latching, anti-restart, and exclusive ownership of the output (GPIO23 on the bench; a simulated output otherwise). The output invariant is: **OUTPUT = actuation enabled AND permit requested AND trip not latched AND E-stop closed AND process healthy.** Any unsafe sensor state, invalid quality, or open E-stop clears the permit and latches safe; recovery requires a healthy observation, an explicit reset, then a new permit.
- Edge HTTP API with capability-manifest filtering: the agent reaches the rig only through this API, and dangerous operations (`bypass_interlock`, `override_limits`) do not exist as callable tools.
- Procedure library shipped as documented skills (`skills/`): relay truth table, pressure guardrail, flow guardrail, dual-input guardrail, emergency-stop anti-restart, ADC validation, thermal soak — each a `SKILL.md`, a `procedure.yaml` contract, and simulator scenarios.
- Digital twin (`certarig/sim/`) with a scenario domain-specific language and invariant checks, plus the **twin gate**: a procedure whose hardware mode is `raspberry_pi` will not start unless the identical procedure hash has passed on the simulator within the previous 24 hours.
- Evidence pipeline: every run writes a CSV recording, `run.json`, `report.md`, and SHA-256 checksums; bundles export as checksummed zip archives naming the adapter class and hostname; run outcomes append to a ledger.
- Provider-neutral agent orchestrator (`certarig/agent/`) with the deterministic **Fake** provider as the default (rule-based, no API key — the provider used in all continuous integration and on the hardware bench), plus a replay capability for re-running transcripts exactly.
- Studio operator console (browser-based: Live, Onboard, Author, Procedures, Approvals, Agent, and Evidence views) and a Python SDK.
- Human-approval workflow: an agent cannot invoke `reset_trip` or `shutdown` without a human grant; an unapproved attempt receives HTTP 428 and deep-links to the Approvals view.

**Partially implemented (present in the tree, not yet validated end-to-end):**

- Live language-model adapters: Anthropic Claude Sonnet 4.5 (`certarig/agent/providers/anthropic_provider.py`, first choice because tool use is first-class) and OpenAI GPT-4.1-mini or any OpenAI-compatible endpoint (`openai_provider.py`, fallback). These adapters exist and are unit-tested, but they are **not** the proven bench path: the 12 September hardware procedures ran on the Fake provider, and no live-key operation has been validated.
- Fieldbus adapters: MQTT and Modbus TCP ship as real **observe-only** adapters; OPC UA, Siemens S7, EtherNet/IP, and CAN are targeted directions with observe-only examples, not validated integrations.
- Evidence export completeness: exported bundles reference each raw hardware CSV by filename, row count, and SHA-256 hash, but do not yet contain the CSV file itself (detailed in Section 6).

**Planned, not implemented:**

- The agent-led commissioning interview (design in `docs/platform-lab/commissioning-interview.md`): a stranger describes their bench, the agent proposes a `rig.json` map, a human applies it. Today's Onboard view is a writable configuration form with a typed bench briefing — useful, but a form, not discovery.
- Relay contact feedback or load-current sensing (needed before any end-to-end electrical trip-latency claim).
- Enterprise concerns: single sign-on, billing, NI-DAQ / PLC write paths.

### 2.2 Implemented Features

| Feature | Description |
| --- | --- |
| Safety kernel | Deterministic guardrail owning measurement, comparison, trip latching, and the physical output; enforces the five-condition output invariant |
| Six bench qualification procedures | ADC validation, relay truth table, pressure guardrail (4.2 bar), flow guardrail (15 L/min), dual-input guardrail, E-stop anti-restart; a thermal-soak skill is an additional simulator extension |
| Digital twin + twin gate | Simulator rehearsal required within 24 hours before the identical procedure hash may run on hardware |
| Agent orchestrator | Interprets operator language, selects an approved skill, starts the named procedure, waits for the deterministic result; never compares numbers |
| Provider neutrality | Fake (default, deterministic), Anthropic, OpenAI/compatible, and transcript replay behind one interface |
| Evidence bundles | Checksummed zip per pull; per-run CSV, `run.json`, `report.md`, events, checks, SHA-256 manifest; outcomes ledger |
| Studio console | Live dual-channel graphs with trip lines, ready-to-arm scorecard, onboarding config diff/apply, procedure authoring and approval, agent chat, evidence export |
| Approvals | Agent requests for `reset_trip` and `shutdown` are gated on explicit human grants |
| Observe-mode adapters | MQTT and Modbus TCP observation of external tags/registers |
| Deployment | `make install` / Docker Compose simulator path for a stranger; `deploy/install_pi.sh` + systemd for a new Raspberry Pi (with guards refusing to run over the frozen Phase 3 host) |

### 2.3 Why This AI, Benchmarking, and Fallbacks

**Why use AI at all?** Test operators express intent in varied language, while rigs require exact procedure identifiers, units, and ordered steps. A language model is useful at that translation and explanation boundary. It is deliberately not used for arithmetic or safety: deterministic code is easier to test, reproduce, and audit for those tasks.

**Why these specific choices?** The proven runtime choice is **Fake**, a deterministic rule-based provider. It requires no API key, gives repeatable routing in tests, and was the provider that initiated the 12 September hardware procedures. For a future live interpreter, the first configured choice is **Anthropic `claude-sonnet-4-5`** because its API exposes tool use directly and the adapter maps CertaRig's provider-neutral tool schema to native tool-use blocks. The second choice is **OpenAI `gpt-4.1-mini`** through the OpenAI API; the same adapter can target an OpenAI-compatible endpoint through `OPENAI_BASE_URL`, including a local service. Transcript replay is a further deterministic regression option. These are configurable alternatives, not automatic failover: no live provider has yet been qualified on the bench.

The benchmark is specific to CertaRig, not a general chat or trivia score:

| Use-case criterion | Required behaviour | Current evidence |
| --- | --- | --- |
| Approved-skill routing | Map operator wording to the correct approved procedure | Fake routed the lab procedures; agent policy and orchestrator tests pass |
| Tool discipline | Call only tools exposed by the capability manifest | Enforced by manifest filtering and contract tests; dangerous tools remain unavailable |
| Safety-boundary discipline | Never compare live values or claim to make a trip decision | Fake transcripts show read skill → start procedure → wait → report kernel result |
| Human boundary | Stop for approval on `reset_trip` and `shutdown` | HTTP 428 approval flow is covered by contract tests |
| Reproducibility | Preserve and replay the complete interaction | Transcript and strict replay providers are implemented and tested |
| Provider comparison | Run the same prompt suite unchanged across candidates | Pending for Claude and OpenAI; live adapters are unit-tested only |

This benchmark establishes a clear admission rule for the capstone: Claude or the OpenAI fallback may assist on a real rig only after passing the same routing, tool, approval, refusal, and replay cases as Fake. Phase 3 validates the deterministic provider and the individual policy, approval, and replay mechanisms; it does **not** report a live-model comparison that was never run.

---

## 3. System Validation and Testing

### 3.1 Testing Strategy

Validation is layered so that no procedure reaches hardware without having survived every cheaper layer first:

1. **Unit tests** (`tests/unit/`, 19 modules) — kernel state machine, guardrail predicates, procedure runner, evidence bundling, configuration and safety validation, simulator, twin gate, Raspberry Pi hardware abstraction.
2. **Contract tests** (`tests/contract/`) — the Edge, agent, ops, procedure, and simulator HTTP APIs against their schemas, including authentication and approval flows.
3. **Agent tests** (`tests/agent/`) — orchestrator policy, provider adapters, skill registry, and authoring; all CI paths use the Fake provider.
4. **Property-based tests** (`tests/property/`) — a Hypothesis state machine drives the kernel through arbitrary command/sensor sequences and asserts the output invariant and anti-restart property can never be violated.
5. **Scenario tests** (`tests/scenario/`) — every shipped skill scenario executes against the digital twin with invariant checks.
6. **End-to-end tests** (`studio/e2e/`, Playwright) — browser-level flows against `certarig sim serve`: the pressure-guardrail journey and Studio honesty checks (6 tests across 2 spec files; require Node 20).
7. **Digital-twin gate** — the operational enforcement that a hardware procedure hash must match a simulator pass from the last 24 hours.
8. **Hardware-in-the-loop** (`tests/hil/`) — bench tests that skip unless a live node reports `ready_to_arm`, plus `test_phase3_untouched.py`, which verifies the frozen Phase 3 dashboard was not altered.

`make check` (lint, types, unit/contract/agent/property/scenario at 90% coverage) never requires the Pi.

**Test-suite result observed for this document:** all 213 collected tests in the unit, contract, agent, property, and scenario suites passed (`python -m pytest tests/unit tests/contract tests/agent tests/property tests/scenario`, run 17 September 2026 in a fresh environment). The 2 hardware-in-the-loop tests collect but skip without the bench, and the 6 Playwright tests were not run in this environment (Node 20 not provisioned); their presence and scope are stated from the repository, not from an observed run.

### 3.2 Test Cases and Results

The decisive validation was the 12 September 2026 dry-bench lab, structured as six commissioning gates (Gate 0 through Gate 5). Results below are from the verified lab record (`docs/platform-lab/2026-09-12-dry-bench.md` and the evidence analysis in `docs/explainer/2026-09-13-gates-0-to-5-analysis.md`).

| # | Feature Tested | Expected Result | Observed Result | Status |
| --- | --- | --- | --- | --- |
| G0 | Read-only boundary inspection of the frozen Phase 3 system | Phase 3 tree present; no platform files in privileged locations | Phase 3 tree intact; no `/opt/certarig`; no `/etc/certarig/edge.env` | Pass |
| G1 | Isolated sidecar deployment | Platform serves from a separate folder and port with user-local config, without touching Phase 3 | Served from `~/certarig-platform` on port 8081; `install_pi.sh` never run; Phase 3 untouched on port 8080 | Pass |
| G2a | Observe-only ADC validation (first attempt) | Complete P1/P2 sweep within validation envelopes | **Failed** — the P1 (pressure) sweep was never raised and the channel went invalid; failure retained as evidence | Fail (retained) |
| G2b | Observe-only ADC validation (second attempt) | Complete sweep, both channels valid, output authority off | Passed: 1,291 samples over 129.0 s; peaks 8.10 bar / 17.67 L/min, inside the 10 bar / 20 L/min validation envelopes | Pass |
| G3 | Digital-twin gate | Six exact procedure hashes pass in simulation before hardware | All six simulator stamps recorded and matched by the hardware runs | Pass |
| G4a | Relay truth table (hardware, Fake agent initiated) | Reset, permit, safe, anti-restart command sequence | Passed 5 of 5 checks | Pass |
| G4b | Pressure guardrail (4.2 bar) | Crossing removes output and latches safe | Peak 4.83 bar; trip latched; software transition 0.608 ms | Pass |
| G4c | Flow guardrail (15 L/min) | Crossing removes output and latches safe | Peak 15.41 L/min; trip latched; software transition 0.801 ms | Pass |
| G4d | Dual-input guardrail | Pressure and flow independently trip the same output | Peaks 4.34 bar and 15.21 L/min; 9 of 9 checks passed | Pass |
| G4e | E-stop anti-restart | E-stop forces safe; release does not restart; permit before reset rejected | All observed as expected; software transition 0.867 ms | Pass |
| G5 | Restoration and clean exit | Phase 3 dashboard restored, actuation disabled, Pi halted | Sidecar stopped; Phase 3 back on port 8080 observe-only; `test_phase3_untouched` passed; actuation held disabled; Pi halted | Pass |
| S1 | Full software suite (this environment) | All non-hardware tests pass | 213/213 passed (unit, contract, agent, property, scenario) | Pass |

Aggregate hardware result: after the one retained observation failure, **six hardware runs passed, recording 3,422 samples and passing 34 of 34 evaluated checks**. All seven exported evidence archives and every file in their export manifests re-hashed successfully during the evidence review.

An honesty note on the millisecond figures: the sub-millisecond transitions are kernel-observed changes to the *commanded* GPIO state. They are **not** measurements of relay contact motion or electrical load removal — the current bench has no contact-feedback or current sensor (see Section 6).

### 3.3 Validation Summary

The evidence supports a narrow, defensible claim: CertaRig is a working evidence-first commissioning and test-operations runner for an already-mapped low-voltage rig. Specifically:

- The safety architecture behaved deterministically: every consequential hardware run contains the kernel events explaining why output was permitted or removed.
- Unsafe recovery was blocked in every case: pressure, flow, and E-stop runs all recorded a reset-required state and rejected a permit before reset.
- The two analog paths trip independently onto the same output.
- The agent remained outside the numeric safety boundary throughout: transcripts show the Fake agent reading a skill, starting a named procedure, waiting, and reporting the kernel's returned outcome — never comparing a measurement.
- Evidence integrity is inspectable: archive and file hashes verify.
- The failed first observation run is part of the validation, not a blemish: it demonstrates that a procedure refuses to pass when the operator action or signal quality is inadequate.

What is **not** validated: live LLM operation on hardware, discovery of an unmapped bench, write paths to industrial fieldbuses, and electrical (as opposed to software-commanded) trip latency.

---

## 4. Performance and Reliability Analysis

**Responsiveness.** Kernel-commanded safety transitions on the bench measured 0.608 ms (pressure trip), 0.801 ms (flow trip), and 0.867 ms (E-stop) from the kernel observing the condition to the commanded GPIO state changing — comfortably below any human-perceptible delay, with the caveat above that mechanical relay response is not yet instrumented. The Studio Live view streams both channels with trip lines in near real time; the observe run sampled at roughly 10 samples per second (1,291 samples over 129.0 s).

**Stability.** A Hypothesis property-based state machine generates arbitrary command orderings and sensor faults while continuously checking the output invariant and anti-restart rule. All 213 software tests in the stated suites passed in this environment; `make check` sets a 90% coverage threshold, and `make soak` runs one accelerated simulated hour. On hardware, six procedures completed without a kernel fault. The dual-input run also demonstrated trip → reset → permit → a second independent trip within one run.

**Resource usage.** The full stack (kernel, Edge API, Studio, evidence writer) ran as a user-local sidecar on a Raspberry Pi 3 Model A+ — a constrained single-board computer — alongside the frozen Phase 3 tree, while sampling two ADC channels and serving the browser console. No resource exhaustion was observed during the lab. The simulator path runs on any machine with Python 3.11+ (a stranger can go from clone to a running simulated rig in under ten minutes, or use Docker Compose).

**Bottlenecks and reliability risks.** The known constraints are: (a) exclusive hardware ownership — only one kernel may own GPIO23 and the ADS1115 at a time, which is by design but means no redundant observer; (b) the systemd `WatchdogSec=30` is a supervisor heartbeat, not a safety-integrity-level loop, so CertaRig must not be represented as a certified safety system; (c) evidence export currently omits the raw CSV payloads, limiting post-hoc waveform analysis from a pulled bundle; (d) relay state is command-derived, so a welded relay contact would not be detected by the current sensing set.

---

## 5. Risk Analysis and Mitigation Review

### 5.1 Identified Risks (Revisited)

| Risk (from earlier phases) | Phase 3 status |
| --- | --- |
| A language model makes or influences a safety decision | Architecturally excluded: the agent has no tool that compares measurements or drives the output; `bypass_interlock` / `override_limits` do not exist as callable tools; verified by transcripts and contract tests |
| Untested procedure reaches hardware | Mitigated by the twin gate: hardware start refused unless the exact procedure hash passed in simulation within 24 hours; enforced on all six 12 Sep runs |
| Output restarts after a trip or E-stop without human review | Mitigated by latching + anti-restart: permit-before-reset was rejected on the bench in the pressure, flow, and E-stop runs |
| Damaging the frozen Phase 3 course submission | Mitigated by the sidecar pattern (separate folder, port 8081, user-local env), install-script guards that refuse the Phase 3 host, and `test_phase3_untouched` — verified at Gate 0 and Gate 5 |
| Bad sensor data treated as good | Mitigated by sensor-quality checks: invalid quality clears the permit and latches safe; demonstrated by the failed first observation run |
| Evidence tampering or ambiguity | Mitigated by SHA-256 checksums on every artefact and export manifest; all seven archives re-verified. Residual gap: raw CSVs not yet inside the bundle |
| LLM provider outage or lock-in | Mitigated by provider neutrality: deterministic Fake default (no key), Anthropic first choice, OpenAI/compatible fallback, replay provider; CI never depends on a live model |
| Credential leakage | Mitigated by policy: keys live only in `.env` / `/etc/certarig/` / `~/.ssh`; operator keys ≥ 12 characters and distinct from the agent key; no secrets in `config/` |

### 5.2 Mitigation Effectiveness

The mitigations that were tested worked, and — importantly — they were tested by attempting the unsafe thing. The permit-without-reset rejection was exercised on hardware three separate times. The twin gate was not bypassed for convenience even under lab time pressure. The Gate 2 failure shows the quality mitigation firing in practice rather than existing only on paper. Two mitigations remain declared-but-untested at their edges: the live-LLM tool-discipline constraints have only been exercised through the Fake provider and unit tests (a live adapter has never driven the bench workflow), and the evidence-integrity story is weakened by the missing raw CSVs until the exporter fix and hash-verification contract test land.

---

## 6. Limitations and Constraints

Stated plainly, because clarity here is worth more than optimism:

1. **Exported evidence bundles are incomplete.** Each hardware `run.json` records its raw CSV recording by filename, row count, and SHA-256 hash, but the pulled zip bundles do not contain the CSV itself. Metadata, events, checks, and outcomes are intact and the archive hashes match the lab record, but raw physical waveforms cannot be re-plotted from a pulled bundle. The stated next requirement is to include the recording in the export and add a contract test that opens an archive and verifies the CSV hash against `run.json`.
2. **No live language model has driven the proven path.** The 12 September hardware procedures used the deterministic Fake provider. Claude Sonnet 4.5 and OpenAI GPT-4.1-mini adapters exist and are unit-tested, but live-key operation is unvalidated. No claim is made — anywhere in this project — that an LLM tripped the relay.
3. **Software-commanded, not electrical, latency.** The sub-millisecond transition times are commanded-GPIO-state changes. Without an auxiliary contact, optocoupled feedback, or current sensor, end-to-end trip latency (and welded-contact detection) cannot be claimed.
4. **The bench is mapped, not discovered.** The commissioning interview is designed but not built; Onboard today is a configuration form with a bench briefing, not discovery. The proof covers one known Raspberry Pi dry bench.
5. **Fieldbus support is observe-only.** MQTT and Modbus TCP are real observe-mode adapters; OPC UA, Siemens S7, EtherNet/IP, and CAN are examples/directions. No write path to any industrial bus is implemented.
6. **Not a certified safety system.** The watchdog is a supervisor heartbeat, not a SIL loop; the bench is low-voltage; nothing here substitutes for certified safety instrumentation on a dangerous plant.
7. **Simulated and hardware traces are never interchangeable.** Simulator results are labelled as simulation, hardware results as Raspberry Pi, and this document maintains that separation throughout.

---

## 7. Future Enhancements and Scope Extension

### 7.1 End Customer, Industry Opportunity, and Enabling Advances

The end customer is not a general chatbot user. It is the owner or commissioner of a test bench: a lab engineer defining a qualification, a technician repeating it, or a team that needs an auditable record to survive a shift change. Phase 3's immediate customer context is a university dry bench. The capstone target is a customer with an already-understood rig who wants safer guided operation and consistent evidence.

Relevant applications include hydraulic test carts, battery and vehicle benches on CAN, factory cells using Siemens or Allen-Bradley controllers, and Modbus skids. Electrification, connected industrial equipment, and increasingly software-defined products are the proposed growth drivers because they create more sensors, configurations, and repeatable verification work. Three technical advances make CertaRig timely: capable low-cost edge computers can run the kernel beside a rig; standard protocols such as MQTT, Modbus, OPC UA, and CAN expose structured signals; and tool-using language-model APIs can translate operator intent without being given output authority. Digital twins and inexpensive cryptographic hashing add rehearsal and auditable evidence. CertaRig combines those advances while keeping the safety decision deterministic. This is a product hypothesis, not a quantified market claim; capstone customer interviews must test it.

### 7.2 Summary of Capstone Missions

The capstone product is a **deployable agentic test-operations layer for someone else's mapped rig**. Its planned missions, in dependency order, are:

1. **Commissioning interview (the capstone product core).** The agent interviews the owner of a new rig — what modules exist, which bus (GPIO/ADC, MQTT, Modbus, OPC UA, S7, EtherNet/IP, CAN), which pin/register/tag maps to which concept, what trip numbers and units apply, what must remain observe-only — and proposes a `rig.json`. A human reviews and applies it; the twin rehearses the exact procedure; only then can an output be armed. The governing invariant: a new rig can be described in language and proposed as configuration, but no unreviewed mapping can ever reach an output.
2. **Second simulated plant.** Prove the interview against a different physics (for example a thermal plant, building on the existing `thermal_soak` skill and `rig.thermal.sim.json`) before any new physical output is energized.
3. **Evidence completeness.** Ship the exporter fix so bundles contain raw recordings, with the hash-verification contract test.
4. **Relay feedback / current sensing.** Add an isolated auxiliary contact or current sensor so electrical trip response can be measured, upgrading the latency claim from commanded to observed.
5. **Live-provider qualification.** Run `claude-sonnet-4-5` and `gpt-4.1-mini` through the Section 2.3 benchmark: approved-skill routing, capability-manifest discipline, no numeric safety decisions, correct approval stops, and replayable results. A live model remains optional and outside the kernel.
6. **Broader industry reach.** Extend observe-mode adapters toward factory OPC UA cells, battery and vehicle benches on CAN, and Modbus skids. Every new integration starts observe-only and uses a human-applied map.

### 7.3 Readiness to Move to the Capstone

CertaRig is ready for the capstone as a platform foundation, not as a finished industrial product. The kernel, Edge API, simulator gate, approvals, Studio workflow, and hardware procedure path exist and have evidence. The next work is therefore a bounded extension—commissioning a second mapped rig safely—rather than a redesign of the safety architecture. Readiness is conditional on preserving three rules: no unreviewed map reaches an output, simulated evidence is never presented as hardware, and no live model is admitted until it passes the use-case benchmark. Industrial sale or safety certification would require additional work beyond the capstone, including electrical output feedback, completed evidence export, broader hardware validation, and appropriate certified safeguards.

---

## 8. Learning Outcomes and Reflections

- **Splitting interpretation from authority is the design, not a feature.** The most transferable lesson is architectural: the useful question was never whether the model is clever, but who may say yes. Making the kernel the only answer simplified every downstream decision, from tool design to evidence.
- **Failures are evidence.** Retaining the failed Gate 2 sweep, rather than re-running until clean, made the validation more credible, and demonstrated that procedures can refuse to pass.
- **Honesty about the AI stack matters.** The build-time coding assistant does not operate the product. At runtime, Fake is the proven deterministic path; Claude is the intended first live choice and OpenAI the fallback, but both remain unproven live. Keeping those roles separate prevented over-claiming and led to a benchmark based on skill routing and tool discipline rather than chat quality.
- **Commissioning discipline is a product feature.** The six-gate ladder (read-only, sidecar, observe, twin, actuate, restore) began as lab hygiene and turned out to be the product's user journey.
- **Restoration is part of success.** Leaving the frozen Phase 3 system exactly as found, verified by a test, taught that a credible result includes the exit, not just the demonstration.
- **Practical engineering breadth.** The project exercised embedded hardware (ADC, GPIO, E-stop wiring), safety-state-machine design, property-based testing, HTTP API and schema contracts, browser front-end work, deployment (systemd, Docker), and evidence/audit design in one system.

---

## 9. Final Deliverables

| Deliverable | Location / Status |
| --- | --- |
| Source repository | The `certarig-platform` repository (this tree): kernel, Edge API, twin, agent, Studio, skills, tests, deployment scripts |
| Frozen Phase 3 proof of concept | `certarig-phase-2-poc` at commit `23988a3`, frozen on the Pi as the submission evidence source (`docs/PROVENANCE.md`) |
| Deployed system | Frozen Phase 3 live dashboard on the bench Pi (port 8080, observe-only); platform reproducible via `make install && make check` + simulator, or Docker Compose |
| Documentation | `README.md`; `docs/platform-lab/` (product state, dry-bench lab record, commissioning-interview design); `docs/explainer/` (gates 0–5 evidence analysis); this Phase 3 document |
| Evidence | Seven checksummed hardware bundles from 12 Sep 2026 (hashes in `docs/platform-lab/2026-09-12-dry-bench.md`); derived summary data in `docs/explainer/data/`; Phase 2 bench evidence in `pi_retrieval_2026-09-12/phase3_evidence/` |
| Evidence & product-direction report | `deliverables/CertaRig_Gates_0_to_5_Evidence_and_Product_Direction.pdf` (+ editable DOCX) |
| Presentation / demo material | **Phase 3 submission film v4** (13.4 min, paper explainer motion + designed Studio/bench split; atelier lookbook retired): [CertaRig_Phase3_Film.mp4](https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Film.mp4). **Uncut clap-synced bench run** (29.6 min, 1310+608 split, no overlay PiP): [CertaRig_Phase3_Uncut_Bench_Run.mp4](https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Bench_Run.mp4). **Action windows** (no VO): [CertaRig_Phase3_Uncut_Action.mp4](https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Action.mp4). Release page: https://github.com/shadybrook/certarig-platform/releases/tag/phase3-submission-videos-v4. Cut list: `tools/phase3_edit/edl/phase3_film_v4.json`. Motion: `python3 tools/render_phase3_explainer.py`. Source footage folder: https://drive.google.com/drive/folders/1mlegZnq_AQurnBIKY-Ckh1S6TyZ_Q8Bk |

---

## 10. Conclusion

Phase 3 demonstrates implementation readiness within a defined boundary. The core architecture—an agent that interprets while a deterministic kernel measures, compares, latches, and owns the output—was validated through a six-gate hardware progression. In this environment, 213 software tests passed. On 12 September, six exact procedure hashes passed the twin gate before six hardware runs recorded 3,422 samples and passed 34 of 34 checks. The 4.2 bar and 15 L/min guardrails latched safe, E-stop anti-restart held, and the frozen course system was restored and verified.

The result does not prove live-LLM operation, unknown-rig discovery, fieldbus actuation, or mechanical relay latency. It also leaves raw CSV export incomplete. Those limits define the capstone rather than weaken the Phase 3 result: build the commissioning interview, prove a second plant, complete evidence export, add electrical feedback, and qualify live providers. The project is ready to proceed on that bounded mission while retaining the invariant that no unreviewed mapping can reach an output.

The AI can ask. Only the kernel can say yes.

---

## 11. Supervisor Review and Approval

**Supervisor Feedback:**

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________

**Comments:**

_________________________________________________________________

_________________________________________________________________

**Recommendations:**

_________________________________________________________________

_________________________________________________________________

**Supervisor Signature:** ______________________________

**Date:** ______________________________
