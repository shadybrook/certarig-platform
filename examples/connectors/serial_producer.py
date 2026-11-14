"""Synthetic telemetry to stdout. No device is opened."""
import json
from datetime import UTC, datetime

for index in range(10):
    print(json.dumps({"channel_id": "jacket_c", "value": 20 + index * 0.1, "unit": "degC",
        "captured_at": datetime.now(UTC).isoformat(), "quality": "good"}), flush=True)
