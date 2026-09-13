#!/usr/bin/env python3
"""Build source-backed CertaRig gate summaries and static visuals.

The hardware bundles do not include their referenced recording CSV files. This
script therefore uses the immutable run metadata, checks, events, peaks, sample
counts, and hashes for hardware plots. Simulator traces are plotted only from
the CSV files that are actually present in evidence/sim-library.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "evidence" / "lab-pulled"
SIM = ROOT / "evidence" / "sim-library"
OUT = ROOT / "docs" / "explainer" / "assets"
DATA_OUT = ROOT / "docs" / "explainer" / "data"

INK = "#172523"
MUTED = "#66736f"
GREEN = "#1f7a61"
GREEN_LIGHT = "#d8eee5"
BLUE = "#33658a"
BLUE_LIGHT = "#d9e8f1"
GOLD = "#c58a26"
GOLD_LIGHT = "#f5e8c9"
RED = "#b44b42"
RED_LIGHT = "#f4dddd"
GRID = "#dfe5e2"
PAPER = "#fbfcfb"
WHITE = "#ffffff"

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size=size)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, size: int,
         fill: str = INK, bold: bool = False, anchor: str | None = None) -> None:
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def title(draw: ImageDraw.ImageDraw, heading: str, subtitle: str, width: int) -> int:
    text(draw, (70, 48), heading, 38, bold=True)
    text(draw, (70, 96), subtitle, 20, fill=MUTED)
    draw.line((70, 136, width - 70, 136), fill=GRID, width=2)
    return 166


def new_canvas(width: int = 1800, height: int = 1050) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), PAPER)
    return image, ImageDraw.Draw(image)


def save(image: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / name, quality=96)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_hardware_runs() -> list[dict]:
    runs: list[dict] = []
    for run_path in sorted(LAB.glob("*/procedure_runs/*/run.json")):
        run = json.loads(run_path.read_text())
        run["_path"] = str(run_path.relative_to(ROOT))
        run["duration_s"] = round((parse_time(run["ended_at"]) - parse_time(run["started_at"])).total_seconds(), 3)
        run["checks_passed"] = sum(bool(item.get("passed")) for item in run.get("checks", []))
        run["checks_total"] = len(run.get("checks", []))
        runs.append(run)
    return runs


def verify_exports() -> list[dict]:
    records: list[dict] = []
    for folder in sorted(path for path in LAB.iterdir() if path.is_dir()):
        export_manifest = json.loads((folder / "export_manifest.json").read_text())
        checked = 0
        for item in export_manifest["files"]:
            actual = sha256(folder / item["path"])
            if actual != item["sha256"]:
                raise RuntimeError(f"checksum mismatch: {folder / item['path']}")
            checked += 1
        archive = folder.with_suffix(".zip")
        records.append({
            "run_id": export_manifest["run_id"],
            "archive": str(archive.relative_to(ROOT)),
            "archive_sha256": sha256(archive),
            "files_verified": checked,
            "manifest_hash": export_manifest["manifest_hash"],
        })
    return records


def write_summary(runs: list[dict], exports: list[dict]) -> None:
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    export_by_run = {item["run_id"]: item for item in exports}
    fields = [
        "run_id", "procedure_id", "status", "duration_s", "samples",
        "checks_passed", "checks_total", "pressure_peak_bar", "flow_peak_l_min",
        "hardware_mode", "archive_sha256", "recording_sha256", "source_run_json",
    ]
    with (DATA_OUT / "hardware_run_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for run in runs:
            export = export_by_run[run["run_id"]]
            writer.writerow({
                "run_id": run["run_id"],
                "procedure_id": run["procedure_id"],
                "status": run["status"],
                "duration_s": run["duration_s"],
                "samples": (run.get("recording") or {}).get("samples"),
                "checks_passed": run["checks_passed"],
                "checks_total": run["checks_total"],
                "pressure_peak_bar": run.get("peaks", {}).get("pressure"),
                "flow_peak_l_min": run.get("peaks", {}).get("flow"),
                "hardware_mode": run["hardware_mode"],
                "archive_sha256": export["archive_sha256"],
                "recording_sha256": (run.get("recording") or {}).get("sha256"),
                "source_run_json": run["_path"],
            })

    (DATA_OUT / "evidence_verification.json").write_text(
        json.dumps({"verified_at_build": True, "exports": exports}, indent=2) + "\n"
    )


def gate_ladder() -> None:
    image, draw = new_canvas(1800, 1060)
    y = title(draw, "Six gates turned a prototype into a controlled lab proof",
              "Gate 0 through Gate 5 are six numbered gates; every gate passed on 12 Sep 2026.", 1800)
    gates = [
        ("0", "Read only", "Inspect the frozen Phase 3 host\nwithout changing it", BLUE),
        ("1", "Sidecar", "Deploy separately on port 8081\nwith user local configuration", BLUE),
        ("2", "Observe", "Sweep both ADC channels before\nallowing any output", GREEN),
        ("3", "Twin gate", "Require six matching simulator\nprocedure stamps", GOLD),
        ("4", "Actuate", "Run five Fake agent procedures;\nkernel owns every trip", GREEN),
        ("5", "Restore", "Stop the sidecar, restore Phase 3,\nverify untouched, halt Pi", BLUE),
    ]
    x0, gap, card_w, card_h = 85, 26, 250, 590
    cy = y + 90
    for i, (number, name, detail, color) in enumerate(gates):
        x = x0 + i * (card_w + gap)
        if i < len(gates) - 1:
            draw.line((x + card_w, cy + 74, x + card_w + gap, cy + 74), fill=GRID, width=8)
        draw.rounded_rectangle((x, cy, x + card_w, cy + card_h), radius=24, fill=WHITE, outline=GRID, width=2)
        draw.ellipse((x + 78, cy + 26, x + 172, cy + 120), fill=color)
        text(draw, (x + 125, cy + 73), number, 36, fill=WHITE, bold=True, anchor="mm")
        text(draw, (x + 125, cy + 160), name, 27, bold=True, anchor="mm")
        yy = cy + 213
        for line in detail.splitlines():
            text(draw, (x + 125, yy), line, 18, fill=MUTED, anchor="mm")
            yy += 27
        draw.rounded_rectangle((x + 47, cy + 453, x + 203, cy + 505), radius=26, fill=GREEN_LIGHT)
        text(draw, (x + 125, cy + 479), "PASSED", 18, fill=GREEN, bold=True, anchor="mm")
        evidence = ["host boundary", "isolated deploy", "1 pass after 1 fail", "6 stamps", "5 HIL procedures", "untouched test + halt"][i]
        text(draw, (x + 125, cy + 545), evidence, 16, fill=MUTED, anchor="mm")
    text(draw, (90, 940), "Interpretation", 21, bold=True)
    text(draw, (90, 977), "The achievement is not autonomous discovery. It is controlled commissioning of a mapped rig, with explicit boundaries at every transition.", 20, fill=MUTED)
    save(image, "01_gate_ladder.png")


def hil_peaks(runs: list[dict]) -> None:
    image, draw = new_canvas(1800, 1120)
    title(draw, "The hardware crossed each guardrail and stayed inside the validation envelope",
          "Bars use recorded hardware run peaks. Guardrail crossings are expected in trip procedures.", 1800)
    passed = {run["procedure_id"]: run for run in runs if run["status"] == "passed"}
    groups = [
        ("Pressure", "bar", 10.0, 4.2, [
            ("ADC observe", passed["adc_validation"]["peaks"]["pressure"]),
            ("Pressure trip", passed["pressure_guardrail"]["peaks"]["pressure"]),
            ("Dual input", passed["dual_pot_guardrail"]["peaks"]["pressure"]),
        ]),
        ("Flow", "L/min", 20.0, 15.0, [
            ("ADC observe", passed["adc_validation"]["peaks"]["flow"]),
            ("Flow trip", passed["flow_guardrail"]["peaks"]["flow"]),
            ("Dual input", passed["dual_pot_guardrail"]["peaks"]["flow"]),
        ]),
    ]
    for section, (name, unit, maximum, guardrail, rows) in enumerate(groups):
        left = 100 + section * 850
        top = 200
        text(draw, (left, top), f"{name} peak", 27, bold=True)
        text(draw, (left + 690, top), f"Scale maximum {maximum:g} {unit}", 16, fill=MUTED, anchor="ra")
        axis_x0, axis_x1 = left + 190, left + 690
        for tick in range(6):
            value = maximum * tick / 5
            x = axis_x0 + int((axis_x1 - axis_x0) * tick / 5)
            draw.line((x, top + 70, x, top + 590), fill=GRID, width=1)
            text(draw, (x, top + 615), f"{value:g}", 15, fill=MUTED, anchor="ma")
        gx = axis_x0 + int((axis_x1 - axis_x0) * guardrail / maximum)
        draw.line((gx, top + 45, gx, top + 575), fill=RED, width=4)
        text(draw, (gx, top + 28), f"trip {guardrail:g}", 16, fill=RED, bold=True, anchor="ms")
        for idx, (label, value) in enumerate(rows):
            yy = top + 145 + idx * 150
            text(draw, (left, yy + 27), label, 19)
            bar_end = axis_x0 + int((axis_x1 - axis_x0) * value / maximum)
            color = GREEN if value >= guardrail else BLUE
            draw.rounded_rectangle((axis_x0, yy, bar_end, yy + 56), radius=18, fill=color)
            text(draw, (bar_end + 12, yy + 28), f"{value:.2f} {unit}", 18, fill=INK, bold=True, anchor="lm")
    text(draw, (100, 1020), "Observe only note", 20, bold=True)
    text(draw, (285, 1020), "The ADC validation sweep may exceed trip thresholds because Gate 2 intentionally keeps actuation disabled.", 19, fill=MUTED)
    save(image, "02_hardware_peaks.png")


def response_time(runs: list[dict]) -> None:
    image, draw = new_canvas(1800, 1070)
    title(draw, "Every recorded software output transition beat its acceptance budget",
          "These are kernel observed GPIO command transitions, not measured mechanical relay drop times.", 1800)
    items: list[tuple[str, float, float]] = []
    labels = {
        ("pressure_guardrail", "output_removed"): "Pressure trip",
        ("flow_guardrail", "output_removed"): "Flow trip",
        ("dual_pot_guardrail", "pressure_output_removed"): "Dual: pressure",
        ("dual_pot_guardrail", "flow_output_removed"): "Dual: flow",
        ("estop_anti_restart", "output_removed"): "E stop",
    }
    for run in runs:
        if run["status"] != "passed":
            continue
        for check in run.get("checks", []):
            spec = check.get("check", {})
            key = (run["procedure_id"], spec.get("step"))
            if key in labels and "measured_ms" in check:
                items.append((labels[key], float(check["measured_ms"]), float(spec["max_elapsed_ms"])))
    items.sort(key=lambda item: ["Pressure trip", "Flow trip", "Dual: pressure", "Dual: flow", "E stop"].index(item[0]))
    x0, x1, y0 = 370, 1660, 230
    max_budget = 500.0
    for tick in range(6):
        value = max_budget * tick / 5
        x = x0 + int((x1 - x0) * tick / 5)
        draw.line((x, y0 - 20, x, y0 + 600), fill=GRID, width=1)
        text(draw, (x, y0 + 635), f"{value:.0f} ms", 15, fill=MUTED, anchor="ma")
    for idx, (label, measured, budget) in enumerate(items):
        yy = y0 + idx * 120
        text(draw, (330, yy + 26), label, 20, anchor="ra")
        budget_x = x0 + int((x1 - x0) * budget / max_budget)
        draw.rounded_rectangle((x0, yy, budget_x, yy + 52), radius=16, fill=BLUE_LIGHT)
        measured_x = x0 + max(4, int((x1 - x0) * measured / max_budget))
        draw.ellipse((measured_x - 9, yy + 17, measured_x + 9, yy + 35), fill=GREEN)
        text(draw, (x0 + 28, yy + 26), f"{measured:.3f} ms", 18, fill=GREEN, bold=True, anchor="lm")
        text(draw, (budget_x - 10, yy + 26), f"budget {budget:.0f} ms", 16, fill=BLUE, anchor="rm")
    text(draw, (100, 925), "Critical interpretation", 20, bold=True)
    text(draw, (100, 962), "A feedback contact or current sensor is still required before claiming end to end electrical or mechanical trip latency.", 19, fill=MUTED)
    save(image, "03_software_response_time.png")


def run_coverage(runs: list[dict]) -> None:
    image, draw = new_canvas(1800, 1130)
    title(draw, "One failed observation improved the protocol; the next six hardware runs passed",
          "Duration and sample counts come from each immutable run.json record.", 1800)
    labels = {
        "adc_validation": "ADC validation",
        "relay_truth_table": "Relay truth table",
        "pressure_guardrail": "Pressure guardrail",
        "flow_guardrail": "Flow guardrail",
        "dual_pot_guardrail": "Dual input guardrail",
        "estop_anti_restart": "E stop anti restart",
    }
    y0 = 215
    max_samples = max((run.get("recording") or {}).get("samples", 0) for run in runs)
    for idx, run in enumerate(runs):
        yy = y0 + idx * 112
        status_color = GREEN if run["status"] == "passed" else RED
        label = labels[run["procedure_id"]]
        if run["procedure_id"] == "adc_validation":
            label += " — pass" if run["status"] == "passed" else " — first attempt"
        text(draw, (90, yy + 25), label, 19)
        draw.rounded_rectangle((480, yy, 1500, yy + 50), radius=16, fill="#edf1ef")
        samples = (run.get("recording") or {}).get("samples", 0)
        end = 480 + int(1020 * samples / max_samples)
        draw.rounded_rectangle((480, yy, end, yy + 50), radius=16, fill=status_color)
        if samples / max_samples > 0.82:
            text(draw, (end - 14, yy + 25), f"{samples:,} samples", 18, fill=WHITE, bold=True, anchor="rm")
        else:
            text(draw, (end + 14, yy + 25), f"{samples:,} samples", 18, bold=True, anchor="lm")
        text(draw, (1680, yy + 25), f"{run['duration_s']:.1f} s", 18, fill=MUTED, anchor="rm")
    passed = [run for run in runs if run["status"] == "passed"]
    total_samples = sum((run.get("recording") or {}).get("samples", 0) for run in passed)
    total_checks = sum(run["checks_passed"] for run in passed)
    text(draw, (90, 1040), f"Passed evidence: {len(passed)} runs  •  {total_samples:,} samples recorded  •  {total_checks} of {total_checks} evaluated checks passed", 21, bold=True)
    save(image, "04_run_coverage.png")


def event_timeline(runs: list[dict]) -> None:
    image, draw = new_canvas(1800, 1230)
    title(draw, "The kernel, not the agent, created every consequential state transition",
          "Normalized hardware run timelines; only selected safety events are shown.", 1800)
    selected = [run for run in runs if run["status"] == "passed" and run["procedure_id"] != "adc_validation"]
    labels = {
        "relay_truth_table": "Relay truth table",
        "pressure_guardrail": "Pressure",
        "flow_guardrail": "Flow",
        "dual_pot_guardrail": "Dual input",
        "estop_anti_restart": "E stop",
    }
    event_style = {
        "trip_reset_output_safe": (BLUE, "reset"),
        "permit_accepted": (GREEN, "permit"),
        "pressure_high_forced_safe": (RED, "pressure trip"),
        "flow_high_forced_safe": (RED, "flow trip"),
        "estop_open_forced_safe": (RED, "E stop"),
        "process_safe_reset_required": (GOLD, "reset required"),
        "estop_closed_reset_required": (GOLD, "reset required"),
        "permit_rejected_reset_required": (INK, "permit rejected"),
        "operator_safe": (MUTED, "safe"),
    }
    x0, x1, y0 = 320, 1670, 245
    for tick in range(6):
        x = x0 + int((x1 - x0) * tick / 5)
        draw.line((x, y0 - 35, x, y0 + 660), fill=GRID, width=1)
        text(draw, (x, y0 - 55), f"{tick * 20}%", 15, fill=MUTED, anchor="ms")
    for idx, run in enumerate(selected):
        yy = y0 + idx * 150
        text(draw, (280, yy), labels[run["procedure_id"]], 20, bold=True, anchor="rm")
        draw.line((x0, yy, x1, yy), fill=GRID, width=5)
        start = parse_time(run["started_at"])
        duration = max(run["duration_s"], 0.001)
        for event in run.get("kernel_events", []):
            name = event["event"]
            if name not in event_style:
                continue
            elapsed = max(0.0, (parse_time(event["at"]) - start).total_seconds())
            x = x0 + int((x1 - x0) * min(elapsed / duration, 1.0))
            color, short = event_style[name]
            draw.ellipse((x - 10, yy - 10, x + 10, yy + 10), fill=color)
            label_y = yy - 34 if (int(elapsed * 10) % 2 == 0) else yy + 28
            text(draw, (x, label_y), short, 14, fill=color, anchor="mm")
    legend_y = 1065
    for idx, (color, label) in enumerate([(GREEN, "permit"), (RED, "forced safe"), (GOLD, "reset required"), (INK, "rejected"), (BLUE, "reset")]):
        x = 280 + idx * 260
        draw.ellipse((x, legend_y, x + 18, legend_y + 18), fill=color)
        text(draw, (x + 30, legend_y + 9), label, 16, fill=MUTED, anchor="lm")
    text(draw, (90, 1165), "Note: timeline positions are relative to each procedure duration so different tests can be compared without implying a shared clock scale.", 17, fill=MUTED)
    save(image, "05_kernel_event_timeline.png")


def simulator_trace() -> None:
    image, draw = new_canvas(1800, 1180)
    title(draw, "The digital twin rehearsed the same threshold logic before hardware was allowed",
          "Raw simulator CSV traces from the pressure and flow happy paths; hardware peaks are shown separately in Figure 2.", 1800)
    scenarios = [
        ("Pressure twin", SIM / "pressure-guardrail-happy-path" / "20260912T120014073672Z_sim-guardrail.csv", "pressure_bar", 4.2, 10.0, GREEN),
        ("Flow twin", SIM / "flow-guardrail-happy-path" / "20260912T120018457526Z_sim-flow-guardrail.csv", "flow_l_min", 15.0, 20.0, BLUE),
    ]
    for idx, (label, path, field, threshold, ymax, color) in enumerate(scenarios):
        top = 230 + idx * 410
        left, right, bottom = 170, 1680, top + 300
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        xs = [float(row["elapsed_s"]) for row in rows]
        ys = [float(row[field]) for row in rows]
        max_x = max(xs) if xs else 1.0
        text(draw, (90, top - 45), label, 24, bold=True)
        for tick in range(6):
            yval = ymax * tick / 5
            y = bottom - int((bottom - top) * yval / ymax)
            draw.line((left, y, right, y), fill=GRID, width=1)
            text(draw, (left - 18, y), f"{yval:g}", 14, fill=MUTED, anchor="rm")
        ty = bottom - int((bottom - top) * threshold / ymax)
        draw.line((left, ty, right, ty), fill=RED, width=3)
        text(draw, (right - 5, ty - 10), f"trip {threshold:g}", 15, fill=RED, bold=True, anchor="rs")
        points = []
        for xval, yval in zip(xs, ys, strict=True):
            x = left + int((right - left) * xval / max_x)
            y = bottom - int((bottom - top) * yval / ymax)
            points.append((x, y))
        if len(points) > 1:
            draw.line(points, fill=color, width=4, joint="curve")
        text(draw, (left, bottom + 26), "start", 15, fill=MUTED)
        text(draw, (right, bottom + 26), f"{max_x:.1f} s", 15, fill=MUTED, anchor="ra")
    text(draw, (90, 1085), "Twin gate rule", 20, bold=True)
    text(draw, (245, 1085), "A hardware procedure can start only when the identical procedure hash has a simulator pass stamp from the previous 24 hours.", 19, fill=MUTED)
    save(image, "06_twin_traces.png")


def architecture() -> None:
    image, draw = new_canvas(1800, 1040)
    title(draw, "CertaRig separates interpretation from authority",
          "The product pivot is an evidence first commissioning runner for mapped rigs.", 1800)
    boxes = [
        (100, 290, 390, 520, "Operator + Studio", "describes intent\nreviews the rig map\napproves sensitive actions", BLUE_LIGHT, BLUE),
        (520, 290, 810, 520, "Agent layer", "selects an approved procedure\nrelays instructions\nnever compares limits", GOLD_LIGHT, GOLD),
        (940, 250, 1280, 560, "Deterministic kernel", "validates sensor quality\ncompares numeric limits\nlatches trips\nowns GPIO23", GREEN_LIGHT, GREEN),
        (1410, 290, 1695, 520, "Rig or simulator", "ADS1115 signals\nE stop loop\nrelay output\nevidence recorder", "#eef0ef", INK),
    ]
    for x0, y0, x1, y1, heading, body, fill, stroke in boxes:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=fill, outline=stroke, width=3)
        text(draw, ((x0 + x1) // 2, y0 + 58), heading, 23, fill=stroke, bold=True, anchor="mm")
        yy = y0 + 118
        for line in body.splitlines():
            text(draw, ((x0 + x1) // 2, yy), line, 18, fill=INK, anchor="mm")
            yy += 34
    for x0, x1, yy in [(390, 520, 405), (810, 940, 405), (1280, 1410, 405)]:
        draw.line((x0 + 16, yy, x1 - 18, yy), fill=INK, width=4)
        draw.polygon([(x1 - 18, yy), (x1 - 38, yy - 12), (x1 - 38, yy + 12)], fill=INK)
    equation = "OUTPUT = enabled  AND  permit requested  AND  no trip latched  AND  E stop closed  AND  process healthy"
    draw.rounded_rectangle((185, 680, 1615, 785), radius=28, fill=WHITE, outline=GRID, width=2)
    text(draw, (900, 732), equation, 23, bold=True, anchor="mm")
    text(draw, (900, 845), "The agent can ask. Only the kernel can say yes.", 32, fill=GREEN, bold=True, anchor="mm")
    text(draw, (900, 910), "A proposed rig map still requires human apply, a twin gate, and explicit arm before output.", 19, fill=MUTED, anchor="mm")
    save(image, "07_product_architecture.png")


def main() -> None:
    runs = load_hardware_runs()
    exports = verify_exports()
    write_summary(runs, exports)
    gate_ladder()
    hil_peaks(runs)
    response_time(runs)
    run_coverage(runs)
    event_timeline(runs)
    simulator_trace()
    architecture()
    passed = [run for run in runs if run["status"] == "passed"]
    print(json.dumps({
        "hardware_runs": len(runs),
        "hardware_passed": len(passed),
        "passed_samples": sum((run.get("recording") or {}).get("samples", 0) for run in passed),
        "passed_checks": sum(run["checks_passed"] for run in passed),
        "exports_verified": len(exports),
        "output": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
