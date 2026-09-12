#!/usr/bin/env python3
"""Render the CertaRig P1 ADS1115 voltage sweep as Phase 3 evidence."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "output" / "phase3_evidence" / "2026-09-09_p1_sweep"
SOURCE = EVIDENCE / "p1_a0_voltage_sweep_retry.csv"
OUTPUT = EVIDENCE / "p1_a0_voltage_sweep_time_plot.png"

with SOURCE.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
elapsed = np.array([float(row["elapsed_s"]) for row in rows])
voltage = np.array([float(row["voltage_v"]) for row in rows])
window = 11
padded = np.pad(voltage, (window // 2, window // 2), mode="edge")
rolling_median = np.array([np.median(padded[i : i + window]) for i in range(len(voltage))])

SCALE = 2
W, H = 2400, 1350
im = Image.new("RGB", (W * SCALE, H * SCALE), "#F7F8FA")
draw = ImageDraw.Draw(im, "RGBA")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size * SCALE)


def pt(x: float, y: float) -> tuple[int, int]:
    return int(x * SCALE), int(y * SCALE)


def text(x: float, y: float, value: str, size: int, color: str, *, bold: bool = False, anchor: str = "la") -> None:
    draw.text(pt(x, y), value, font=font(size, bold), fill=color, anchor=anchor)


plot_left, plot_top, plot_right, plot_bottom = 175, 220, 2310, 1080
x_min, x_max = 0.0, 80.0
y_min, y_max = -0.32, 3.5


def sx(value: float) -> float:
    return plot_left + (value - x_min) / (x_max - x_min) * (plot_right - plot_left)


def sy(value: float) -> float:
    return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)


draw.rounded_rectangle([*pt(70, 55), *pt(2330, 1265)], radius=22 * SCALE, fill="#FFFFFF", outline="#E3E8EE", width=2 * SCALE)
text(125, 110, "CertaRig P1 Potentiometer: ADS1115 A0 Voltage Sweep", 40, "#17212B", bold=True)
text(125, 165, f"Raspberry Pi 3 A+  |  ADS1115 at 0x48  |  {len(voltage)} samples  |  {elapsed[-1]:.1f} seconds  |  10 Hz", 22, "#52606D")

regions = [
    (0.0, 31.0, "OFF / LEFT\nBASELINE", "#E9EEF4"),
    (31.0, 38.5, "TRANSITION", "#FCEFD8"),
    (38.5, 44.5, "CENTRE\nREGION", "#E7F0F8"),
    (45.0, 50.0, "RIGHT\nPLATEAU", "#ECE7F4"),
    (50.0, 62.0, "RETURN\nTRANSITION", "#FCEFD8"),
    (62.0, 80.0, "OFF / LEFT\nBASELINE", "#E9EEF4"),
]
for start, end, label, color in regions:
    draw.rectangle([*pt(sx(start), plot_top), *pt(sx(end), plot_bottom)], fill=color + "88")
    label_y = 245 if "RIGHT" not in label else 360
    text((sx(start) + sx(end)) / 2, label_y, label, 16, "#344054", bold=True, anchor="ma")

for y in np.arange(0.0, 3.6, 0.5):
    draw.line([*pt(plot_left, sy(float(y))), *pt(plot_right, sy(float(y)))], fill="#D9E0E7", width=SCALE)
    text(plot_left - 23, sy(float(y)), f"{y:.1f}", 18, "#52606D", anchor="rm")
for x in np.arange(0.0, 81.0, 5.0):
    draw.line([*pt(sx(float(x)), plot_top), *pt(sx(float(x)), plot_bottom)], fill="#EEF1F4", width=SCALE)
    text(sx(float(x)), plot_bottom + 28, f"{int(x)}", 18, "#52606D", anchor="ma")

draw.line([*pt(plot_left, plot_top), *pt(plot_left, plot_bottom)], fill="#7B8794", width=2 * SCALE)
draw.line([*pt(plot_left, plot_bottom), *pt(plot_right, plot_bottom)], fill="#7B8794", width=2 * SCALE)


def dashed_horizontal(y: float, color: str) -> None:
    x = plot_left
    while x < plot_right:
        draw.line([*pt(x, sy(y)), *pt(min(x + 13, plot_right), sy(y))], fill=color, width=2 * SCALE)
        x += 23


dashed_horizontal(0.0, "#4B5563")
dashed_horizontal(1.65, "#C88A1A")
dashed_horizontal(3.3, "#713F98")
raw_points = [pt(sx(float(x)), sy(float(y))) for x, y in zip(elapsed, voltage)]
median_points = [pt(sx(float(x)), sy(float(y))) for x, y in zip(elapsed, rolling_median)]
draw.line(raw_points, fill="#93A4B8AA", width=2 * SCALE, joint="curve")
draw.line(median_points, fill="#1261A0", width=5 * SCALE, joint="curve")

draw.ellipse([*pt(sx(47.0) - 7, sy(3.24) - 7), *pt(sx(47.0) + 7, sy(3.24) + 7)], fill="#713F98")
draw.line([*pt(sx(47.0) + 8, sy(3.24) + 5), *pt(sx(52.0), sy(2.78))], fill="#713F98", width=2 * SCALE)
text(sx(52.2), sy(2.78), "Observed high plateau about 3.24 V", 19, "#52306E", bold=True, anchor="lm")

text((plot_left + plot_right) / 2, 1150, "Elapsed time (seconds)", 22, "#344054", bold=True, anchor="ma")
y_label = Image.new("RGBA", (600 * SCALE, 60 * SCALE), (0, 0, 0, 0))
y_draw = ImageDraw.Draw(y_label)
y_draw.text((300 * SCALE, 30 * SCALE), "A0 voltage (V)", font=font(22, True), fill="#344054", anchor="mm")
y_label = y_label.rotate(90, expand=True)
im.paste(y_label, pt(80, 425), y_label)

legend_y = 1205
draw.line([*pt(150, legend_y), *pt(205, legend_y)], fill="#93A4B8", width=3 * SCALE)
text(220, legend_y, "Raw A0 samples", 17, "#344054", anchor="lm")
draw.line([*pt(475, legend_y), *pt(530, legend_y)], fill="#1261A0", width=5 * SCALE)
text(545, legend_y, "1-second rolling median", 17, "#344054", anchor="lm")
draw.line([*pt(960, legend_y), *pt(1015, legend_y)], fill="#C88A1A", width=3 * SCALE)
text(1030, legend_y, "Nominal centre 1.65 V", 17, "#344054", anchor="lm")
draw.line([*pt(1425, legend_y), *pt(1480, legend_y)], fill="#713F98", width=3 * SCALE)
text(1495, legend_y, "3.3 V supply reference", 17, "#344054", anchor="lm")
text(125, 1305, "Positions are inferred from plateaus because operator markers were not synchronised into the CSV. Negative transition samples are retained for follow-up inspection.", 17, "#5F6B76")

im.resize((W, H), Image.Resampling.LANCZOS).save(OUTPUT, quality=96)
print(OUTPUT)
