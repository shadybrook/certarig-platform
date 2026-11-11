"""Reproducible electrical design experiments, not physical qualification.

Only Python stdlib and the ngspice executable are required. All IC models are
explicit bounded behavioral equivalents, not manufacturer-certified macromodels.
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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Case:
    name: str
    family: str
    revision: str = "R1"
    params: dict[str, Any] = field(default_factory=dict)
    diagnostic: bool = False


def pwl(points):
    return "PWL(" + " ".join(f"{t:.9g} {v:.9g}" for t, v in points) + ")"


def pulses(ends=1.4, stop=10):
    points = [(0, 0)]
    t = 0.005
    value = 0
    while t < ends and t < stop:
        points.extend([(t, value), (t + 0.0001, 3.3 - value)])
        value = 3.3 - value
        t += 0.01
    points.append((ends, value))
    return pwl(points)


MODELS = """
.model CONTACT SW(Ron=.03 Roff=1e10 Vt=2.5 Vh=.1)
.model MOS SW(Ron=.10 Roff=1e10 Vt=2.5 Vh=.1)
.model FLY D(Is=1n Rs=.05 N=1.5 Cjo=50p BV=100)
.model ZENER D(Is=1p Rs=.2 N=1 BV=20 IBV=1m Cjo=30p)
.model AVAL D(Is=1p Rs=.1 N=1 BV=100 IBV=1m Cjo=30p)
.model LED D(Is=1e-20 N=1.8 Rs=5 Cjo=20p)
.model REV D(Is=1n N=1.2 Rs=.05)
"""


def power(case):
    p = case.params
    rev = case.revision
    supply = p.get("supply", 12)
    res = p.get("valve_r", 24)
    ind = p.get("valve_l", 0.2)
    permit = [(0, 0), (0.12, 0), (0.1201, 3.3), (0.60, 3.3), (0.6001, 0), (1.4, 0)]
    reset = [(0, 0), (0.05, 0), (0.0501, 3.3), (0.07, 3.3), (0.0701, 0), (1.4, 0)]
    estop = [(0, 5), (1.4, 5)]
    adc = [(0, 0), (0.002, 3.3), (1.4, 3.3)]
    aux = [(0, 0), (0.002, 5), (1.4, 5)]
    kind = p.get("fault", "normal")
    if kind in {"estop", "estop_reset_held", "estop_release_high"}:
        permit = [(0, 0), (0.12, 0), (0.1201, 3.3), (1.4, 3.3)]
        estop = [(0, 5), (0.35, 5), (0.3501, 0), (0.5, 0), (0.5001, 5), (1.4, 5)]
    if kind == "estop_reset_held":
        reset = [(0, 0), (0.05, 0), (0.0501, 3.3), (1.4, 3.3)]
        permit = [
            (0, 0),
            (0.12, 0),
            (0.1201, 3.3),
            (0.4, 3.3),
            (0.4001, 0),
            (0.7, 0),
            (0.7001, 3.3),
            (1.4, 3.3),
        ]
    if kind == "rearm":
        estop = [(0, 5), (0.35, 5), (0.3501, 0), (0.5, 0), (0.5001, 5), (1.4, 5)]
        reset = [
            (0, 0),
            (0.05, 0),
            (0.0501, 3.3),
            (0.07, 3.3),
            (0.0701, 0),
            (0.65, 0),
            (0.6501, 3.3),
            (0.67, 3.3),
            (0.6701, 0),
            (1.4, 0),
        ]
        permit = [
            (0, 0),
            (0.12, 0),
            (0.1201, 3.3),
            (0.55, 3.3),
            (0.5501, 0),
            (0.75, 0),
            (0.7501, 3.3),
            (1.1, 3.3),
            (1.1001, 0),
            (1.4, 0),
        ]
    if kind in {
        "heartbeat_loss",
        "heartbeat_missing",
        "brownout",
        "logic_loss",
        "stuck_command",
        "feedback_broken",
    }:
        permit = [(0, 0), (0.12, 0), (0.1201, 3.3), (1.4, 3.3)]
    if kind == "brownout":
        adc = [(0, 0), (0.002, 3.3), (0.35, 3.3), (0.351, 2.7), (0.5, 2.7), (0.501, 3.3), (1.4, 3.3)]
    if kind == "logic_loss":
        aux = [(0, 0), (0.002, 5), (0.35, 5), (0.351, 0), (0.5, 0), (0.501, 5), (1.4, 5)]
    if kind == "stuck_command":
        permit = [(0, 3.3), (1.4, 3.3)]
    hb_stop = (
        0 if kind == "heartbeat_missing" else 0.35 if kind in {"heartbeat_loss", "stuck_command"} else 10
    )
    tau = p.get("watchdog_s", 0.2) / math.log(2)
    # The watcher's first-edge qualification, timer, latch and reset-edge memory
    # are actual RC state in SPICE, not precomputed expected response waveforms.
    circuit = f"""CertaRig {case.name}: bounded functional power stage {rev}
