"""Common measurement contract. A zero value is data; quality is separate."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any, Protocol


class ObservationSource(Protocol):
    def read(self) -> list[dict[str, Any]]: ...
    def status(self) -> dict[str, Any]: ...
    def close(self) -> None: ...


def checked_sample(
    raw: dict[str, Any], *, expected_unit: str, max_age_s: float = 1, now: datetime | None = None
) -> dict[str, Any]:
    value = raw.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("A finite numeric measurement is required")
    if not isinstance(raw.get("channel_id"), str) or not 0 < len(raw["channel_id"]) <= 128:
        raise ValueError("Missing channel identity")
    if not isinstance(expected_unit, str) or not expected_unit or raw.get("unit") != expected_unit:
        raise ValueError("Incompatible or missing units")
    timestamp = datetime.fromisoformat(raw["captured_at"])
    if timestamp.tzinfo is None:
        raise ValueError("Timezone-aware source timestamp required")
    age = ((now or datetime.now(UTC)) - timestamp).total_seconds()
    if age < -0.1:
        raise ValueError("Source timestamp is in the future")
    quality = raw.get("quality", "good")
    if quality not in {"good", "missing", "stale", "malformed", "disconnected", "out_of_range", "invalid"}:
        raise ValueError("Unknown source quality")
    if age > max_age_s and quality == "good":
        quality = "stale"
    return {
        "channel_id": raw["channel_id"],
        "value": float(value),
        "unit": expected_unit,
        "captured_at": timestamp.isoformat(),
        "quality": quality,
        "raw_value": raw.get("raw_value", value),
        "timestamp_origin": raw.get("timestamp_origin", "source"),
    }
