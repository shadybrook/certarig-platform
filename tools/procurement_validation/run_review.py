"""Replayable, bounded component-selection experiments; never a hardware release.

Python standard library + ngspice. No provider calls or connection to equipment.
The models deliberately distinguish published values from assumed envelopes.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE = Path(__file__).resolve().parent.parent / "circuit_validation"
if BASELINE.is_dir():
    sys.path.insert(0, str(BASELINE))
import run_spice as baseline  # noqa: E402


def finish(body, vectors, end, step):
    return (
        body
        + f"""
.options method=gear reltol=1e-5
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran {step} {end} 0 {step}
wrdata trace.dat {vectors}
quit
.endc
.end
"""
    )


def circuit(case):
    p = case["params"]
    family = case["family"]
    if family == "integrated":
        text = baseline.power(
            baseline.Case(
                case["name"],
                "power",
                params={
                    "fault": p.get("fault", "normal"),
                    "valve_r": 14.4,
                    "valve_l": p.get("valve_l", 0.2),
                    "supply": p.get("supply", 12),
                    "max_step_s": p.get("step", 0.0001),
                },
            )
        )
        # Replace the old RL pump, retain a tiny numerical current probe.
        text = text.replace(
            "Rpump bus pumptop 20\nLpump pumptop pumpdrain 0.01",
            "* BLDC INPUT surrogate; capacitance/startup are ASSUMED.\n"
            f"Bpump bus pumptop I=(time<.18 ? {p.get('startup_A', 1.5)} : 1.5)*max(0,v(bus,pumpdrain))/(max(0,v(bus,pumpdrain))+1)\n"
            f"Lpump pumptop pumpdrain 1n\nCpumpinput bus pumpdrain {p.get('cap_u', 1)}u",
        )
        if "Rpump bus pumptop" in text:
            raise ValueError("Pump replacement did not match baseline generator")
        # Remove the valve-style fast reverse clamp from the BLDC input.
        text = text.replace(
            "Dpumpfly pumpdrain pumpz FLY\nDpumpz bus pumpz ZENER\n", "Dpumpfly pumpdrain bus FLY\n"
        )
        text = text.replace("Rpumpsense pumpsource 0 .05", "Rpumpsense pumpsource 0 .1")
        text = text.replace("Rvalvesense valvesource 0 .05", "Rvalvesense valvesource 0 .1")
        text = text.replace(
            "v(pumpsource)>.2 || v(valvesource)>.2", "v(pumpsource)>.25 || v(valvesource)>.25"
        )
        text = text.replace("BV=20 IBV=1m", "BV=28.5 IBV=1m")
        text = text.replace(
            "v(pumpsource) v(valvesource)\n", "v(pumpsource) v(valvesource) v(bus,pumpdrain)\n"
        )
        return text, 1.4
    if family == "loop":
        current = p.get("current", 0.02)
        r = p.get("burden", 100)
        rail = p.get("rail", 3.3)
        off = p.get("off", False)
        isolated = p.get("isolated", True)
        rail_expr = f"PWL(0 {rail} .01 {rail} .010001 0 .04 0)" if off else str(rail)
        # 11V minimum from Nishka PDF, MAX14626 45ohm max plus assumed
        # 10ohm wiring. Limit 33mA is its upper DC bound, not transient proof.
        limit = p.get("limit", 0.033)
        body = f"""CertaRig stocked-product loop envelope: {case["name"]}
* Bounded equivalents, not a SEN0262 or MAX14626 vendor macromodel.
* 120ohm cases examine the SEN0262 burden INPUT, not its TP5551 output.
Vloop loop 0 {p.get("supply", 24)}
Btx loop raw I=min(min({current},{limit}),max(0,(v(loop)-v(raw)-11)/55))
Rburden raw 0 {r}
Vrail rail 0 {rail_expr}
"""
        if isolated:
            body += """
* Candidate 100ohm receiver: 10k series, bounded 2.5V shunt clamp,
* TMUX1511 4.5ohm ON envelope, 2uA conservative OFF leakage.
* Reference/diodes/PG implementation and power-off timing remain unselected.
Rseries raw pre 10k
Vinst inst 0 5
Rbias inst ref 1k
Dref 0 ref REFERENCE
.model REFERENCE D(Is=1p N=1 Rs=.8 BV=2.5 IBV=80u)
Dupper pre ref CLAMP
Dlower 0 pre CLAMP
.model CLAMP D(Is=1e-7 N=1.05 Rs=.5 Cjo=10p)
Ben en 0 V=(v(rail)>3 ? 5 : 0)
Smux pre pin en 0 MUX
.model MUX SW(Ron=4.5 Roff=1e12 Vt=2.5 Vh=.05)
Boff 0 pin I=(v(en)<2.5 ? 2u : 0)
Rdis pin 0 33k
Cpin pin 0 10p
"""
        else:
            body += "Rdirect raw pin 100\nCpin pin 0 10p\n"
        body += f"""