* 12V Thevenin supply with 0.3 ohm source/wiring; no SMPS current limit assumed.
V12 source 0 {pwl([(0, 0), (0.005, supply), (1.4, supply)])}
Rsrc source raw .3
Craw raw 0 10u
Vaux aux 0 {pwl(aux)}
Vadc adcrail 0 {pwl(adc)}
Vestop estop 0 {pwl(estop)}
Vpermit permit 0 {pwl(permit)}
Vreset reset 0 {pwl(reset)}
Vhb hb 0 {pulses(stop=hb_stop)}
Rpgfilter raw pgfiltered 10k
Cpgfilter pgfiltered 0 10n
Bpg pg 0 V=(v(aux)>4.5 && v(adcrail)>3.0 && v(pgfiltered)>10.0 ? 5 : 0)
Rhblag hb hblag 1k
Chblag hblag 0 100n
Bedge edge 0 V=(abs(v(hb)-v(hblag))>.5 ? 5 : 0)
Rwd aux wd 288.539k
Cwd wd 0 {tau / 288539:.12g} IC=0
Bwdreset wd 0 I=(v(edge)>2.5 ? v(wd)/10 : 0)
Cseen seen 0 10n IC=0
Rseen seen 0 1e10
Bseen seen 0 I=(v(aux)<4.5 ? v(seen)/100 : (v(edge)>2.5 ? (v(seen)-5)/100 : 0))
Bwdok wdok 0 V=(v(seen)>2.5 && v(wd)<2.5 && v(aux)>4.5 ? 5 : 0)
Rreset reset resetlag 1k
Creset resetlag 0 1u
Bresetedge resetedge 0 V=(v(reset)-v(resetlag)>.5 ? 5 : 0)
Carm arm 0 1u IC=0
Rarm arm 0 1e10
"""
    if rev == "UNPROTECTED":
        circuit += "Barm arm 0 I=(v(estop)<2.5 ? v(arm)/100 : (v(arm)-5)/100)\n"
    else:
        circuit += "Barm arm 0 I=(v(estop)<2.5 || v(pg)<2.5 || v(wdok)<2.5 || v(itrip)>2.5 ? v(arm)/100 : (v(resetedge)>2.5 && v(permit)<.5 ? (v(arm)-5)/100 : 0))\n"
    circuit += """Bdrive drive 0 V=(v(arm)>2.5 && v(permit)>2.4 && v(aux)>4.5 ? 5 : 0)
