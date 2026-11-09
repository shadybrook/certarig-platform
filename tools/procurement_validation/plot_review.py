import base64
import csv
import gzip
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import argparse

import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description="Plot saved CertaRig component-selection experiment samples")
parser.add_argument("root", type=Path)
root = parser.parse_args().root.resolve()


def trace(name):
    with gzip.open(root / "cases" / name / "trace.csv.gz", "rt") as stream:
        reader = csv.reader(stream)
        next(reader)
        data = [[float(x) for x in row] for row in reader]
    return list(zip(*data, strict=True))


plt.rcParams.update(
    {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
)
fig, ax = plt.subplots(2, 2, figsize=(12, 7.8), constrained_layout=True)
for name, label, col in [
    ("drv8871_1.5A_TI_testPCB", "1.5A, TI PCB analogy", "#176b52"),
    ("drv8871_3.6A_continuous_claim", "3.6A continuous, unconstrained analogy", "#b24a32"),
]:
    t = trace(name)
    ax[0, 0].plot(t[0], t[2], label=label, color=col, lw=2)
ax[0, 0].axhline(125, color="#a56f1b", ls="--", label="125 C design criterion")
ax[0, 0].set(
    title="Conduction / thermal comparison", xlabel="Time (s)", ylabel="Analog junction temperature (C)"
)
ax[0, 0].legend(fontsize=8)
ax[0, 0].text(
    0.03,
    0.58,
    "Real chip shutdown is omitted.\nHigh model temperature rejects\nthe continuous-current claim.",
    transform=ax[0, 0].transAxes,
    fontsize=8,
)
for name, label, col, which in [
    ("protected_100R_33mA", "Protected candidate ADC pin", "#176b52", 2),
    ("sen0262_burden_33mA_fault", "Unbuffered 120-ohm input fault", "#b24a32", 1),
]:
    t = trace(name)
    ax[0, 1].plot([v * 1000 for v in t[0]], t[which], label=label, color=col, lw=2)
ax[0, 1].axhline(3.6, color="#a56f1b", ls="--", label="3.3 V + 0.3 V input budget")
ax[0, 1].set(title="33 mA receiver fault envelope", xlabel="Time (ms)", ylabel="Voltage (V)", ylim=(0, 4.5))
ax[0, 1].legend(fontsize=8, loc="lower right")
for name, label, col in [
    ("integrated_normal", "Nominal input assumption", "#176b52"),
    ("integrated_unknown_startup_trip", "3A / 100uF assumption: trips", "#b24a32"),
]:
    t = trace(name)
    ax[1, 0].plot(t[0][::5], t[17][::5], label=label, color=col, lw=1.5)
ax[1, 0].set(
    title="Integrated pump terminal voltage", xlabel="Time (s)", ylabel="Pump terminal (V)", xlim=(0, 1.4)
)
ax[1, 0].legend(fontsize=8)
t = trace("integrated_estop")
ax[1, 1].plot(t[0][::5], t[7][::5], label="Pump input demand probe", color="#176b52")
ax[1, 1].plot(t[0][::5], t[8][::5], label="Valve coil current", color="#4786a7")
ax[1, 1].axvspan(0.35, 0.50, alpha=0.18, color="#c38c38", label="E-stop asserted")
ax[1, 1].set(
    title="E-stop / release: behavioral model", xlabel="Time (s)", ylabel="Current (A)", xlim=(0, 1.4)
)
ax[1, 1].legend(fontsize=8)
fig.suptitle(
    "CertaRig product-selection experiments | Bounded models, not physical qualification",
    fontsize=14,
    fontweight="bold",
)
fig.savefig(root / "simulation-plots.png", dpi=150)
html = (root / "index.html").read_text()
embedded = base64.b64encode((root / "simulation-plots.png").read_bytes()).decode()
html = html.replace(
    '<div id="plots"></div>',
    f'<figure><img alt="Saved-sample plots of receiver fault, driver thermal analogy, assumed pump startup and E-stop behavior" src="data:image/png;base64,{embedded}"><figcaption>Plots generated from recorded ngspice samples. Full netlists, logs and samples remain in this pack.</figcaption></figure>',
)
(root / "index.html").write_text(html)
print("Rendered saved-sample figure and embedded it into standalone HTML")
