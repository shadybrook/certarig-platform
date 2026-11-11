"""Paired mitigations for eight procurement-review rejections, simulation only.

Keeps the original unsafe controls intact. Revised criteria distinguish a healthy
measurement from a contained fault that must remain refused. No equipment I/O.
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
from pathlib import Path

import run_review as review


def cases():
    result = []

    def add(name, family, params, original="", outcome="normal"):
        result.append(dict(name=name, family=family, params=params, original=original, outcome=outcome))

    add("receiver_33mA_contained_refusal", "loop", dict(current=0.033), "sen0262_burden_33mA_fault", "refuse")
    add("receiver_pi_off_isolated", "loop", dict(off=True), "unprotected_receiver_pi_off", "power_off")
    add("receiver_24V_fullscale", "loop", dict(supply=24), "nishka_12V_insufficient_compliance")
    add("receiver_burden_open_refused", "loop", dict(burden=1e9), "missing_burden_protected", "refuse")
    add("receiver_repaired_requalified", "loop", dict(supply=24))
    for supply in [21.6, 26.4]:
        add(f"receiver_fullscale_{supply}V", "loop", dict(supply=supply))
    for current in [0.004, 0.012, 0.020]:
        add(f"receiver_calibrated_{current * 1000:g}mA", "loop", dict(current=current))
    # Rds=0.154 is an explicit 2x hot bound on Vishay IRL540 0.077ohm
    # at 5V gate. 20C/W is a REQUIRED mounted thermal path, not a board claim.
    add(
        "unidirectional_stage_3.6A_thermal",
        "thermal_driver",
        dict(amps=3.6, rdson=0.154, theta=20, ambient=50),
        "drv8871_3.6A_continuous_claim",
    )
    add(
        "unidirectional_stage_hot_1.5A",
        "thermal_driver",
        dict(amps=1.5, rdson=0.154, theta=20, ambient=50),
        "drv8871_1.5A_hot_board_bound",
    )
    add(
        "supply_10.8V_0.3ohm_3x_start",
        "pump_input",
        dict(supply=10.8, startup=3, source_r=0.3),
        "pump_weak_supply_startup",
    )
    add("softstart_3A_100uF", "start_power", dict(), "integrated_unknown_startup_trip")
    add("softstart_low_supply", "start_power", dict(supply=10.8, limit=3.68))
    add("softstart_high_supply_large_cap", "start_power", dict(supply=13.2, cap_u=1000, limit=4.32))
    add(
        "softstart_weak_source_refused",
        "start_power",
        dict(supply=10.8, source_r=1.2, start_A=4.5),
        outcome="fault",
    )
    add("persistent_overload_latches", "start_power", dict(fault="overload"), outcome="fault")
    add(
        "overload_high_supply_limit_corner",
        "start_power",
        dict(fault="overload", supply=13.2, limit=4.32),
        outcome="fault",
    )
    add("shorted_output_latches", "start_power", dict(fault="short"), outcome="fault")
    add("estop_no_automatic_restart", "start_power", dict(fault="estop"), outcome="fault")
    add("estop_large_output_cap", "start_power", dict(fault="estop", cap_u=1000), outcome="fault")
    add("softstart_refined", "start_power", dict(step=2e-6))
    return result


def circuit(case):
    p = case["params"]
    if case["family"] != "start_power":
        return review.circuit(case)
    supply = p.get("supply", 12)
    start = p.get("start_A", 3)
    fault = p.get("fault", "")
    stop = "PWL(0 5 .09 5 .09001 0 .12 0 .12001 5 .3 5)" if fault == "estop" else "5"
    # eFuse is a behavioral envelope inspired by TPS25940L features. It is
    # NOT that vendor macromodel and does not establish SOA/thermal immunity.
    body = f"""CertaRig revised startup envelope: {case["name"]}
