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
    return {
        "kind": "raw_sample_summary", "rows": len(rows),
        "sample_rows": sum(r.get("record_kind") == "sample" for r in rows),
        "command_rows": sum(r.get("record_kind") == "command" for r in rows),
        "unsafe_command_rows": unsafe, "channels": channels,
        "output_state_source": "command_derived_not_electrical_feedback",
    }
