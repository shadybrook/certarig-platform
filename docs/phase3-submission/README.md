# Phase 3 submission — where everything lives

Start here. This repository is the **platform** (`certarig-platform`). The frozen course PoC remains https://github.com/shadybrook/certarig-phase-2-poc (commit `23988a3` imported here; later PoC evidence through 12 Sep is retained below).

Two hardware worlds must not be mixed:

| | Frozen Phase 3 (World A) | Platform sidecar lab (World B) |
| --- | --- | --- |
| When | 9–12 Sep 2026 on the Pi live-dashboard | 12 Sep (and 13 Sep follow-on) on port **8081** |
| Code | `certarig-phase-2-poc` | this repo |
| Raw CSV / photos / plots | [`pi_retrieval_2026-09-12/phase3_evidence/`](../../pi_retrieval_2026-09-12/phase3_evidence/) | Checksummed zips in [`archive/phase3-submission/sidecar-lab-2026-09-12/`](../../archive/phase3-submission/sidecar-lab-2026-09-12/) — those zips **do not contain** the raw CSV (known exporter gap) |
| Circuit / BOM / SOPs | [`docs/phase3/`](../phase3/README.md) | same bench; see as-built diagram |

## 1. Open these first

| What | Path |
| --- | --- |
| Phase 3 Word report | [`deliverables/phase3-document/CertaRig_Phase3_Document.docx`](../../deliverables/phase3-document/CertaRig_Phase3_Document.docx) · [download](https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Document.docx) |
| As-built circuit | [`docs/phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png`](../phase3/diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png) |
| Bill of materials | [`docs/phase3/CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.md`](../phase3/CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.md) |
| Six-gate analysis | [`docs/explainer/2026-09-13-gates-0-to-5-analysis.md`](../explainer/2026-09-13-gates-0-to-5-analysis.md) |
| 12 Sep sidecar lab write-up | [`docs/platform-lab/2026-09-12-dry-bench.md`](../platform-lab/2026-09-12-dry-bench.md) |
| Edited film | https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Film.mp4 |
| Uncut Studio + bench split | https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Bench_Run.mp4 |

## 2. Raw recordings, graphs, logs (frozen PoC)

Pulled from the Pi into [`pi_retrieval_2026-09-12/`](../../pi_retrieval_2026-09-12/README.md). Same tree as `phase3_evidence/` on the PoC repo.

| Date | Folder | What is in it |
| --- | --- | --- |
| 9 Sep | `phase3_evidence/2026-09-09_ads1115_commissioning/` | I²C bring-up notes, wiring photo |
| 9 Sep | `phase3_evidence/2026-09-09_p1_potentiometer/` | P1 as-built photo |
| 9 Sep | `phase3_evidence/2026-09-09_p1_sweep/` | **CSV** + time plot of A0 sweep |
| 10 Sep | `phase3_evidence/2026-09-10_dual_pot_sweep/` | **CSV** (raw + 0–100 s trim) + dual plot |
| 10 Sep | `phase3_evidence/2026-09-10_estop/` | **CSV** + GPIO24 timeline plot + NC1 photo |
| 11 Sep | `phase3_evidence/2026-09-11_integrated_bench/` | Gate 1/2 **CSVs**, meter register, pre-power photos |
| 12 Sep | `phase3_evidence/2026-09-12_integrated_bench/` | Transistor permit/safe **CSVs**, truth table |
| 12 Sep | `phase3_evidence/2026-09-12_sensor_guardrail_shadow/` | Observe-only 7,591-sample **CSV** + plot (GPIO23 not armed) |
| 12 Sep | `phase3_evidence/live_runs/` | Two live `bench-run.csv` recordings |

## 3. Checksummed procedure bundles (platform sidecar)

Copied from gitignored `evidence/lab-pulled/` so they stay on GitHub. Bundle SHA-256s: [`archive/phase3-submission/SHA256SUMS-bundles.txt`](../../archive/phase3-submission/SHA256SUMS-bundles.txt).

| Lab | Folder | Contents |
| --- | --- | --- |
| 12 Sep Gate 2–4 | [`archive/phase3-submission/sidecar-lab-2026-09-12/`](../../archive/phase3-submission/sidecar-lab-2026-09-12/) | Zip + extracted `run.json`, `events.jsonl`, `report.md`, `SHA256SUMS.txt` for ADC (fail then pass), relay, pressure, flow, dual-pot, E-stop |
| 13 Sep agent loop | [`archive/phase3-submission/sidecar-lab-2026-09-13/`](../../archive/phase3-submission/sidecar-lab-2026-09-13/) | Pressure, flow, 5.0 bar, session, pre-shutdown zips |
| Twin-gate stamps | [`archive/phase3-submission/twin-gate-sim-library/`](../../archive/phase3-submission/twin-gate-sim-library/) | **Simulator** CSVs used as 24-hour stamps — not hardware traces |
| Fake agent logs | [`archive/phase3-submission/agent-transcripts/`](../../archive/phase3-submission/agent-transcripts/) | JSONL transcripts (Fake provider) |

Honesty: those sidecar zips record the CSV **hash** in `run.json` but do not include the CSV file. The physical waveforms you can plot are the PoC logger CSVs in section 2 and the shadow-run CSV.

## 4. Derived graphs (from the 12 Sep sidecar numbers)

[`docs/explainer/assets/`](../explainer/assets/) and [`docs/explainer/data/hardware_run_summary.csv`](../explainer/data/hardware_run_summary.csv):

- `01_gate_ladder.png` — Gates 0–5
- `02_hardware_peaks.png` — pressure / flow peaks vs 4.2 bar and 15 L/min
- `03_software_response_time.png` — commanded-GPIO times (not relay motion)
- `04_run_coverage.png`
- `05_kernel_event_timeline.png`
- `06_twin_traces.png` — labelled simulation
- `07_product_architecture.png`

## 5. Phase 2 PoC cases (synthetic, retained)

[`archive/phase3-submission/phase2-synthetic-cases/`](../../archive/phase3-submission/phase2-synthetic-cases/) — four JSON evidence bundles from the browser PoC. Architecture notes: [`docs/phase2/DIAGRAMS.md`](../phase2/DIAGRAMS.md).

Frozen source repo: https://github.com/shadybrook/certarig-phase-2-poc

## 6. What is deliberately not in git

- Live `evidence/lab-pulled/`, `evidence/runs/`, `evidence/sim-library/` (working dirs; snapshots are under `archive/phase3-submission/`)
- `.env`, operator/agent keys, SSH private keys, Wi-Fi screenshots
- Submission films (GitHub **release** `phase3-submission-videos-v4`, not the git tree)
