# Platform lab pack (optional, not Phase 3)

This folder is a **template** for a for-grade write-up of the *platform* dry-bench lab. It is not the 20 Sep Phase 3 submission. Do not copy Phase 3 evidence here. Do not invent HIL results.

The 12 Sep 2026 sidecar lab is written up in [2026-09-12-dry-bench.md](2026-09-12-dry-bench.md). Working copies stay gitignored under `evidence/lab-pulled/`. The GitHub snapshot is [archive/phase3-submission/sidecar-lab-2026-09-12/](../../archive/phase3-submission/sidecar-lab-2026-09-12/). Map: [docs/phase3-submission/README.md](../phase3-submission/README.md).

## What to attach

| Item | Where it comes from |
| --- | --- |
| Bench briefing | `briefing.json` in each run folder and at the evidence root |
| Per-run `report.md` | Deterministic step table, kernel events, briefing copy |
| CSV + SHA256 | Flight recorder / whole-run recording |
| Ledger | `evidence/ledger/outcomes.jsonl` |
| Twin-gate stamps | `evidence/twin_gate/*.json` (simulator passes, 24 h) |

## Suggested index

1. What the operator did with P1, P2, E-stop, and the relay (from the briefing, not from memory).
2. Observe-only results (`adc_validation`, Fake `read_state` / `force_safe`).
3. Actuated results in order: `relay_truth_table`, `pressure_guardrail`, `flow_guardrail`, `dual_pot_guardrail`, `estop_anti_restart`.
4. How a stranger repeats this: declare a `rig.json`, stamp the twin on `certarig sim stamp-gate`, serve the sidecar on a free port, never overwrite a frozen demo.

## Ease of use notes

Write these after the lab, from what actually happened. Empty sections stay empty until then.
