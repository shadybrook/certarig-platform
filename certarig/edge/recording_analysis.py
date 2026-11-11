"""Reproducible descriptive results from recorded samples, without model inference."""

from __future__ import annotations

import csv
import io
import math
from typing import Any


def analyze_csv(data: bytes, config: dict[str, Any]) -> dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    channels: dict[str, Any] = {}
    for channel in config["channels"]:
        cid = channel["channel_id"]
        values = []
        for row in rows:
            raw = row.get(f"{cid}_value")
            if raw not in {None, "", "None"}:
                value = float(str(raw))
                if not math.isfinite(value):
                    raise ValueError(f"non-finite recording value: {cid}")
                values.append(value)
        channels[cid] = {
            "unit": channel["unit"], "observations": len(values),
            "minimum": min(values) if values else None, "maximum": max(values) if values else None,
        }
    unsafe = sum(
        row.get("output_high") == "true" and (
            row.get("estop_active") == "true" or row.get("trip_latched") == "true"
            or row.get("process_healthy") != "true"
        ) for row in rows
    )
    feedback = [r for r in rows if r.get("output_feedback") in {"true", "false"}]
    return {
        "kind": "raw_sample_summary", "rows": len(rows),
        "sample_rows": sum(r.get("record_kind") == "sample" for r in rows),
        "command_rows": sum(r.get("record_kind") == "command" for r in rows),
        "unsafe_command_rows": unsafe, "channels": channels,
        "output_state_source": "electrical_feedback_and_command" if feedback else "command_derived_not_electrical_feedback",
        "feedback_observations": len(feedback),
        "feedback_transition_intervals_s": [
            {"from": float(a["elapsed_s"]), "to": float(b["elapsed_s"]), "state": b["output_feedback"]}
            for a, b in zip(feedback, feedback[1:], strict=False) if a["output_feedback"] != b["output_feedback"]
        ],
    }


def reproduce_checks(data: bytes, config: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Reproduce supported checks from CSV and the recorded procedure event stream.

    Event completion is not independent proof of physical motion; latency checks
    cannot be reconstructed beyond the recorder's sampling resolution.
    """
    summary = analyze_csv(data, config)
    concepts = {c.get("concept", c["channel_id"]): c["channel_id"] for c in reversed(config["channels"])}
    events = run.get("events", [])
    kernel = {e["event"] for e in run.get("kernel_events", [])}
    result = []
    for row in run.get("checks", []):
        check = row["check"]
        passed = None
        source = "not_independently_reproduced"
        if "peak_below" in check:
            cid = concepts.get(check["signal"], check["signal"])
            peak = summary["channels"].get(cid, {}).get("maximum")
            passed = peak is not None and peak < check["peak_below"]
            source = "raw_recording"
        elif "step_passed" in check:
            passed = any(e.get("kind") == "step_passed" and e.get("step") == check["step_passed"] for e in events)
            source = "recorded_step_events"
        elif "event_observed" in check:
            passed, source = check["event_observed"] in kernel, "recorded_kernel_events"
        elif "event_not_observed" in check:
            passed, source = check["event_not_observed"] not in kernel, "recorded_kernel_events"
        result.append({"check": check, "reproduced_passed": passed, "reported_passed": row["passed"], "source": source})
    return {"checks": result, "consistent": all(r["reproduced_passed"] is None or r["reproduced_passed"] == r["reported_passed"] for r in result), "limitation": "Sampled electrical intervals and recorded software events do not measure mechanical valve or contact motion"}
