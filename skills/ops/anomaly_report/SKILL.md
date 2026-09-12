---
name: anomaly_report
domain: ops
procedure: procedure.yaml
intents:
  - explain the last trip
  - draft an anomaly report
  - what just happened
---

# Anomaly report

Use this after a trip or abort. The procedure itself only proves the bench is still safe
and records a mark. The explanation comes from deterministic artefacts:

1. The latest file in the node's `flight/` directory (ring buffer dumped on `*_forced_safe`).
2. The last procedure run's `events.jsonl` and `report.md`.
3. The kernel events on `/v1/live/state`.

Write a short narrative that quotes those events. Label it as narrative, not measurement.
Do not request permit. Do not reset the trip unless the operator asks.
