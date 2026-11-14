"""Read-only Edge wrapper for an operator-installed observation source."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models import RigSnapshot, Sample
from .base import HardwareAdapter, HardwareError


class ObservationHardware(HardwareAdapter):
    def __init__(self, config: Any, source: Any):
        if not config.hardware.observe_only:
            raise HardwareError("Observation connectors require observe_only")
        self.config, self.source = config, source

    def snapshot(self) -> RigSnapshot:
        timestamp = datetime.now(UTC).isoformat()
        measured = {row["channel_id"]: row for row in self.source.read()}
        status = self.source.status()
        samples = []
        for channel in self.config.channels:
            row = measured.get(channel.channel_id)
            if row:
                quality = row["quality"]
                if quality == "good" and not channel.valid_min <= row["value"] <= channel.valid_max:
                    quality = "out_of_range"
                samples.append(
                    Sample(
                        channel.channel_id,
                        row["value"],
                        channel.unit,
                        row.get("raw_value"),
                        quality,
                        row["captured_at"],
                    )
                )
            else:
                quality = "disconnected" if not status["connected"] else status.get("quality", "missing")
                samples.append(
                    Sample(
                        channel.channel_id,
                        0,
                        channel.unit,
                        None,
                        "missing" if quality == "good" else quality,
                        timestamp,
                    )
                )
        # Unknown equipment feedback never becomes a safe output indication.
        return RigSnapshot(
            self.config.rig_id, self.config.config_hash, False, False, tuple(samples), timestamp
        )

    def set_valve(self, open_state: bool) -> None:
        raise HardwareError("Observation connector has no equipment command interface")

    def force_safe_state(self) -> None:
        pass  # No output channel exists; this cannot claim a remote safe state.

    def output_is_safe(self) -> bool:
        return False

    def status(self) -> dict[str, Any]:
        return dict(self.source.status())

    def close(self) -> None:
        self.source.close()