Radc pin 0 6Meg
Dhi pin rail ESD
Dlo 0 pin ESD
.model ESD D(Is=1p N=1.3 Rs=10 Cjo=4p)
Bhead head 0 V=v(loop)-v(raw)-11-abs(i(Vloop))*55
Bpower power 0 V=v(raw)*v(raw)/{r}
"""
        return finish(
            body, "v(raw) v(pin) v(rail) v(head) v(power) i(Vrail) i(Vloop)", 0.04, p.get("step", 2e-6)
        ), 0.04
    if family == "thermal_driver":
        amps = p["amps"]
        rdson = p.get("rdson", 0.565)
        theta = p.get("theta", 41.1)
        # T rise is a physical RC analog; Cth is assumed and only steady
        # behavior is assessed. Rtheta is TI's test PCB, not this module.
        body = f"""DRV8871 steady conduction / thermal analogy: {case["name"]}
Vbus bus 0 12
Rbridge bus load {rdson}
Iload load 0 {amps}
Bheat 0 trise I=i(Vbus)*i(Vbus)*{rdson}
Rtheta trise 0 {theta}
Cthermal trise 0 .02 IC=0
Bjunction tj 0 V={p.get("ambient", 40)}+v(trise)
"""
        return finish(body, "v(load) v(tj) i(Vbus)", 15, 0.01), 15
    if family == "pump_input":
        # Two-wire BLDC input equivalent: capacitor plus bounded demand.
        # No motor-phase inductance, internal control, commutation or reverse
        # voltage limit is claimed. Startup factors are explicit assumptions.
        amps = p.get("amps", 1.5)
        startup = p.get("startup", 1)
        cap = p.get("cap_u", 100)
        body = f"""TOPSFLO B12 electrical INPUT envelope: {case["name"]}
