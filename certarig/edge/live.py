from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .commissioning import ProcessGuardrail, ProcessInterlockResult
from .hardware.base import HardwareAdapter
from .models import RigConfig, RigSnapshot

CSV_FIELDS = (
    "sample_index",
    "timestamp_utc",
    "elapsed_s",
    "event",
    "reason",
    "pressure_voltage_v",
    "pressure_bar",
    "pressure_state",
    "flow_voltage_v",
    "flow_l_min",
    "flow_state",
    "estop_active",
    "process_healthy",
    "trip_latched",
    "permit_requested",
    "gpio23_command_high",
    "relay_energized_expected",
    "red_indicator_expected",
    "green_indicator_expected",
    "record_kind",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class LiveBenchRuntime:
    """Continuously samples the bench, enforces limits, and records CSV evidence."""

    def __init__(
        self,
        config: RigConfig,
        hardware: HardwareAdapter,
        evidence_dir: str | Path,
        allow_output: bool = False,
        history_size: int = 300,
    ) -> None:
        self.config = config
        self.hardware = hardware
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.guardrail = ProcessGuardrail(config, allow_output=allow_output)
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = time.monotonic()
        self._sample_index = 0
        self._history: deque[dict[str, Any]] = deque(maxlen=history_size)
        self._latest: dict[str, Any] = self._empty_state()
        self._last_event = "runtime_started_output_safe"
        self._last_event_at = utc_now()
        self._record_handle: Any | None = None
        self._record_writer: csv.DictWriter[str] | None = None
        self._record_path: Path | None = None
        self._last_record_path: Path | None = None
        self._record_samples = 0
        self.hardware.force_safe_state()

    def _empty_state(self) -> dict[str, Any]:
        return {
            "status": "starting",
            "rig_id": self.config.rig_id,
            "config_hash": self.config.config_hash,
            "actuation_enabled": self.allow_output,
            "captured_at": utc_now(),
            "elapsed_s": 0.0,
            "sample_index": -1,
            "samples": [],
            "guardrail": {
                "drive_high": False,
                "permit_requested": False,
                "trip_latched": True,
                "estop_active": True,
                "process_healthy": False,
                "reason": "startup_safe",
                "event": "runtime_started_output_safe",
                "channels": [],
            },
            "outputs": {
                "gpio23_command_high": False,
                "relay_energized_expected": False,
                "relay_state_source": "commanded_not_feedback",
                "relay_board_power_expected": False,
                "red_indicator_expected": True,
                "green_indicator_expected": False,
            },
            "last_event": "runtime_started_output_safe",
            "last_event_at": utc_now(),
            "recording": {"active": False, "filename": None, "samples": 0},
            "history": [],
            "warning": "Relay and panel-light states are expected from the command/contact model; no feedback sensor is fitted.",
        }

    @property
    def allow_output(self) -> bool:
        return self.guardrail.allow_output

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="certarig-live", daemon=True)
            self._thread.start()

    def _loop(self) -> None:
        interval = self.config.sample_interval_ms / 1000.0
        next_sample = time.monotonic()
        while not self._stop.is_set():
            self.sample_once()
            next_sample += interval
            self._stop.wait(max(0.0, next_sample - time.monotonic()))

    @staticmethod
    def _channel(statuses: tuple[dict[str, object], ...], unit: str) -> dict[str, object]:
        for status in statuses:
            if str(status.get("unit", "")).lower() == unit.lower():
                return status
        return {}

    @staticmethod
    def _finite(value: object) -> float | None:
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _apply_output(self, result: ProcessInterlockResult) -> ProcessInterlockResult:
        try:
            if result.drive_high:
                self.hardware.set_valve(True)
            else:
                self.hardware.force_safe_state()
            return result
        except Exception:
            self.hardware.force_safe_state()
            return self.guardrail.fail_safe("output_driver_error")

    def _compose_state(
        self,
        snapshot: RigSnapshot,
        result: ProcessInterlockResult,
        event: str,
    ) -> dict[str, Any]:
        if event:
            self._last_event = event
            self._last_event_at = utc_now()
        relay_energized = bool(result.drive_high and not result.estop_active)
        elapsed = time.monotonic() - self._started
        return {
            "status": "ok",
            "rig_id": self.config.rig_id,
            "config_hash": self.config.config_hash,
            "actuation_enabled": self.allow_output,
            "captured_at": snapshot.captured_at,
            "elapsed_s": round(elapsed, 6),
            "sample_index": self._sample_index,
            "samples": [
                {
                    "channel_id": sample.channel_id,
                    "value": self._finite(sample.value),
                    "unit": sample.unit,
                    "raw_value": self._finite(sample.raw_value),
                    "quality": sample.quality,
                }
                for sample in snapshot.samples
            ],
            "guardrail": result.to_dict(),
            "outputs": {
                "gpio23_command_high": result.drive_high,
                "relay_energized_expected": relay_energized,
                "relay_state_source": "commanded_not_feedback",
                "relay_board_power_expected": not result.estop_active,
                "red_indicator_expected": not relay_energized,
                "green_indicator_expected": relay_energized,
            },
            "last_event": self._last_event,
            "last_event_at": self._last_event_at,
            "recording": {
                "active": self._record_writer is not None,
                "filename": self._record_path.name if self._record_path else None,
                "samples": self._record_samples,
            },
            "warning": "Relay and panel-light states are expected from the command/contact model; no feedback sensor is fitted.",
        }

    def _csv_row(self, state: dict[str, Any], record_kind: str) -> dict[str, object]:
        guardrail = state["guardrail"]
        channels = tuple(guardrail["channels"])
        pressure = self._channel(channels, "bar")
        flow = self._channel(channels, "L/min")
        raw_samples = {sample["channel_id"]: sample for sample in state["samples"]}
        pressure_raw = raw_samples.get(pressure.get("channel_id"), {})
        flow_raw = raw_samples.get(flow.get("channel_id"), {})
        outputs = state["outputs"]
        return {
            "sample_index": state["sample_index"],
            "timestamp_utc": state["captured_at"],
            "elapsed_s": f"{float(state['elapsed_s']):.6f}",
            "event": guardrail.get("event", ""),
            "reason": guardrail["reason"],
            "pressure_voltage_v": pressure_raw.get("raw_value", ""),
            "pressure_bar": pressure.get("value", ""),
            "pressure_state": pressure.get("state", "missing"),
            "flow_voltage_v": flow_raw.get("raw_value", ""),
            "flow_l_min": flow.get("value", ""),
            "flow_state": flow.get("state", "missing"),
            "estop_active": str(guardrail["estop_active"]).lower(),
            "process_healthy": str(guardrail["process_healthy"]).lower(),
            "trip_latched": str(guardrail["trip_latched"]).lower(),
            "permit_requested": str(guardrail["permit_requested"]).lower(),
            "gpio23_command_high": str(outputs["gpio23_command_high"]).lower(),
            "relay_energized_expected": str(outputs["relay_energized_expected"]).lower(),
            "red_indicator_expected": str(outputs["red_indicator_expected"]).lower(),
            "green_indicator_expected": str(outputs["green_indicator_expected"]).lower(),
            "record_kind": record_kind,
        }

    def _write_record(self, state: dict[str, Any], record_kind: str = "sample") -> None:
        if self._record_writer is None or self._record_handle is None:
            return
        self._record_writer.writerow(self._csv_row(state, record_kind))
        self._record_handle.flush()
        self._record_samples += 1

    def sample_once(self) -> dict[str, Any]:
        with self._lock:
            try:
                snapshot = self.hardware.snapshot()
                result = self.guardrail.observe(snapshot)
                result = self._apply_output(result)
                state = self._compose_state(snapshot, result, result.event)
            except Exception as exc:
                self.hardware.force_safe_state()
                result = self.guardrail.fail_safe("sensor_runtime_error")
                state = dict(self._latest)
                state.update(
                    {
                        "status": "error",
                        "captured_at": utc_now(),
                        "elapsed_s": round(time.monotonic() - self._started, 6),
                        "sample_index": self._sample_index,
                        "guardrail": result.to_dict(),
                        "last_event": result.event,
                        "last_event_at": utc_now(),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                state["outputs"] = {
                    "gpio23_command_high": False,
                    "relay_energized_expected": False,
                    "relay_state_source": "commanded_not_feedback",
                    "relay_board_power_expected": False,
                    "red_indicator_expected": True,
                    "green_indicator_expected": False,
                }
                self._last_event = result.event
                self._last_event_at = state["last_event_at"]
            point = {
                "elapsed_s": state["elapsed_s"],
                "pressure_bar": self._csv_row(state, "sample")["pressure_bar"],
                "flow_l_min": self._csv_row(state, "sample")["flow_l_min"],
                "gpio23_command_high": state["outputs"]["gpio23_command_high"],
                "event": state["guardrail"].get("event", ""),
            }
            self._history.append(point)
            self._latest = state
            self._write_record(state)
            self._sample_index += 1
            return {**state, "history": list(self._history)}

    def state(self) -> dict[str, Any]:
        with self._lock:
            state = json.loads(json.dumps(self._latest))
            state["history"] = list(self._history)
            state["recording"] = {
                "active": self._record_writer is not None,
                "filename": self._record_path.name if self._record_path else None,
                "samples": self._record_samples,
            }
            return state

    def command(self, command: str) -> dict[str, Any]:
        with self._lock:
            result = self.guardrail.command(command)
            result = self._apply_output(result)
            if result.event:
                self._last_event = result.event
                self._last_event_at = utc_now()
            state = dict(self._latest)
            state["guardrail"] = result.to_dict()
            state["last_event"] = self._last_event
            state["last_event_at"] = self._last_event_at
            relay_energized = bool(result.drive_high and not result.estop_active)
            state["outputs"] = {
                "gpio23_command_high": result.drive_high,
                "relay_energized_expected": relay_energized,
                "relay_state_source": "commanded_not_feedback",
                "relay_board_power_expected": not result.estop_active,
                "red_indicator_expected": not relay_energized,
                "green_indicator_expected": relay_energized,
            }
            self._latest = state
            self._write_record(state, "command")
            return self.state()

    @staticmethod
    def _safe_label(label: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", label.strip()).strip("-").lower()
        return cleaned[:40] or "bench-run"

    def start_recording(self, label: str = "bench-run") -> dict[str, Any]:
        with self._lock:
            if self._record_writer is not None:
                raise RuntimeError("a CSV recording is already active")
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            self._record_path = self.evidence_dir / f"{stamp}_{self._safe_label(label)}.csv"
            self._record_handle = self._record_path.open("x", newline="", encoding="utf-8")
            self._record_writer = csv.DictWriter(self._record_handle, fieldnames=CSV_FIELDS)
            self._record_writer.writeheader()
            self._record_handle.flush()
            self._record_samples = 0
            self._last_event = "csv_recording_started"
            self._last_event_at = utc_now()
            return self.state()

    def stop_recording(self) -> dict[str, Any]:
        with self._lock:
            if self._record_writer is None or self._record_handle is None or self._record_path is None:
                raise RuntimeError("no CSV recording is active")
            self._record_handle.flush()
            self._record_handle.close()
            completed_path = self._record_path
            samples = self._record_samples
            digest = hashlib.sha256(completed_path.read_bytes()).hexdigest()
            self._last_record_path = completed_path
            self._record_handle = None
            self._record_writer = None
            self._record_path = None
            self._last_event = "csv_recording_stopped"
            self._last_event_at = utc_now()
            state = self.state()
            state["completed_recording"] = {
                "filename": completed_path.name,
                "samples": samples,
                "sha256": digest,
            }
            return state

    def latest_recording(self) -> Path | None:
        with self._lock:
            path = self._record_path or self._last_record_path
            if path is None or not path.is_file():
                return None
            return path

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        with self._lock:
            self.hardware.force_safe_state()
            if self._record_handle is not None:
                self._record_handle.close()
                self._record_handle = None
                self._record_writer = None
            self.hardware.close()