Rkdelay drive kdelay 10k
Ckdelay kdelay 0 1.5u
Barmbuffer armcmd 0 V=(v(arm)>2.5 ? 5 : 0)
Rk0 armcmd k0delay 10k
Ck0 k0delay 0 1.5u
Sestop raw mid k0delay 0 CONTACT
* Continuous conductance transition avoids an ideal-contact discontinuity.
Bmaster mid bus I=v(mid,bus)*(1e-10+(1/.03-1e-10)*(1+tanh((v(kdelay)-2.5)/.1))/2)
Cmaster mid bus 100p
Cestop raw mid 100p
Rbleed bus 0 10k
Cbus bus 0 10u
Rdriver drive gatein 50
Rgate gatein gate 100
Rpulldown gate 0 47k
Cgate gate 0 3n
"""
    if rev == "UNPROTECTED":
        circuit += "Rmaster_bypass mid bus .001\n"
    if p.get("master_welded"):
        circuit += "Rweld mid bus .001\n"
    for load, r, inductance in [("pump", p.get("pump_r", 20), p.get("pump_l", 0.01)), ("valve", res, ind)]:
        if p.get("open_load") == load:
            r = 1e9
        if p.get("short_load") == load:
            r = 0.05
            inductance = 0.0001
        circuit += f"R{load} bus {load}top {r}\nL{load} {load}top {load}drain {inductance}\n"
        circuit += f"S{load} {load}drain {load}source gate 0 MOS\nC{load}oss {load}drain {load}source 1n\nR{load}sense {load}source 0 .05\n"
        if p.get("mos_short") == load:
            circuit += f"R{load}short {load}drain {load}source .001\n"
        if not p.get("no_suppression"):
            # Opposed diode+avalanche suppressor across coil: release energy is
            # measured; no mechanical position/time is inferred.
            circuit += f"D{load}fly {load}drain {load}z FLY\nD{load}z bus {load}z ZENER\n"
        circuit += f"D{load}av 0 {load}drain AVAL\n"
    circuit += """Citrip itrip 0 1u IC=0
Ritrip itrip 0 1e10
Bitrip itrip 0 I=(v(itrip)>2.5 || v(pumpsource)>.2 || v(valvesource)>.2 ? (v(itrip)-5)/100 : (v(resetedge)>2.5 && v(permit)<.5 ? v(itrip)/100 : 0))
* Fast OC veto exists independently of slow relay contact motion.
Bocgate gatein 0 I=(v(itrip)>2.5 ? v(gatein)/.1 : 0)
* Actual isolated voltage-feedback interface: current-limited optocoupler LED,
* reverse LED diode, bounded CTR equivalent and local 3.3V pullup.
Rled bus ledtop 1.8k
Vledsense ledtop led 0
Dled led 0 LED
Dledreverse 0 led REV
Rfb adcrail feedback 10k
Cfb feedback 0 1n
"""
    ctr = 0 if kind == "feedback_broken" else p.get("ctr", 0.2)
    circuit += (
        f"Bphoto feedback 0 I={ctr}*max(0,i(Vledsense))*v(feedback)/sqrt(v(feedback)*v(feedback)+.0025)\n"
    )
    circuit += MODELS
    circuit += """.options method=gear reltol=1e-4 abstol=1n
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran .0001 1.4 0 .0001 uic
wrdata trace.dat v(permit) v(estop) v(arm) v(wdok) v(bus) v(gate) i(lpump) i(lvalve) v(pumpdrain) v(valvedrain) v(feedback) v(adcrail) v(aux) v(itrip) v(pumpsource) v(valvesource)
quit
.endc
.end
"""
    if rev == "UNPROTECTED":
        circuit = circuit.replace(
            "Sestop raw mid k0delay 0 CONTACT",
            "Bestop raw mid I=v(raw,mid)*(1e-10+(1/.03-1e-10)*(1+tanh((v(k0delay)-2.5)/.1))/2)",
        )
    step = p.get("max_step_s", 0.0001)
    if "integration_order" in p:
        circuit = circuit.replace(
            "reltol=1e-4 abstol=1n", "reltol=1e-4 abstol=1n maxord=" + str(p["integration_order"])
        )
    return circuit.replace("tran .0001 1.4 0 .0001 uic", f"tran {step} 1.4 0 {step} uic")


def receiver(case):
    p = case.params
    revision = case.revision
    supply = p.get("supply", 24)
    r = p.get("burden", 100)
    current = p.get("current", 0.02)
    fault = p.get("fault", "normal")
    rail = p.get("rail", 3.3)
    # current source represents a transmitter with a 10V minimum operating
    # compliance; its physical transfer range is NOT inferred from disputed PDF.
    limited = min(current, p.get("limit", 0.033)) if revision == "R1" else current
    adc = (
        pwl([(0, rail), (0.01, rail), (0.01 + p.get("rail_fall_s", 0.0001), 0), (0.04, 0)])
        if fault == "adc_off"
        else str(rail)
    )
    inst = pwl([(0, 5), (0.01, 5), (0.0101, 0), (0.04, 0)]) if fault == "instrument_off" else "5"
    rawexpr = f"min({limited},max(0,(v(loop)-v(raw)-10)/{25 if revision == 'R1' else 1}))"
    if fault == "short_transmitter":
        rawexpr = "min(.033, max(0,(v(loop)-v(raw))/25))" if revision == "R1" else "max(0,(v(loop)-v(raw))/1)"
    if fault == "reverse_loop":
        supply = -abs(supply)
        rawexpr = "0" if revision == "R1" else "-.02"
    if fault == "open_loop":
        rawexpr = "0"
    if fault == "short_burden":
        r = 0.001
    if fault == "open_burden":
        r = 1e9
    circuit = f"""CertaRig {case.name}: sensor loop / ADC protection {revision}
