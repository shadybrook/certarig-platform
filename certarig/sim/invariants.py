"""Named safety invariants checked over a CSV recording and a kernel event list.

These are the properties the platform promises. They are used by scenario expectations,
the property tests and the digital-twin gate before any hardware deployment.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any

TRIP_EVENT_SUFFIX = "_forced_safe"


def read_rows(csv_path: str | Path) -> list[dict[str, str]]:
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _truthy(value: str | None) -> bool:
    return str(value).lower() == "true"


def output_off_when_estop(rows: Iterable[dict[str, str]]) -> list[str]:
    return [
        f"row {row['sample_index']}: output high while E-stop active"
        for row in rows
        if _truthy(row.get("gpio23_command_high")) and _truthy(row.get("estop_active"))
    ]


def _channel_state_keys(row: dict[str, str]) -> list[str]:
    return [key for key in row if key.endswith("_state")]


def output_off_when_process_unsafe(rows: Iterable[dict[str, str]]) -> list[str]:
    problems: list[str] = []
    for row in rows:
        if not _truthy(row.get("gpio23_command_high") or row.get("output_high")):
            continue
        bad_states = [
            f"{key}={row[key]}"
            for key in _channel_state_keys(row)
            if row.get(key, "safe") not in {"safe", "", "None"}
        ]
        if bad_states:
            problems.append(f"row {row['sample_index']}: output high with {', '.join(bad_states)}")
        if not _truthy(row.get("process_healthy")):
            problems.append(f"row {row['sample_index']}: output high while process unhealthy")
    return problems


def no_restart_without_reset(events: Iterable[str]) -> list[str]:
    """After any forced-safe event, ``permit_accepted`` needs ``trip_reset_output_safe`` first."""
    problems: list[str] = []
    needs_reset = False
    for index, event in enumerate(events):
        if event.endswith(TRIP_EVENT_SUFFIX) or event == "operator_safe":
            needs_reset = True
        elif event == "trip_reset_output_safe":
            needs_reset = False
        elif event == "permit_accepted" and needs_reset:
            problems.append(f"event {index}: permit_accepted without a reset after a trip")
    return problems


def csv_rows_contiguous(rows: list[dict[str, str]]) -> list[str]:
    problems: list[str] = []
    last_index: int | None = None
    last_elapsed = -1.0
    for row in rows:
        if row.get("record_kind") != "sample":
            continue
        index = int(row["sample_index"])
        elapsed = float(row["elapsed_s"])
        if last_index is not None and index != last_index + 1:
            problems.append(f"sample_index jumped from {last_index} to {index}")
        if elapsed < last_elapsed:
            problems.append(f"elapsed_s went backwards at sample {index}")
        last_index, last_elapsed = index, elapsed
    return problems


def ends_safe(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ["no rows"]
    last = rows[-1]
    return [] if not _truthy(last.get("gpio23_command_high")) else ["last row has output high"]


CHECKS = {
    "output_off_when_estop": lambda rows, events: output_off_when_estop(rows),
    "output_off_when_process_unsafe": lambda rows, events: output_off_when_process_unsafe(rows),
    "no_restart_without_reset": lambda rows, events: no_restart_without_reset(events),
    "csv_rows_contiguous": lambda rows, events: csv_rows_contiguous(rows),
    "ends_safe": lambda rows, events: ends_safe(rows),
}


def check_all(
    rows: list[dict[str, str]], events: list[str], names: Iterable[str] | None = None
) -> dict[str, Any]:
    selected = list(names) if names is not None else list(CHECKS)
    report: dict[str, Any] = {}
    for name in selected:
        problems = CHECKS[name](rows, events)
        report[name] = {"passed": not problems, "problems": problems[:20], "problem_count": len(problems)}
    return report


def events_from_rows(rows: Iterable[dict[str, str]]) -> list[str]:
    return [row["event"] for row in rows if row.get("event")]
