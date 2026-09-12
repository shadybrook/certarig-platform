#!/usr/bin/env python3
"""Record a timestamped ADS1115 voltage sweep for Phase 3 evidence."""

from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from certarig_edge.hardware.raspberry_pi import ADS1115Reader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--rate", type=float, default=10.0)
    parser.add_argument("--channel", type=int, default=0)
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--address", type=lambda value: int(value, 0), default=0x48)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duration <= 0 or args.rate <= 0:
        raise SystemExit("duration and rate must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    adc = ADS1115Reader(args.bus, args.address)
    interval = 1.0 / args.rate
    started = time.monotonic()
    sample_index = 0

    print(
        f"LOGGING_IS_ON output={args.output} duration={args.duration:.1f}s "
        f"rate={args.rate:.1f}Hz channel=A{args.channel}",
        flush=True,
    )
    try:
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "sample_index",
                    "timestamp_utc",
                    "elapsed_s",
                    "channel",
                    "voltage_v",
                    "adc_count_derived",
                ]
            )
            while True:
                elapsed = time.monotonic() - started
                if elapsed > args.duration:
                    break
                voltage = adc.read_voltage(args.channel)
                adc_count = round(voltage * 32768.0 / 4.096)
                writer.writerow(
                    [
                        sample_index,
                        datetime.now(timezone.utc).isoformat(),
                        f"{elapsed:.6f}",
                        f"A{args.channel}",
                        f"{voltage:.6f}",
                        adc_count,
                    ]
                )
                handle.flush()
                sample_index += 1
                sleep_for = interval - ((time.monotonic() - started) % interval)
                time.sleep(max(0.0, sleep_for))
    finally:
        adc.close()

    print(f"LOGGING_COMPLETE samples={sample_index} output={args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