* Unidirectional current-limited supply with 10ms target ramp.
* 4A +/-8% limit, 5A fast veto, 2.5A/80ms sustained-overload timer.
* 50milliohm pump shunt / recalibration required; stock R100 is not this circuit.
Vsource source 0 {supply}
* Total source/wiring/contact/shunt impedance, not adapter resistance alone.
Rsource source vin {p.get("source_r", 0.3)}
* Input rail has settled before permit. Hot-plug/supply-rise is not qualified.
Cinput vin 0 10u IC={supply}
Vpermit permit 0 PWL(0 0 .02 0 .02001 5 .18 5 .18001 0 .22 0 .22001 5 .30 5)
Vestop estop 0 {stop}
Ctrip trip 0 1u IC=0
Rtrip trip 0 1e12
Bover over 0 V=(i(Vsense)>2.5 ? 5 : 0)
Rover over timer 115.416k
Ctimer timer 0 1u IC=0
* Persistent low output or excessive supply sag is a hard refusal, not a
* timer that grants permission. Startup fault-energy/SOA remains a hold.
Btrip trip 0 I=(v(trip)>2.5 || v(estop)<2.5 || i(Vsense)>5 || v(timer)>2.5 || (v(elapsed)>.03 && v(permit)>2.5 && (v(out)<6 || v(vin)<8)) || (v(elapsed)>.01 && v(out)<1) ? (v(trip)-5)/100 : 0)
Ben enabled 0 V=(v(permit)>2.5 && v(trip)<2.5 && v(estop)>2.5 ? 5 : 0)
Belapsed 0 elapsed I=(v(enabled)>2.5 ? .001 : -v(elapsed)/1)
Celapsed elapsed 0 .001 IC=0
Relapsed elapsed 0 1e12
* RC rise is the bounded soft-start equivalent. Fast discharge tracks veto.
Bramp 0 ramp I=(v(enabled)>2.5 ? min(.001,max(0,(1-v(ramp))/.1)) : -v(ramp)/1)
Cramp ramp 0 10u IC=0
Rramp ramp 0 1e12
Btarget target 0 V=max(0,v(vin))*min(1,max(0,v(ramp)))
Bpass vin sensed I=(v(enabled)>2.5 ? min({p.get("limit", 4)},max(0,(v(target)-v(out))/.05)) : 0)
Vsense sensed out 0
Cout out 0 {p.get("cap_u", 100)}u IC=0
Rbleed out 0 1000
* Actively discharge stored output energy when disabled; requires actual
* transistor/resistor pulse-energy selection and reverse/backfeed review.
Bdischarge out 0 I=(v(enabled)<2.5 ? v(out)/47 : 0)
Bpump out 0 I=(v(elapsed)<.06 ? {start} : {4 if fault == "overload" else 1.5})*(1+tanh((v(out)-5.8)/.25))/2
* Valve opens after pump startup and uses an independent load stage.
Bvalve vin 0 I=(v(elapsed)>.08 && v(enabled)>2.5 && v(over)<2.5 ? v(vin)/14.4 : 0)
Bshunt shunt 0 V=i(Vsense)*.05
Befusepower stress 0 V=max(0,v(vin,out)*i(Vsense))
"""
    if fault == "short":
        body += "Rshort out 0 .05\n"
    return review.finish(
        body,
        "v(out) i(Vsource) v(trip) v(enabled) i(Vsense) v(shunt) v(stress) v(timer)",
        0.30,
        p.get("step", 1e-5),
    ).replace(
        f"tran {p.get('step', 1e-5)} 0.3 0 {p.get('step', 1e-5)}",
        f"tran {p.get('step', 1e-5)} 0.3 0 {p.get('step', 1e-5)} uic",
    ), 0.30


def current_from_adc(volts):
    # Full nominal divider/loading model, not Vpin/100. Component tolerances
    # and actual ADS1115 gain must enter the physical calibration record.
    tail = 1 / (1 / 33000 + 1 / 6e6)
    series = 10000 + 4.5
    burden = 1 / (1 / 100 + 1 / (series + tail))
    return volts / (burden * tail / (series + tail))


def guard_exercise(healthy, invalid):
    """Offline reference guard, NOT integrated into the deployed Edge runtime."""
    latched = False
    allowed = []
    for value, reset in [(healthy, False), (invalid, False), (healthy, False), (healthy, True)]:
        valid = math.isfinite(value) and 0.0036 <= value <= 0.021
        if not valid:
            latched = True
        elif reset:
            latched = False
        allowed.append(valid and not latched)
    return allowed


def assess(case, rows):
    if case["family"] != "start_power":
        old = review.assess(case, rows)
        checks = dict(old["checks"])
        metrics = dict(old["metrics"])
        if case["family"] == "loop":
            observed = current_from_adc(rows[-1][2])
            valid = 0.0036 <= observed <= 0.021 and not case["params"].get("off", False)
            metrics.update(inferred_current_A=observed, observation_valid=valid)
            if case["outcome"] in {"refuse", "power_off"}:
                # This criterion still fails for the broken original circuit;
                # do not relabel its requested-current requirement as passed.
                checks.pop("transmitter_reaches_requested_current", None)
                checks["invalid_observation_refuses_authority"] = not valid
                exercise = guard_exercise(0.012, observed if not valid else float("nan"))
                if case["outcome"] == "power_off":
                    exercise = guard_exercise(0.012, float("nan"))
                checks["recovery_requires_explicit_reset"] = exercise == [True, False, False, True]
                metrics["reference_guard_sequence"] = exercise
            else:
                checks["valid_calibrated_reading"] = (
                    valid and abs(observed - case["params"].get("current", 0.02)) < 1e-4
                )
        return dict(checks=checks, metrics=metrics, passed=all(checks.values()))
    fault = case["outcome"] == "fault"
    operating = [r for r in rows if 0.055 < r[0] < 0.075]
    late = [r for r in rows if 0.25 < r[0] < 0.29]
    checks = dict(
        measured_pump_shunt_in_range=max(abs(r[6]) for r in rows) < 0.320,
        source_within_5A=max(abs(r[2]) for r in rows) < 5,
        actuator_voltage_below_18V=max(r[1] for r in rows) < 18,
        peak_current_limited=max(r[5] for r in rows) <= case["params"].get("limit", 4) + 0.01,
    )
    if fault:
        checks["fault_latches"] = max(r[3] for r in rows) > 4
        checks["permit_retry_does_not_restart"] = (
            max(r[4] for r in late) < 0.1 and max(r[1] for r in late) < 1
        )
    else:
        checks["startup_above_6V"] = min(r[1] for r in operating) > 6
        checks["no_spurious_trip"] = max(r[3] for r in rows) < 0.1
        checks["steady_after_startup"] = min(r[1] for r in rows if 0.12 < r[0] < 0.16) > 8
    # Stress is reported, not accepted against invented silicon SOA.
    energy = sum((b[0] - a[0]) * (a[7] + b[7]) / 2 for a, b in zip(rows, rows[1:], strict=False))
    metrics = dict(
        supply_peak_A=max(abs(r[2]) for r in rows),
        pump_peak_A=max(r[5] for r in rows),
        pump_shunt_peak_V=max(abs(r[6]) for r in rows),
        trip_peak_V=max(r[3] for r in rows),
        start_output_min_V=min(r[1] for r in operating),
        efuse_energy_J=energy,
        silicon_SOA_qualified=False,
    )
    return dict(checks=checks, metrics=metrics, passed=all(checks.values()))


def original_controls():
    return [c for c in review.scenarios() if c["expected"] == "reject"]


def run(root):
    root.mkdir(parents=True, exist_ok=True)
    engine = shutil.which("ngspice")
    if not engine:
        raise RuntimeError("ngspice required")
    experiments = [(c, True) for c in original_controls()] + [(c, False) for c in cases()]
    results = []
    for case, original in experiments:
        folder = root / "cases" / case["name"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "trace.dat").unlink(missing_ok=True)
        text, end = review.circuit(case) if original else circuit(case)
        (folder / "circuit.cir").write_text(text)
        proc = subprocess.run(
            [engine, "-b", "circuit.cir"], cwd=folder, capture_output=True, text=True, timeout=40
        )
        log = proc.stdout + proc.stderr
        (folder / "ngspice.log").write_text(log)
        if proc.returncode or not (folder / "trace.dat").is_file():
            raise RuntimeError(f"Invalid simulation {case['name']}")
        with (folder / "trace.dat").open() as stream:
            header = stream.readline().split()
            rows = [[float(x) for x in line.split()] for line in stream if line.strip()]
        if (
            not rows
            or rows[-1][0] < end - 1e-8
            or any(len(r) != len(header) or not all(math.isfinite(v) for v in r) for r in rows)
            or any(
                t in log.lower() for t in ["timestep too small", "transient analysis failed", "fatal error"]
            )
        ):
            raise RuntimeError(f"Incomplete/nonfinite simulation {case['name']}")
        with gzip.open(folder / "trace.csv.gz", "wt", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)
        (folder / "trace.dat").unlink()
        assessment = review.assess(case, rows) if original else assess(case, rows)
        result = dict(
            case=case,
            original_control=original,
            assessment=assessment,
            samples=len(rows),
            horizon_s=end,
            netlist_sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        result["experiment_ok"] = (not assessment["criteria_pass"]) if original else assessment["passed"]
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(case["name"], result["experiment_ok"], flush=True)
    summary = dict(
        engine=subprocess.check_output([engine, "--version"], text=True).strip(),
        results=results,
        all_experiments_ok=all(r["experiment_ok"] for r in results),
        physical_qualification=False,
        procurement_release=False,
        application_integration=False,
        scope="Paired design envelopes and reference refusal guards, not a vendor macromodel or complete construction design",
    )
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    for path in [Path(__file__), Path(review.__file__), Path(review.baseline.__file__)]:
        shutil.copy2(path, root / path.name)
    review.manifest(root)
    if not summary["all_experiments_ok"]:
        raise SystemExit("A declared mitigation failed: inspect the saved evidence")


def verify(root):
    entries = [line.split("  ", 1) for line in (root / "SHA256SUMS").read_text().splitlines() if line]
    names = {r for _, r in entries}
    if not {"summary.json", "run_closure.py", "run_review.py", "run_spice.py"}.issubset(names):
        raise ValueError("Incomplete manifest")
    for digest, relative in entries:
        p = (root / relative).resolve()
        if (
            not p.is_relative_to(root.resolve())
            or not p.is_file()
            or hashlib.sha256(p.read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"Missing/corrupt evidence: {relative}")
    summary = json.loads((root / "summary.json").read_text())
    declared = [(c, True) for c in original_controls()] + [(c, False) for c in cases()]
    if len(declared) != len(summary["results"]):
        raise ValueError("Incomplete case set")
    for (case, original), saved in zip(declared, summary["results"], strict=True):
        folder = root / "cases" / case["name"]
        if saved["case"] != case or saved["original_control"] != original:
            raise ValueError("Case identity mismatch")
        required = {
            f"cases/{case['name']}/{n}" for n in ["circuit.cir", "result.json", "trace.csv.gz", "ngspice.log"]
        }
        if not required.issubset(names):
            raise ValueError("Missing case entries")
        netlist, end = review.circuit(case) if original else circuit(case)
        if (folder / "circuit.cir").read_text() != netlist:
            raise ValueError("Netlist mismatch")
        with gzip.open(folder / "trace.csv.gz", "rt") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            rows = [[float(x) for x in r] for r in reader]
        if (
            not rows
            or len(rows) != saved["samples"]
            or rows[-1][0] < end - 1e-8
            or any(len(r) != len(header) or not all(math.isfinite(v) for v in r) for r in rows)
        ):
            raise ValueError("Incomplete/nonfinite trace")
        replay = review.assess(case, rows) if original else assess(case, rows)
        if replay != saved["assessment"] or not saved["experiment_ok"]:
            raise ValueError("Replay or experiment failed")
    print(f"VERIFIED {len(declared)} paired controls and mitigation experiments")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "verify"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"run": run, "verify": verify}[args.mode](args.root.resolve())