Vloop loop 0 {supply}
Bsensor loop raw I={rawexpr}
Rburden raw 0 {r}
Vrail rail 0 {adc}
Vinst inst 0 {inst}
"""
    if revision == "UNPROTECTED":
        circuit += "Rinput raw pin 1\nCinput pin 0 100n\n"
    else:
        circuit += """* Bounded fault protection equivalent: 2.5V rail maintained by shunt
* reference plus steering diode and power-good controlled power-off isolator.
Rseries raw pre 10k
Cfilter pre 0 10n
Rbias inst ref 1k
Dref 0 ref REFERENCE
.model REFERENCE D(Is=1p N=1 Rs=.8 BV=2.5 IBV=80u)
Dupper pre ref CLAMP
Dlower 0 pre CLAMP
Bmux mux_enable 0 V=(v(rail)>3.0 && v(inst)>4.5 ? 5 : 0)
Smux pre pin mux_enable 0 MUX
Rdischarge pin 0 33k
* Worst-case off leakage, source-independent envelope +/-2uA.
Boffleak 0 pin I=(v(mux_enable)<2.5 ? 2u : 0)
Cpin pin 0 10p
.model MUX SW(Ron=4.5 Roff=1e12 Vt=2.5 Vh=.05)
.model CLAMP D(Is=1e-7 N=1.05 Rs=.5 Cjo=10p)
"""
    circuit += (
        f"""Radc pin 0 6Meg
Dadc_hi pin rail ESD
Dadc_lo 0 pin ESD
.model ESD D(Is=1p N=1.3 Rs=10 Cjo=4p)
Bheadroom headroom 0 V=v(loop)-v(raw)-10-abs(i(Vloop))*{25 if revision == "R1" else 0}
Bburden_power power 0 V=v(raw)*v(raw)/"""
        + str(r)
        + """
.options method=gear reltol=1e-5
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran .000002 .04 0 .000002
wrdata trace.dat v(raw) v(pin) v(rail) v(headroom) v(power) i(Vrail) i(Vloop)
quit
.endc
.end
"""
    )
    return circuit


def flow(case):
    p = case.params
    supply = p.get("supply", 5)
    ctr = p.get("ctr", 0.2)
    fault = p.get("fault", "normal")
    rail = 0 if fault == "pi_off" else 3.3
    field = 0 if fault == "open_signal" else supply
    return f"""CertaRig {case.name}: pulse interface {case.revision}
