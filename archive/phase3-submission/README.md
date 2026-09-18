# Archived Phase 3 / lab evidence

Snapshots that used to live only on this Mac (gitignored `evidence/lab-pulled/`) or only on https://github.com/shadybrook/certarig-phase-2-poc.

Visitor map: [`docs/phase3-submission/README.md`](../../docs/phase3-submission/README.md).

| Folder | Origin | Hardware? |
| --- | --- | --- |
| `sidecar-lab-2026-09-12/` | Platform sidecar port 8081, 12 Sep 2026 | Raspberry Pi (metadata + events; raw CSV not inside the zip) |
| `sidecar-lab-2026-09-13/` | Same sidecar, 13 Sep agent loop | Raspberry Pi, same exporter gap |
| `twin-gate-sim-library/` | `certarig sim stamp-gate` | **No** — simulator only |
| `phase2-synthetic-cases/` | PoC `evidence/phase2/` | **No** — browser synthetic cases |
| `agent-transcripts/` | Fake provider sessions 12–13 Sep | Tool log, not a sensor recording |
| `SHA256SUMS-bundles.txt` | SHA-256 of every archived zip | Matches `docs/platform-lab/2026-09-12-dry-bench.md` for the 12 Sep set |

Do not add new live runs here. Pull those into the gitignored `evidence/lab-pulled/` working directory.