Vsource source 0 {p.get("supply", 12)}
Rwire source bus {p.get("source_r", 0.3)}
Cbus bus 0 {cap}u IC=0
Bload bus 0 I=(time<.005 ? 0 : (time<.055 ? {amps * startup} : {amps}))*max(0,v(bus))/(max(0,v(bus))+.01)
"""
        return finish(body, "v(bus) i(Vsource)", 0.15, p.get("step", 1e-5)), 0.15
    raise ValueError(f"Unknown family {family}")


def scenarios():
    cases = []

    def add(name, family, params, unsafe=False, reason=""):
        cases.append(
            dict(
                name=name,
                family=family,
                params=params,
                expected="reject" if unsafe else "within_envelope",
                reason=reason,
            )
        )

    for current in [0.004, 0.012, 0.020, 0.024, 0.033]:
        add(f"protected_100R_{current * 1000:g}mA", "loop", {"current": current})
    for supply in [21.6, 26.4]:
        for burden in [99.9, 100.1]:
            add(f"protected_{supply:g}V_{burden:g}R", "loop", dict(supply=supply, burden=burden, rail=3.135))
    add("protected_pi_poweroff", "loop", dict(off=True))
    add("protected_pi_poweroff_refined", "loop", dict(off=True, step=5e-7))
    add("sen0262_burden_normal20mA", "loop", dict(burden=120, isolated=False))
    add(
        "sen0262_burden_33mA_fault",
        "loop",
        dict(burden=120, isolated=False, current=0.033),
        True,
        "120ohm input can exceed the 3.3V domain; TP5551 clipping/protection is not modeled",
    )
    add(
        "unprotected_receiver_pi_off",
        "loop",
        dict(burden=120, isolated=False, off=True),
        True,
        "Burden connected to unpowered ADC injects current; not a full SEN0262 board model",
    )
    add(
        "nishka_12V_insufficient_compliance",
        "loop",
        dict(supply=12),
        True,
        "11V transmitter minimum plus receiver/protector burden prevents 20mA",
    )
    add(
        "missing_burden_protected",
        "loop",
        dict(burden=1e9),
        True,
        "Input clamp limits voltage but sensor cannot produce the requested full-scale current",
    )
    for amps in [0.84, 1.38, 1.5]:
        add(f"drv8871_{amps:g}A_TI_testPCB", "thermal_driver", dict(amps=amps))
    add(
        "drv8871_3.6A_continuous_claim",
        "thermal_driver",
        dict(amps=3.6),
        True,
        "TI specifies peak current; sustained conduction exceeds recommended junction envelope",
    )
    add(
        "drv8871_1.5A_hot_board_bound",
        "thermal_driver",
        dict(amps=1.5, rdson=0.96, theta=65, ambient=50),
        True,
        "Assumed hot resistance / poorer PCB thermal path; actual module cooling unqualified",
    )
    for supply in [10.8, 12, 13.2]:
        for startup in [1, 2, 3]:
            add(f"pump_input_{supply:g}V_start{startup}x", "pump_input", dict(supply=supply, startup=startup))
    add(
        "pump_weak_supply_startup",
        "pump_input",
        dict(supply=10.8, startup=3, source_r=1.2),
        True,
        "Assumed high source impedance / startup demand drops below manufacturer operating minimum",
    )
    add("pump_input_refined", "pump_input", dict(supply=10.8, startup=3, step=2e-6))
    for fault in ["normal", "estop", "estop_reset_held", "heartbeat_loss"]:
        add("integrated_" + fault, "integrated", dict(fault=fault))
    add("integrated_estop_refined", "integrated", dict(fault="estop", step=0.00002))
    add("integrated_valve_L_corner", "integrated", dict(fault="estop", valve_l=0.5, supply=13.2))
    add(
        "integrated_unknown_startup_trip",
        "integrated",
        dict(startup_A=3, cap_u=100),
        True,
        "Assumed 2x startup/100uF trips the 2.5A latch before running; actual pump inrush is unknown",
    )
    return cases


def assess(case, rows):
    checks = {}
    p = case["params"]
    if case["family"] == "integrated":
        old = baseline.assess(baseline.Case(case["name"], "power", params=case["params"]), [], rows)
        checks = {c["check"]: c["passed"] for c in old["checks"]}
        checks["BLDC_reverse_above_assumed_minus1V"] = min(r[17] for r in rows) >= -1
        metrics = {
            **old["metrics"],
            "pump_terminal_min_V": min(r[17] for r in rows),
            "pump_terminal_max_V": max(r[17] for r in rows),
            "trip_latch_max_V": max(r[14] for r in rows),
        }
    elif case["family"] == "loop":
        tail = [r for r in rows if r[0] > 0.035]
        off = p.get("off", False)
        checks["ADC_or_120R_input_within_rail_plus_0.3V"] = all(-0.3 <= r[2] <= r[3] + 0.3 for r in rows)
        if not p.get("isolated", True):
            # ADC loading can clamp the pin while the actual unbuffered burden
            # is too high for the input of a 3.3V-powered buffer.
            checks["burden_input_within_3.6V"] = max(r[1] for r in rows) <= 3.6
        checks["burden_below_half_watt"] = max(r[5] for r in rows) < 0.5
        requested = min(p.get("current", 0.02), p.get("limit", 0.033))
        checks["transmitter_reaches_requested_current"] = abs(abs(rows[-1][7]) - requested) <= 5e-5
        if off:
            checks["off_ADC_discharged"] = max(r[2] for r in tail) < 0.15
            checks["off_injection_below_1uA"] = max(abs(r[6]) for r in tail) < 1e-6
        metrics = dict(
            raw_max_V=max(r[1] for r in rows),
            pin_max_V=max(r[2] for r in rows),
            final_current_mA=abs(rows[-1][7]) * 1000,
            burden_max_W=max(r[5] for r in rows),
            off_injection_A=max(abs(r[6]) for r in tail) if off else None,
        )
    elif case["family"] == "thermal_driver":
        checks["junction_below_125C_conservative_design_limit"] = max(r[2] for r in rows) <= 125
        checks["load_above_6V"] = min(r[1] for r in rows) >= 6
        metrics = dict(junction_max_C=max(r[2] for r in rows), load_min_V=min(r[1] for r in rows))
    else:
        operating = [r for r in rows if r[0] > 0.006]
        checks["input_6_to_18V"] = all(6 <= r[1] <= 18 for r in operating)
        # 5A supply is a candidate nameplate limit, not an asserted limiter.
        # Ignore capacitor startup to report pump-demand envelope separately.
        checks["steady_startup_demand_below_5A"] = max(abs(r[2]) for r in operating) <= 5
        metrics = dict(
            operating_input_min_V=min(r[1] for r in operating),
            operating_source_max_A=max(abs(r[2]) for r in operating),
            connection_inrush_peak_A=max(abs(r[2]) for r in rows),
        )
    return dict(checks=checks, metrics=metrics, criteria_pass=all(checks.values()))


def analytical():
    """Deterministic calculations, explicitly separate from circuit transients."""
    rows = []

    def item(name, value, unit, within, basis):
        rows.append(dict(name=name, value=value, unit=unit, within=within, basis=basis))

    for head in [3, 5, 6]:
        pressure = 998.2 * 9.80665 * head / 1e5
        item(
            f"shutoff_{head}m",
            pressure,
            "bar",
            pressure <= 1,
            "Hydrostatic conversion only; 3m original A12, 5m stocked sheet, 6m listing; not water hammer",
        )
    item(
        "0.2bar_sensor_at_6m",
        998.2 * 9.80665 * 6 / 1e5,
        "bar",
        False,
        "A 0-200mbar sensor would overrange before considering transients",
    )
    item("INA219_0.1ohm_range", 0.320 / 0.1, "A", True, "TI +/-320mV range / actual listed board shunt")
    item(
        "old_4A_threshold_voltage",
        4 * 0.1,
        "V",
        False,
        "0.4V exceeds +/-0.320V measurement range; replace old threshold or sensor design",
    )
    item(
        "candidate_2.5A_threshold_voltage",
        2.5 * 0.1,
        "V",
        True,
        "0.25V in range; candidate only, INA219/software is not independent fast OC protection",
    )
    item(
        "24V_plus10pct_INA219_bus",
        24 * 1.1,
        "V",
        False,
        "26.4V exceeds TI 26V common-mode recommended limit; do not measure instrument rail with INA219",
    )
    item(
        "Nishka_1bar_conservative_accuracy",
        0.005,
        "bar",
        True,
        "Use 0.5% FS listing claim conservatively; PDF says 0.5% reading, unresolved",
    )
    item(
        "Nishka_1bar_0.1bar_relative_error",
        0.005 / 0.1 * 100,
        "%",
        True,
        "5% of 0.1bar signal before ADC/calibration/reference uncertainty; not 0.5% system accuracy",
    )
    item("20mA_120ohm", 0.020 * 120, "V", True, "DFRobot SEN0262 published burden")
    item("33mA_120ohm", 0.033 * 120, "V", False, "3.96V burden exceeds 3.3V-domain budget")
    # Hydraulic steady network, *assumed* linear pump endpoint model and
    # pipe minor-loss coefficient K=6. This does NOT model a selected valve,
    # real bypass, pressure relief, air, cavitation or water hammer.
    for d in [0.008, 0.012]:

        def pipe_head(q_lmin, diameter=d):
            q = q_lmin / 60000
            velocity = q / (math.pi * diameter * diameter / 4)
            re = velocity * diameter / 1e-6
            f = 64 / max(re, 1) if re < 2300 else 0.3164 / re**0.25
            return (f * 2 / diameter + 6) * velocity * velocity / (2 * 9.80665)

        lo, hi = 0.0, 9.5
        for _ in range(70):
            q = (lo + hi) / 2
            if 6 * (1 - q / 9.5) > pipe_head(q):
                lo = q
            else:
                hi = q
        q = (lo + hi) / 2
        item(
            f"assumed_unrestricted_{d * 1000:g}mm_return",
            q,
            "L/min",
            None,
            "ASSUMED 6m/9.5Lmin straight-line pump curve, 2m tube, K=6; no selected-valve claim",
        )
    return rows


def manifest(root):
    files = sorted(
        p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS" and "__pycache__" not in p.parts
    )
    (root / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(root).as_posix() + "\n"
            for p in files
        )
    )


def run(root):
    root.mkdir(parents=True, exist_ok=True)
    engine = shutil.which("ngspice")
    if not engine:
        raise RuntimeError("ngspice required")
    results = []
    for case in scenarios():
        folder = root / "cases" / case["name"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "trace.dat").unlink(missing_ok=True)
        netlist, end = circuit(case)
        (folder / "circuit.cir").write_text(netlist)
        proc = subprocess.run(
            [engine, "-b", "circuit.cir"], cwd=folder, capture_output=True, text=True, timeout=40
        )
        log = proc.stdout + proc.stderr
        (folder / "ngspice.log").write_text(log)
        if proc.returncode or not (folder / "trace.dat").is_file():
            raise RuntimeError(f"Invalid simulation: {case['name']}")
        with (folder / "trace.dat").open() as stream:
            header = stream.readline().split()
            rows = [[float(x) for x in line.split()] for line in stream if line.strip()]
        if (
            not rows
            or rows[-1][0] < end - 1e-8
            or any(len(r) != len(header) or not all(math.isfinite(x) for x in r) for r in rows)
            or any(
                x in log.lower() for x in ["timestep too small", "transient analysis failed", "fatal error"]
            )
        ):
            raise RuntimeError(f"Incomplete/nonfinite/nonconverged simulation: {case['name']}")
        with gzip.open(folder / "trace.csv.gz", "wt", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        (folder / "trace.dat").unlink()
        result = {
            **case,
            **assess(case, rows),
            "samples": len(rows),
            "horizon_s": end,
            "netlist_sha256": hashlib.sha256(netlist.encode()).hexdigest(),
        }
        result["matched_expectation"] = result["criteria_pass"] == (case["expected"] == "within_envelope")
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(case["name"], result["matched_expectation"], flush=True)
    summary = dict(
        engine=subprocess.check_output([engine, "--version"], text=True).strip(),
        scope="Bounded DC/transient component envelopes; no complete assembly, hydraulic or functional safety qualification",
        procurement_release=False,
        physical_validation=False,
        results=results,
        analytical_checks=analytical(),
    )
    summary["all_experiments_match_expectation"] = all(r["matched_expectation"] for r in results)
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    shutil.copy2(__file__, root / "run_review.py")
    shutil.copy2(baseline.__file__, root / "run_spice.py")
    manifest(root)
    if not summary["all_experiments_match_expectation"]:
        raise SystemExit("An experiment did not match its declared expectation; inspect evidence")


def verify(root):
    entries = [line.split("  ", 1) for line in (root / "SHA256SUMS").read_text().splitlines() if line]
    names = {rel for _, rel in entries}
    if not {"summary.json", "run_review.py", "run_spice.py"}.issubset(names):
        raise ValueError("Incomplete manifest")
    for checksum, relative in entries:
        p = (root / relative).resolve()
        if (
            not p.is_relative_to(root.resolve())
            or not p.is_file()
            or hashlib.sha256(p.read_bytes()).hexdigest() != checksum
        ):
            raise ValueError(f"Missing/corrupt evidence: {relative}")
    summary = json.loads((root / "summary.json").read_text())
    expected = scenarios()
    if len(expected) != len(summary["results"]):
        raise ValueError("Incomplete scenario matrix")
    for case, saved in zip(expected, summary["results"], strict=True):
        folder = root / "cases" / case["name"]
        required = {
            f"cases/{case['name']}/{f}" for f in ["circuit.cir", "ngspice.log", "trace.csv.gz", "result.json"]
        }
        if not required.issubset(names):
            raise ValueError("Incomplete required case manifest")
        if any(saved[k] != case[k] for k in case):
            raise ValueError("Scenario identity mismatch")
        generated, end = circuit(case)
        if (folder / "circuit.cir").read_text() != generated:
            raise ValueError("Netlist identity mismatch")
        with gzip.open(folder / "trace.csv.gz", "rt") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            rows = [[float(x) for x in r] for r in reader]
        if (
            not rows
            or len(rows) != saved["samples"]
            or rows[-1][0] < end - 1e-8
            or any(len(r) != len(header) or not all(math.isfinite(x) for x in r) for r in rows)
        ):
            raise ValueError("Invalid trace")
        replay = assess(case, rows)
        if any(replay[k] != saved[k] for k in replay):
            raise ValueError("Sample replay mismatch")
        if not saved["matched_expectation"] or saved["criteria_pass"] != (
            case["expected"] == "within_envelope"
        ):
            raise ValueError("Unexpected circuit result")
    if analytical() != summary["analytical_checks"]:
        raise ValueError("Analytical replay mismatch")
    print(f"VERIFIED {len(expected)} circuit experiments and {len(analytical())} calculations")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "verify", "manifest"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"run": run, "verify": verify, "manifest": manifest}[args.mode](args.root.resolve())