Vfield field 0 PULSE(0 {field} .001 10u 10u .0009 .002)
Vrail rail 0 {rail}
Rled field sense 560
Vled sense led 0
Dled led 0 LED
Danti 0 led REV
Rpull rail pin 10k
Cpin pin 0 1n
Bphoto pin 0 I={ctr}*max(0,i(Vled))*v(pin)/sqrt(v(pin)*v(pin)+.0025)
.model LED D(Is=1e-20 N=1.8 Rs=5 Cjo=20p)
.model REV D(Is=1n N=1.2 Rs=.05)
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran 2u .02 0 2u
wrdata trace.dat v(field) v(pin) v(rail) i(Vled)
quit
.endc
.end
"""


def maximum(data, col, start=0, end=1e9):
    vals = [r[col] for r in data if start <= r[0] <= end]
    return max(vals) if vals else None


def minimum(data, col, start=0, end=1e9):
    vals = [r[col] for r in data if start <= r[0] <= end]
    return min(vals) if vals else None


def assess(case, header, data):
    checks = []
    metrics = {}
    p = case.params

    def check(name, value):
        checks.append({"check": name, "passed": bool(value)})

    if case.family == "power":
        # column ordering matches wrdata vector order; time is column 0.
        peak = max(abs(r[9]) for r in data)
        peak = max(peak, max(abs(r[10]) for r in data))
        metrics = {
            "peak_drain_v": peak,
            "min_bus_v": minimum(data, 5),
            "peak_pump_a": maximum(data, 7),
            "peak_valve_a": maximum(data, 8),
            "peak_shunt_v": max(max(r[15], r[16]) for r in data),
        }
        kind = p.get("fault", "normal")
        check("startup_no_drive", maximum(data, 7, 0, 0.04) < 0.01 and maximum(data, 8, 0, 0.04) < 0.01)
        if kind not in {"heartbeat_missing", "stuck_command"} and not p.get("short_load"):
            check("run_has_expected_load_response", maximum(data, 8, 0.2, 0.3) > 0.1)
        check("drain_voltage_below_70V_model_design_limit", peak < 70)
        if kind in {"estop", "estop_reset_held", "estop_release_high", "brownout", "logic_loss"}:
            check(
                "fault_removes_current",
                maximum(data, 7, 0.46, 0.49) < 0.01 and maximum(data, 8, 0.46, 0.49) < 0.01,
            )
            check(
                "release_does_not_restart",
                maximum(data, 7, 0.8, 1.3) < 0.01 and maximum(data, 8, 0.8, 1.3) < 0.01,
            )
        elif kind in {"heartbeat_loss", "stuck_command"}:
            check(
                "watchdog_removes_current",
                maximum(data, 7, 0.7, 1.3) < 0.01 and maximum(data, 8, 0.7, 1.3) < 0.01,
            )
        elif kind == "heartbeat_missing":
            check("no_heartbeat_no_arm", maximum(data, 7) < 0.01 and maximum(data, 8) < 0.01)
        elif kind == "rearm":
            check("released_without_reset_stays_off", maximum(data, 8, 0.53, 0.64) < 0.01)
            check("fresh_reset_and_permit_restore_run", maximum(data, 8, 0.85, 1.0) > 0.1)
        elif kind == "feedback_broken":
            check("broken_feedback_stays_high", minimum(data, 11, 0.2, 0.3) > 3.0)
        if kind not in {
            "estop",
            "estop_reset_held",
            "estop_release_high",
            "brownout",
            "logic_loss",
            "heartbeat_loss",
            "heartbeat_missing",
            "stuck_command",
            "rearm",
            "feedback_broken",
        }:
            check(
                "permit_off_removes_current",
                maximum(data, 7, 0.75, 1.3) < 0.01 and maximum(data, 8, 0.75, 1.3) < 0.01,
            )
        if p.get("open_load"):
            check(
                "open_load_current_is_missing",
                maximum(data, 7 if p["open_load"] == "pump" else 8, 0.2, 0.3) < 0.001,
            )
        if p.get("short_load"):
            check("overcurrent_latches_trip", maximum(data, 14, 0.2, 0.3) > 4)
            check(
                "overcurrent_removes_current",
                maximum(data, 7, 0.3, 1.3) < 0.01 and maximum(data, 8, 0.3, 1.3) < 0.01,
            )
        # supply feedback is active-low, not a mechanical-position sensor.
        check("feedback_is_3V3_bounded", minimum(data, 11) >= -0.05 and maximum(data, 11) <= 3.35)
    elif case.family == "receiver":
        fault = p.get("fault", "normal")
        metrics = {
            "adc_pin_max_v": maximum(data, 2),
            "adc_pin_min_v": minimum(data, 2),
            "sensor_headroom_min_v": minimum(data, 4),
            "burden_peak_w": maximum(data, 5),
            "adc_steady_v": data[-1][2],
            "loop_steady_a": abs(data[-1][7]),
            "off_rail_injection_peak_a": max(abs(r[6]) for r in data if r[3] < 0.1)
            if fault == "adc_off"
            else None,
        }
        check("ADC_normal_range_margin", all(-0.3 <= r[2] <= r[3] + 0.3 for r in data))
        if fault == "normal":
            check("ADC_below_supply_for_valid_observation", maximum(data, 2) <= p.get("rail", 3.3))
        if fault == "normal":
            target = (
                min(p.get("current", 0.02), p.get("limit", 0.033))
                if case.revision == "R1"
                else p.get("current", 0.02)
            )
            check(
                "transmitter_current_tracks_request",
                abs(abs(data[-1][7]) - target) < max(1e-6, target * 0.001),
            )
            check("sensor_compliance_nonnegative", minimum(data, 4) >= 0)
            check("burden_below_0.5W", maximum(data, 5) < 0.5)
        if fault == "adc_off":
            check("off_pin_discharges_below_0.15V", maximum(data, 2, 0.011, 0.04) < 0.15)
            check("off_supply_injection_below_1uA", max(abs(r[6]) for r in data if r[0] > 0.011) < 1e-6)
        if fault == "instrument_off":
            check("loss_of_conditioner_disables_signal", maximum(data, 2, 0.011, 0.04) < 0.15)
        if fault == "open_burden":
            check("missing_burden_outside_valid_20mA_range", minimum(data, 2) > 1.8)
        if fault == "short_transmitter":
            check("input_fault_burden_survives_envelope", maximum(data, 5) < 0.5)
        if fault in {"open_loop", "reverse_loop", "short_burden"}:
            check("bad_loop_not_normal_4mA_reading", maximum(data, 2) < 0.2)
    else:
        metrics = {
            "logic_max_v": maximum(data, 2),
            "logic_min_v": minimum(data, 2),
            "led_max_a": maximum(data, 4),
        }
        check("logic_voltage_safe", all(-0.05 <= r[2] <= r[3] + 0.05 for r in data))
        check("LED_current_bounded", maximum(data, 4) < 0.02)
        if p.get("fault") not in {"pi_off", "open_signal"}:
            check("pulse_high_recognizable", maximum(data, 2) > 0.8 * p.get("rail", 3.3))
            check("pulse_low_recognizable", minimum(data, 2) < 0.4)
    return {"checks": checks, "metrics": metrics, "criteria_pass": all(c["passed"] for c in checks)}


def run_one(case, root, executable):
    folder = root / "cases" / case.name
    folder.mkdir(parents=True, exist_ok=True)
    netlist = {"power": power, "receiver": receiver, "flow": flow}[case.family](case)
    (folder / "trace.csv.gz").unlink(missing_ok=True)
    (folder / "circuit.cir").write_text(netlist)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [executable, "-b", "circuit.cir"], cwd=folder, capture_output=True, text=True, timeout=30
        )
    except subprocess.TimeoutExpired as exc:
        (folder / "ngspice.log").write_text(
            "TIMEOUT: invalid simulation; not a design result\n"
            + str(exc.stdout or "")
            + str(exc.stderr or "")
        )
        (folder / "trace.dat").unlink(missing_ok=True)
        return {
            "name": case.name,
            "family": case.family,
            "revision": case.revision,
            "params": case.params,
            "diagnostic": case.diagnostic,
            "criteria_pass": False,
            "error": "ngspice timeout",
        }
    (folder / "ngspice.log").write_text(proc.stdout + proc.stderr)
    if proc.returncode or not (folder / "trace.dat").is_file():
        (folder / "trace.dat").unlink(missing_ok=True)
        return {
            "name": case.name,
            "family": case.family,
            "revision": case.revision,
            "params": case.params,
            "error": "ngspice failed",
            "diagnostic": case.diagnostic,
            "process_exit": proc.returncode,
            "criteria_pass": False,
        }
    with (folder / "trace.dat").open() as f:
        header = f.readline().split()
        data = [[float(x) for x in line.split()] for line in f if line.strip()]
    if not data or not all(math.isfinite(x) for row in data for x in row):
        raise ValueError(f"bad trace {case.name}")
    expected_end = 1.4 if case.family == "power" else 0.04 if case.family == "receiver" else 0.02
    if data[-1][0] < expected_end - 1e-8 or "Timestep too small" in proc.stdout + proc.stderr:
        (folder / "trace.dat").unlink(missing_ok=True)
        return {
            "name": case.name,
            "family": case.family,
            "revision": case.revision,
            "params": case.params,
            "diagnostic": case.diagnostic,
            "criteria_pass": False,
            "error": "incomplete or nonconverged transient",
            "last_time": data[-1][0],
        }
    with gzip.open(folder / "trace.csv.gz", "wt", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)
    (folder / "trace.dat").unlink()
    result = {
        "name": case.name,
        "family": case.family,
        "revision": case.revision,
        "params": case.params,
        "diagnostic": case.diagnostic,
        "process_exit": proc.returncode,
        "samples": len(data),
        "wall_seconds": round(time.monotonic() - start, 3),
        "netlist_sha256": hashlib.sha256(netlist.encode()).hexdigest(),
        **assess(case, header, data),
    }
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def cases():
    result = [
        Case("negative_estop_auto_restart", "power", "UNPROTECTED", {"fault": "estop"}, True),
        Case("negative_no_suppression", "power", "UNPROTECTED", {"no_suppression": True}, True),
        Case("negative_receiver_12V_150R", "receiver", "UNPROTECTED", {"supply": 12, "burden": 150}),
        Case(
            "negative_receiver_24mA_150R",
            "receiver",
            "UNPROTECTED",
            {"supply": 24, "burden": 150, "current": 0.024},
            True,
        ),
        Case(
            "negative_adc_poweroff_backfeed",
            "receiver",
            "UNPROTECTED",
            {"supply": 24, "burden": 150, "fault": "adc_off"},
            True,
        ),
    ]
    result[2].diagnostic = True
    for fault in [
        "normal",
        "estop",
        "estop_reset_held",
        "estop_release_high",
        "rearm",
        "heartbeat_loss",
        "heartbeat_missing",
        "brownout",
        "logic_loss",
        "stuck_command",
        "feedback_broken",
    ]:
        result.append(Case("r1_power_" + fault, "power", params={"fault": fault}))
    result.extend(
        [
            Case("r1_mosfet_short", "power", params={"mos_short": "pump"}),
            Case("r1_master_welded", "power", params={"master_welded": True}),
            Case(
                "r1_combined_master_mos_short",
                "power",
                params={"master_welded": True, "mos_short": "pump"},
                diagnostic=True,
            ),
            Case("r1_open_pump", "power", params={"open_load": "pump"}),
            Case("r1_short_pump", "power", params={"short_load": "pump"}),
            Case(
                "r1_load_corner_high",
                "power",
                params={"supply": 13.2, "valve_r": 15, "valve_l": 0.5, "watchdog_s": 0.25},
            ),
            Case(
                "r1_load_corner_low",
                "power",
                params={"supply": 10.8, "valve_r": 40, "valve_l": 0.05, "watchdog_s": 0.15},
            ),
        ]
    )
    for current in [0, 0.0036, 0.004, 0.012, 0.020, 0.024, 0.033, 0.05]:
        result.append(Case(f"r1_receiver_{current * 1000:g}mA", "receiver", params={"current": current}))
    for fault in [
        "adc_off",
        "instrument_off",
        "short_transmitter",
        "reverse_loop",
        "open_loop",
        "short_burden",
        "open_burden",
    ]:
        result.append(Case("r1_receiver_" + fault, "receiver", params={"fault": fault}))
    result.append(
        Case("r1_receiver_fast_adc_off", "receiver", params={"fault": "adc_off", "rail_fall_s": 0.000001})
    )
    for supply in [21.6, 26.4]:
        for resistance in [99.9, 100.1]:
            result.append(
                Case(
                    f"r1_receiver_corner_{supply:g}V_{resistance:g}R",
                    "receiver",
                    params={"supply": supply, "burden": resistance, "current": 0.020, "rail": 3.135},
                )
            )
    for ctr in [0.2, 0.5, 2]:
        for supply in [4.5, 5.5]:
            result.append(
                Case(f"r1_flow_{supply:g}V_CTR{ctr:g}", "flow", params={"supply": supply, "ctr": ctr})
            )
    result.extend(
        [
            Case("r1_flow_pi_off", "flow", params={"fault": "pi_off"}),
            Case("r1_flow_wire_open", "flow", params={"fault": "open_signal"}),
        ]
    )
    result.extend(
        [
            Case("r1_refined_estop", "power", params={"fault": "estop", "max_step_s": 0.00002}),
            Case(
                "r1_refined_short",
                "power",
                params={"short_load": "pump", "max_step_s": 0.00002, "integration_order": 1},
            ),
            Case(
                "r1_combined_fault_estop",
                "power",
                params={"fault": "estop", "master_welded": True, "mos_short": "pump"},
            ),
        ]
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ngspice", default=shutil.which("ngspice"))
    parser.add_argument("--select", default="")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Replay and reuse complete traces only when the exact generated netlist and engine version match",
    )
    args = parser.parse_args()
    if not args.ngspice:
        raise SystemExit("ngspice executable required")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    selected = [c for c in cases() if args.select in c.name]
    if not selected:
        raise SystemExit("No matching scenarios")
    engine = subprocess.check_output([args.ngspice, "--version"], text=True).strip()
    previous_path = out / "summary.json"
    reuse_ok = (
        args.reuse and previous_path.is_file() and json.loads(previous_path.read_text())["engine"] == engine
    )
    results = []
    for case in selected:
        result = None
        folder = out / "cases" / case.name
        if reuse_ok and (folder / "result.json").is_file() and (folder / "trace.csv.gz").is_file():
            saved = json.loads((folder / "result.json").read_text())
            generated = {"power": power, "receiver": receiver, "flow": flow}[case.family](case)
            identity = hashlib.sha256(generated.encode()).hexdigest()
            if (
                "error" not in saved
                and saved.get("netlist_sha256") == identity
                and hashlib.sha256((folder / "circuit.cir").read_bytes()).hexdigest() == identity
            ):
                with gzip.open(folder / "trace.csv.gz", "rt") as stream:
                    reader = csv.reader(stream)
                    header = next(reader)
                    samples = [[float(value) for value in row] for row in reader]
                end = 1.4 if case.family == "power" else 0.04 if case.family == "receiver" else 0.02
                if (
                    len(samples) == saved["samples"]
                    and samples[-1][0] >= end - 1e-8
                    and all(math.isfinite(value) for row in samples for value in row)
                ):
                    result = {**saved, **assess(case, header, samples), "reused_trace": True}
        if result is None:
            result = run_one(case, out, args.ngspice)
        (out / "cases" / case.name / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(case.name, "complete" if "error" not in result else result["error"], flush=True)
    summary = {
        "engine": engine,
        "model_kind": "Explicit behavioral IC equivalents plus R/L/diode/switch circuit models; no manufacturer macromodel claim",
        "physical_validation": False,
        "procurement_release": False,
        "construction_release": False,
        "results": results,
        "required_pass": all(r.get("criteria_pass", False) for r in results if not r["diagnostic"]),
        "diagnostics_detected": all(
            not r.get("criteria_pass", False) and "error" not in r for r in results if r["diagnostic"]
        ),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = sorted(
        path
        for path in out.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS" and "__pycache__" not in path.parts
    )
    (out / "SHA256SUMS").write_text(
        "".join(
            hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path.relative_to(out)) + "\n"
            for path in files
        )
    )
    for r in results:
        print(
            ("PASS" if r.get("criteria_pass") else "FAIL"),
            r["name"],
            [c["check"] for c in r.get("checks", []) if not c["passed"]],
            r.get("error", ""),
        )
    print(
        "required_pass:", summary["required_pass"], "diagnostics_detected:", summary["diagnostics_detected"]
    )
    if not summary["required_pass"] or not summary["diagnostics_detected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
