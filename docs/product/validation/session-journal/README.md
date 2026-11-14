# Session Journal implementation and qualification record

Date: 15 November 2026, Asia/Calcutta. Branch: `product/session-journal-2026-11-14`. Base: `13bd409a1ec045df986b1fc1aa8e129562a3ddee`. This is a locally tested software release candidate; M5 and final capstone acceptance remain open.

## Recorded checks

| Check | Result | Evidence |
|---|---|---|
| Lint | Passed | `make lint`; current regression log |
| Typing | Passed across 120 source files | `make typecheck` |
| Coverage gate | Passed at 90.63% | `make coverage`; threshold unchanged at 90% |
| New description and advanced-lineage tests | 311 passed | `bench-spec-tests.xml`; no model/provider/physical calls |
| Platform browser | 11 passed | New Journal lifecycle, unsafe-text handling, missing/analysis-only descriptions and conflict recovery; classic lifecycle/profile/authoring parity |
| Legacy Edge browser | 10 passed | Approval/run/export, onboarding, interviews and unavailable Sandbox refusal |
| Simulated-hour soak | Passed | `make soak`; not a physical 60-minute acquisition |
| Design prototype interactions | Passed | `node studio/check-prototype.mjs`; four viewport widths, 200% reflow equivalent, navigation, recovery, cancellation, review, revoke and keyboard/dialog checks; zero platform requests |
| Independent visual review | 8/10, no blocking defect | `/root/journal_visual_review`; action hierarchy, reading measure and mobile repetition subsequently refined |
| Independent UX walkthrough | Fixture lifecycle completed | `/root/journal_ux_review`; complete exact definition and readiness/source explanations subsequently added |
| Wheel build and clean import/resource check | Recorded in summary | Studio remains served from a source checkout; not a standalone wheel-hosted UI qualification |

Full regression includes contract, property and scenario coverage. The extra soak covers the selected slow scenario. Passing fixtures establish the tested software behavior; they do not qualify genuine accounts, live providers, physical devices or container isolation.

## Open gates

| Gate | Current status | Required evidence |
|---|---|---|
| Genuine Dex login | Unverified | Two attended provisioned users, organization/role isolation and revocation |
| Live Codex connection and comparison | Unverified | Managed sign-in, actual candidate traces, consent and evaluated exact version; no API-key fallback or paid calls were used |
| Sandbox image | Not built | Resource preflight, dedicated profile, pinned build and exact source/image/policy binding |
| Seven real-container cases | Unrun | Fixed qualification suite without failures/skips; no host fallback |
| Local MQTT broker | Unrun in this checkpoint | A genuine selected loopback broker; no Mosquitto executable found in the checked installation paths |
| Real serial/Modbus equipment | Unverified | Operator-enrolled hardware and relevant fault/device evidence; existing loopback/fixture tests are narrower |
| Native mobile keyboard | Unverified | Actual device/emulator with keyboard open; viewport checks alone are insufficient |
| Physical missions | No new evidence | Measured/calibrated/protected trials or a genuine approved scope amendment |
| Final university submission | Unconfirmed | Deadline, metadata, actual demo link, genuine supervisor remarks and attended rehearsal |

Initial resource probe met disk/memory prerequisites; later Sandbox preflight reported elevated memory pressure and a missing pinned image. No existing workload was stopped, Docker context switched globally or isolation limit weakened. Exact free-byte/pressure observations appear in `sandbox-preflight.json`. This remains an execution blocker, not a passed test.

## Reproduce

Use the source checkout and its documented dependencies. Run `make lint typecheck coverage`, `make soak`, `cd studio && npx playwright test --config platform.playwright.config.mjs`, and the legacy `playwright.config.mjs`. Browser fixtures are explicit test-only dependencies. For the isolated prototype, serve `studio/` on loopback port 18121 and run `node studio/check-prototype.mjs`.

For genuine runtime work, run `python -m certarig sandbox preflight` first, then only when ready use the documented `prepare` and fixed `qualify` path. Requalify after relevant source/image changes. Keep failed/unrun results in the ledger. Missing or modified evidence must fail its offline verifier.

## Milestone disposition

M0–M4 software is implemented with the supported scope documented in `docs/product/SESSION_JOURNAL.md`. M1's native keyboard check remains open. M5 has passed local software checks but has the genuine qualification gates above. M6 includes report/deck/supervisor drafts and reproduction material; final acceptance, recording and rehearsal require real evidence and student/institution participation.
