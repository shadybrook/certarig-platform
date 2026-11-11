"""Check saved electrical simulation evidence without running ngspice."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

from run_spice import Case, assess, flow, power, receiver


def verify(root: Path) -> int:
    manifest = root / "SHA256SUMS"
    entries = [line.split("  ", 1) for line in manifest.read_text().splitlines() if line]
    for expected, relative in entries:
        target = (root / relative).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError(f"Missing or invalid evidence path: {relative}")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Checksum mismatch: {relative}")
    summary = json.loads((root / "summary.json").read_text())
    if not summary["required_pass"] or not summary["diagnostics_detected"]:
        raise ValueError("The declared simulation gate did not pass")
    for saved in summary["results"]:
        if "error" in saved:
            raise ValueError(f"Invalid simulation: {saved['name']}")
        folder = root / "cases" / saved["name"]
        circuit = folder / "circuit.cir"
        if hashlib.sha256(circuit.read_bytes()).hexdigest() != saved["netlist_sha256"]:
            raise ValueError(f"Netlist identity mismatch: {saved['name']}")
        with gzip.open(folder / "trace.csv.gz", "rt") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            samples = [[float(value) for value in row] for row in reader]
        end = 1.4 if saved["family"] == "power" else 0.04 if saved["family"] == "receiver" else 0.02
        if not samples or samples[-1][0] < end - 1e-8:
            raise ValueError(f"Incomplete trace: {saved['name']}")
        if len(samples) != saved["samples"] or not all(math.isfinite(x) for row in samples for x in row):
            raise ValueError(f"Invalid samples: {saved['name']}")
        case = Case(saved["name"], saved["family"], saved["revision"], saved["params"], saved["diagnostic"])
        generated = {"power": power, "receiver": receiver, "flow": flow}[case.family](case)
        if hashlib.sha256(generated.encode()).hexdigest() != saved["netlist_sha256"]:
            raise ValueError(f"Generator no longer reproduces netlist: {saved['name']}")
        replay = assess(case, header, samples)
        if any(replay[key] != saved[key] for key in ["checks", "metrics", "criteria_pass"]):
            raise ValueError(f"Replayed measurements differ: {saved['name']}")
    return len(summary["results"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        count = verify(args.root.resolve())
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"VERIFICATION FAILED: {exc}") from exc
    print(f"VERIFIED: checksums and recorded-sample replay for {count} simulation scenarios")


if __name__ == "__main__":
    main()
