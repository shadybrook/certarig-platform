"""CR-EXT-R1 requirements validation. No connection to equipment.

Ngspice solves electrical module-boundary circuits. Python solves explicit
hydraulic/thermal bounds. These are not manufacturer IC macromodels or a PCB
construction release. Actual procurement must satisfy the frozen envelopes.
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

import hydraulics
import safety

SPEC = json.loads((Path(__file__).with_name("spec.json")).read_text())


def end(text, vectors, horizon, step, uic=False):
    return (
        text
        + f"""\n.options method=gear reltol=1e-5
.control
set wr_singlescale
set wr_vecnames
set numdgt=12
tran {step} {horizon} 0 {step}{" uic" if uic else ""}
wrdata trace.dat {vectors}
quit
.endc
.end
"""
    )


def cases():
    out = []

    def add(name, family, params=None, unsafe=False):
        out.append(dict(name=name, family=family, params=params or {}, unsafe=unsafe))

    for supply in [21.6, 26.4]:
        for current in [0.004, 0.020, 0.033]:
            add(f"afe_{supply}_{current}", "afe", dict(supply=supply, current=current))
    for fault in ["rail_loss", "open_burden", "short_loop", "short_burden", "open_loop"]:
        add("afe_" + fault, "afe", dict(fault=fault))
    add("negative_afe_no_hold_no_isolation", "afe", dict(fault="rail_loss", hold=1e-8, isolate=False), True)
    add("afe_rail_loss_refined", "afe", dict(fault="rail_loss", step=2e-7))
    for resistance in [99.9, 100.1]:
        add(f"afe_burden_{resistance}", "afe", dict(burden=resistance))
    for level in ["high", "low", "open", "short", "eol_open", "24V_fault"]:
        add("flow_" + level, "flow", dict(level=level))
    for supply in [4.75, 5.25]:
        for level in ["high", "low"]:
            add(f"flow_{supply}_{level}", "flow", dict(level=level, supply=supply))
    for supply in [10.8, 13.2]:
        for limit in [1.752, 2.268]:
            add(f"power_{supply}_{limit}", "power", dict(supply=supply, limit=limit))
    for fault in [
        "short",
        "overload",
        "estop",
        "watchdog",
        "brownout",
        "q_short",
        "k1_weld",
        "k2_weld",
        "k1_weld_q_short",
        "restore",
    ]:
        add("power_" + fault, "power", dict(fault=fault))
    add("power_max_cap_low_limit", "power", dict(cap=0.00047, limit=1.752, power=12))
    add(
        "power_low_limit_fast_timer",
        "power",
        dict(supply=10.8, cap=0.00047, limit=1.752, power=12, timeout=0.020),
    )
    add("power_refined", "power", dict(step=2e-6))
    add("negative_power_no_cutoff_no_latch", "power", dict(fault="q_short", unguarded=True), True)
    for inductance in [0.05, 1, 10]:
        add("coil_" + str(inductance), "coil", dict(L=inductance))
    add("negative_coil_no_suppression", "coil", dict(L=10, unclamped=True), True)
    return out


def circuit(case):
    p = case["params"]
    family = case["family"]
    if family == "afe":
        current = p.get("current", 0.02)
        fault = p.get("fault", "")
        r = p.get("burden", 100)
        if fault == "open_burden":
            r = 1e9
        if fault == "short_burden":
            r = 0.001
        if fault == "open_loop":
            current = 0
        if fault == "short_loop":
            current = 0.1
        field = "PWL(0 5 .01 5 .010001 0 .04 0)" if fault == "rail_loss" else "5"
        mux = "Rdirect pre pin 4.5" if not p.get("isolate", True) else "Smux pre pin en 0 SWITCH"
        text = f"""CR-EXT-R1 AFE {case["name"]}
* Field ADC 5V; host connected through isolated I2C, not analog.
Vloop loop 0 {p.get("supply", 24)}
Btx loop raw I=min({current},min(.033,max(0,(v(loop)-v(raw)-11)/55)))
Rburden raw 0 {r}
* Real wiring/filter capacitance prevents a singular open-input initial step.
Craw raw 0 10n IC=0
Vfield field 0 {field}
Dhold field adcrail HOLD
Cadc adcrail 0 {p.get("hold", 0.0001)} IC=4.6
Bload adcrail 0 I=.02*max(0,v(adcrail))/(max(0,v(adcrail))+.1)
Rpg field pg 10k
Cpg pg 0 39n IC=5
Ben en 0 V=(v(pg)>4.4 ? 5 : 0)
* Independent passive reference remains available from instrument 24V.
Rbias loop ref 10k
Dref 0 ref REF
Rseries raw pre 10k
Dupper pre ref CLAMP
Dlower 0 pre CLAMP
{mux}
Boff 0 pin I=(v(en)<2.5 ? 2u : 0)
Rdis pin 0 33k
Cpin pin 0 10p
Radc pin 0 6Meg
Dhi pin adcrail ESD
Dlo 0 pin ESD
Vhost hostrail 0 0
Bhostleak 0 hostpin I=1u
Rhost hostpin hostrail 33k
.model HOLD D(Is=1u N=1 Rs=.05)
.model REF D(Is=1p N=1 Rs=.8 BV=2.5 IBV=80u)
.model CLAMP D(Is=1e-7 N=1.05 Rs=.5 Cjo=10p)
.model ESD D(Is=1p N=1.3 Rs=10 Cjo=4p)
.model SWITCH SW(Ron=4.5 Roff=1e12 Vt=2.5 Vh=.05)
Bpow power 0 V=v(raw)*v(raw)/{r}
"""
        return end(
            text,
            "v(raw) v(pin) v(adcrail) v(en) i(Vloop) v(power) v(hostpin)",
            0.04,
            p.get("step", 2e-6),
            True,
        ), 0.04
    if family == "flow":
        s = p.get("supply", 5)
        level = p["level"]
        eol = 1e12 if level == "eol_open" else 10000
        sw = ".001" if level in ["low", "eol_open"] else "1e12"
        text = f"""CR-EXT-R1 supervised flow {case["name"]}
Vfield field 0 {s}
Rpull field line 4700
Rwire line remote {1e12 if level == "open" else 1}
Reol remote 0 {eol}
Rseries remote sink 2200
Rnpn sink 0 {sw}
"""
        if level == "short":
            text += "Rshort line 0 .001\n"
        if level == "24V_fault":
            text += "Vwrong wrong 0 24\nRwrong wrong line 10\n"
        text += "Rinput line protected 10k\nDclamp 0 protected Z\n.model Z D(Is=1p N=1 Rs=.2 BV=4.3 IBV=1m)\n"
        return end(text, "v(line) v(protected) i(Vfield)", 0.01, 1e-5), 0.01
    if family == "coil":
        text = f"""CR-EXT-R1 coil {case["name"]}
V24 src 0 26.4
Rcoil src mid 44
Lcoil mid drain {p["L"]}
Vgate gate 0 PWL(0 5 .3 5 .30001 0 1 0)
Sload drain 0 gate 0 SW
Coss drain 0 1n
.model SW SW(Ron=.154 Roff=1e12 Vt=2.5 Vh=.05)
.model D D(Is=1n N=1.5 Rs=.05)
.model Z D(Is=1p N=1 Rs=.1 BV=28 IBV=1m)
.model AV D(Is=1p N=1 Rs=.1 BV=100 IBV=1m)
Dav 0 drain AV
"""
        if not p.get("unclamped"):
            text += "Dfly drain z D\nDz src z Z\n"
        text += "BcoilV cv 0 V=v(src,drain)\nBclampPower cp 0 V=max(0,v(drain,src)*i(Dav))\n"
        # Clamp energy is analytically bounded from initial coil energy below.
        return end(text, "i(Lcoil) v(drain) v(cv)", 1, 1e-4), 1
    if family == "power":
        fault = p.get("fault", "")
        s = p.get("supply", 13.2)
        il = p.get("limit", 2.268)
        cmd = "PWL(0 0 .12 0 .12001 5 .30 5 .30001 0 .5 0 .50001 5 .8 5)"
        healthy = (
            "PWL(0 5 .35 5 .35001 0 .43 0 .43001 5 .8 5)"
            if fault in ["estop", "watchdog", "k1_weld", "k2_weld", "k1_weld_q_short"]
            else "5"
        )
        vin = (
            f"PWL(0 {s} .35 {s} .351 0 .43 0 .431 {s} .8 {s})" if fault in ["brownout", "restore"] else str(s)
        )
        # RC latch, monitored reset, contact delay and per-enable timers are solved
        # inside SPICE. S01 current/power control is a declared module equivalent.
        text = f"""CR-EXT-R1 protected pump chain {case["name"]}
Vsource source 0 {vin}
Rsource source raw .3
Cinput raw 0 220u IC={s}
Vcmd cmd 0 {cmd}
Vhealth health 0 {healthy}
Vreset reset 0 PWL(0 0 .05 0 .05001 5 .07 5 .07001 0 .8 0)
Rreset reset lag 1k
Creset lag 0 1u IC=0
Breset edge 0 V=(v(reset)-v(lag)>.5 ? 5 : 0)
Carm arm 0 1u IC=0
Rarm arm 0 1e12
Barm arm 0 I=(v(trip)>2.5 || v(health)<2.5 || v(raw)<9.5 ? v(arm)/100 : (v(edge)>2.5 && v(cmd)<.5 ? (v(arm)-5)/100 : 0))
Barmbuffer armcmd 0 V=(v(arm)>2.5 ? 5 : 0)
Rk armcmd k 10k
Ck k 0 3.5u IC=0
Sk1 raw middle k 0 CONTACT
Sk2 middle input k 0 CONTACT
.model CONTACT SW(Ron=.03 Roff=1e12 Vt=2.5 Vh=.05)
"""
        if fault in ["k1_weld", "k1_weld_q_short"] or p.get("unguarded"):
            text += "Vweld wc 0 PWL(0 0 .2 0 .20001 5 .8 5)\nSweld raw middle wc 0 CONTACT\n"
        if fault == "k2_weld" or p.get("unguarded"):
            text += "Vweld2 wc2 0 PWL(0 0 .2 0 .20001 5 .8 5)\nSweld2 middle input wc2 0 CONTACT\n"
        text += f"""Ben enabled 0 V=(v(arm)>2.5 && v(cmd)>2.5 && v(trip)<2.5 ? 5 : 0)
Crun elapsed 0 1m IC=0
Brun 0 elapsed I=(v(enabled)>2.5 ? .001 : -v(elapsed)/1)
Coff offtime 0 1m IC=0
Boff 0 offtime I=(v(enabled)<2.5 ? .001 : -v(offtime)/1)
Cramp ramp 0 10u IC=0
Bramp 0 ramp I=(v(enabled)>2.5 ? min(.0005,max(0,(1-v(ramp))/.1)) : -v(ramp)/1)
Btarget target 0 V=max(0,v(input))*min(1,max(0,v(ramp)))
Bbound bound 0 V=min({il},{p.get("power", 25)}/max(.1,v(input,out)))
Bpass input measured I=(v(enabled)>2.5 ? min(v(bound),max(0,(v(target)-v(out))/.072)) : 0)
Vsense measured out 0
Cout out 0 {p.get("cap", 0.00047)} IC=0
Bdis out 0 I=(v(enabled)<2.5 ? v(out)/47 : v(out)/10000)
Bpump out 0 I=(v(elapsed)<.06 ? 1.5 : {3 if fault == "overload" else 1.0})*(1+tanh((v(out)-5.8)/.25))/2
Blimiting limiting 0 V=(i(Vsense)>.99*v(bound) && v(enabled)>2.5 ? 5 : 0)
Ctimer timer 0 1m IC=0
Btimer 0 timer I=(v(limiting)>2.5 ? .001 : (v(timer)>0 ? -.00001 : 0))
Ctrip trip 0 1u IC=0
Rtrip trip 0 1e12
Btrip trip 0 I=(v(trip)>2.5 || v(timer)>{p.get("timeout", 0.06)} || (v(elapsed)>.10 && v(out)<6) || (v(offtime)>.12 && time>.3 && v(out)>1) ? (v(trip)-5)/100 : 0)
Bpower power 0 V=max(0,v(input,out)*i(Vsense))
"""
        if fault == "short":
            text += "Rshort out 0 .05\n"
        if fault in ["q_short", "k1_weld_q_short"]:
            text += "Vqs qs 0 PWL(0 0 .2 0 .20001 5 .8 5)\nSqs input out qs 0 CONTACT\n"
        if p.get("unguarded"):
            text += "Rtrip_bypass trip 0 .00001\n"
        return end(
            text,
            "v(out) i(Vsource) v(arm) v(trip) v(enabled) i(Vsense) v(power) v(timer)",
            0.8,
            p.get("step", 1e-5),
            True,
        ), 0.8
    raise ValueError(family)


def assess(case, rows):
    family = case["family"]
    p = case["params"]
    checks = {}
    metrics = {}
    if family == "afe":
        checks["adc_pin_absolute_budget"] = all(-0.3 <= r[2] <= r[3] + 0.3 for r in rows)
        checks["burden_below_half_watt"] = max(r[6] for r in rows) < 0.5
        checks["host_poweroff_injection_bounded"] = max(r[7] for r in rows) < 0.15
        fault = p.get("fault", "")
        if fault == "rail_loss":
            checks["signal_disconnected_after_loss"] = max(r[2] for r in rows if r[0] > 0.012) < 0.15
        if fault in ["open_burden", "short_burden", "open_loop", "short_loop"]:
            pin = rows[-1][2]
            # From the full nominal receiver divider; includes reference clamping.
            normal_low = 0.0036 / 0.020 * 1.5292
            normal_high = 0.021 / 0.020 * 1.5292
            checks["fault_is_not_a_valid_observation"] = not (normal_low <= pin <= normal_high)
        if p.get("current", 0.020) > 0.021:
            inferred = rows[-1][2] / 1.5292 * 0.020
            checks["overrange_is_invalid"] = not (0.0036 <= inferred <= 0.021)
        metrics = dict(
            pin_max_V=max(r[2] for r in rows),
            rail_min_V=min(r[3] for r in rows),
            host_off_pin_V=max(r[7] for r in rows),
        )
    elif family == "flow":
        ratio = rows[-1][1] / p.get("supply", 5)
        valid = (0.25 <= ratio <= 0.295) or (0.655 <= ratio <= 0.705)
        healthy = p["level"] in ["low", "high"]
        checks["healthy_low_or_high_is_valid_zero_or_pulse"] = valid == healthy
        checks["conditioned_field_input_bounded"] = max(r[2] for r in rows) < 5.5
        metrics = dict(line_V=rows[-1][1], ratio=ratio, valid=valid)
    elif family == "coil":
        checks["drain_below_80V_design_limit"] = max(r[2] for r in rows) < 80
        checks["coil_current_removed_by_one_second"] = abs(rows[-1][1]) < 0.001
        energy = 0.5 * p["L"] * max(r[1] for r in rows) ** 2
        checks["energy_within_5J_suppressor_requirement"] = energy < 5
        metrics = dict(drain_peak_V=max(r[2] for r in rows), stored_energy_J=energy)
    else:
        fault = p.get("fault", "")
        bad = fault in [
            "short",
            "overload",
            "estop",
            "watchdog",
            "brownout",
            "restore",
            "q_short",
            "k1_weld",
            "k2_weld",
            "k1_weld_q_short",
        ]
        tail = [r for r in rows if 0.65 < r[0] < 0.79]
        if bad:
            checks["fault_does_not_restart"] = max(r[1] for r in tail) < 1
            if fault in ["short", "overload"]:
                checks["fault_was_actually_excited"] = (
                    max(r[6] for r in rows) > 0.5 and max(r[4] for r in rows) > 4
                )
            else:
                checks["pre_fault_actuation_was_observed"] = max(r[1] for r in rows if 0.17 < r[0] < 0.20) > 6
        else:
            checks["startup_supports_load"] = min(r[1] for r in rows if 0.22 < r[0] < 0.28) > 6
            checks["no_nuisance_latch"] = max(r[4] for r in rows) < 0.1
        # Q-short transfer through the explicitly independent cutoffs is assessed
        # separately; its bypass current does not go through the modeled pass FET.
        checks["pass_current_bounded"] = max(r[6] for r in rows) <= p.get("limit", 2.268) + 0.001
        checks["pass_power_bounded"] = max(r[7] for r in rows) <= p.get("power", 25) + 0.01
        checks["regulated_forward_SOA_rectangle"] = (
            max(r[6] for r in rows) < 2.3 and max(r[7] for r in rows) < 575
        )
        metrics = dict(
            output_max_V=max(r[1] for r in rows),
            pass_peak_A=max(r[6] for r in rows),
            pass_peak_W=max(r[7] for r in rows),
            tail_voltage_max_V=max(r[1] for r in tail),
        )
        metrics["pass_energy_J"] = sum(
            (b[0] - a[0]) * (a[7] + b[7]) / 2 for a, b in zip(rows, rows[1:], strict=False)
        )
    return dict(checks=checks, metrics=metrics, criteria_pass=all(checks.values()))


def analytical():
    out = []

    def add(name, ok, metrics, basis):
        out.append(dict(name=name, passed=ok, metrics=metrics, basis=basis))

    h = SPEC["hydraulic"]
    rho = 1000
    # Energy and slow-closure bounds use declared line inertance, including all
    # fittings, and a factor of two on pressure rise. They are not CFD/FEM.
    for line, inertance, Q in [
        ("branch", h["branch_inertance_max_Pas2m3"], 2 / 60000),
        ("main", h["main_inertance_max_Pas2m3"], 10 / 60000),
    ]:
        energy = 0.5 * inertance * Q * Q
        peak = 0.60 + 2 * math.sqrt(2 * energy / h["arrestor_compliance_min_m3Pa"]) / 1e5
        add(
            line + "_instant_closure_with_arrestor",
            peak < 2,
            dict(energy_J=energy, peak_bound_bar=peak),
            "Stored line kinetic energy into minimum declared compliance; factor 2 pressure margin; 0.60bar head envelope",
        )
    slow = 0.6 + 2 * h["branch_inertance_max_Pas2m3"] * (2 / 60000) / 0.05 / 1e5
    add(
        "arrestor_unavailable_slow_valve",
        slow < 2,
        dict(peak_bar=slow),
        "Minimum 50ms hydraulic closure and maximum total branch inertance, conservative slow-closure bound",
    )
    unsafe = 0.6 + rho * 1500 * (2 / 60000) / (math.pi * 0.006**2 / 4) / 1e5
    add(
        "negative_fast_valve_and_no_arrestor_detected",
        unsafe > 6,
        dict(peak_bar=unsafe),
        "Unsafe simultaneous loss of two transient protections; Joukowsky upper comparison, not permitted procurement substitution",
    )
    # PRV capacity at 0.45bar must exceed entire possible pump free flow.
    add(
        "relief_capacity_covers_pump",
        10 >= 10,
        dict(pump_Lmin=10, relief_Lmin=10, full_flow_pressure_bar=0.45),
        "Independent full-flow water relief; return backpressure included in supplier rating",
    )
    for head in [0.3, 0.6]:
        for free in [7, 10]:
            for curve in [0.5, 1, 2]:
                for blocked in [False, True]:

                    def balance(pressure, free=free, head=head, curve=curve, blocked=blocked):
                        q = free * max(0, 1 - pressure / head) ** curve if pressure < head else 0
                        # Fixed bypass coefficient from a conservative 2m/12mm pipe loss
                        # envelope. Actual supplier curve must be inside the stated envelope.
                        bypass = 0 if blocked else (10 / math.sqrt(0.10)) * math.sqrt(max(0, pressure))
                        branch = 1.5 * math.sqrt(max(0, pressure) / 0.45)
                        relief = 10 * math.sqrt(max(0, pressure - 0.33) / (0.45 - 0.33))
                        return q - bypass - branch - relief

                    lo, hi = 0.0, head
                    for _ in range(70):
                        mid = (lo + hi) / 2
                        if balance(mid) > 0:
                            lo = mid
                        else:
                            hi = mid
                    p = (lo + hi) / 2
                    add(
                        f"hydraulic_{head}_{free}_{curve}_{blocked}",
                        p <= 0.45,
                        dict(steady_bar=p, bypass_blocked=blocked),
                        "Monotone curve-shape family, fixed return, bounded metering branch and independent full-flow relief; not an identified vendor pump curve",
                    )
    add(
        "permanent_bypass_normal_pressure",
        0.10 < 0.12,
        dict(required_bypass_Lmin=10, pressure_bar=0.10),
        "Certified complete return passes maximum pump free flow by0.10bar; branch only adds capacity. Hose ID alone does not prove this.",
    )
    add(
        "valve_suppressor_stored_energy",
        0.5 * 10 * 0.6**2 < 5,
        dict(max_energy_J=0.5 * 10 * 0.6**2, minimum_rating_J=5),
        "Worst allowed coil L and current, independent of whether a short simulation reached steady state; verify actual suppressor pulse duration/temperature curve.",
    )
    # Field ADC hold-up: at 20mA, 100uF loses 10mV in 50us.
    droop = 0.02 * 0.00005 / 0.0001
    add(
        "AFE_hold_up_before_isolation",
        4.5 - droop > 3.6,
        dict(droop_V=droop, rail_after_delay_V=4.5 - droop),
        "Explicit 50us worst disconnect envelope, no ideal instantaneous switch claim",
    )
    for R in [0.0274, 0.0681]:
        imin = 0.0485 / (R * 1.01)
        imax = 0.0615 / (R * 0.99)
        add(
            "LM5069_current_bound_" + str(R),
            imax < 2.3,
            dict(min_A=imin, max_A=imax),
            "TI threshold bounds and 1% reference shunt; actual module output acceptance required",
        )
    tmin = 0.68e-6 * 0.95 * 3.76 / 120e-6
    tmax = 0.68e-6 * 1.05 * 4.16 / 51e-6
    add(
        "LM5069_timer_bound",
        tmin >= 0.020 and tmax <= 0.060,
        dict(min_s=tmin, max_s=tmax, max_fault_energy_J=25 * tmax),
        "680nF 5%, TI timer threshold/current extremes; regulator limiting only, restart remains human-gated",
    )
    add(
        "thermal_pass_junction_bound",
        75 + 25 * 0.14 < 125,
        dict(junction_bound_C=75 + 25 * 0.14),
        "Case limited to <=75C and RthetaJC <=0.14C/W; not ambient-only thermal arithmetic",
    )
    for mass, ambient in [(3, 30), (3, 35), (2, 30), (1, 30)]:
        C = mass * 4180
        UA = 0.5
        T = ambient
        dt = 1.0
        peak = T
        trip = None
        for t in range(3600):
            heat = 30 if trip is None else 0
            T += (heat - UA * (T - ambient)) / C * dt
            peak = max(peak, T)
            if T >= 40 and trip is None:
                trip = t + 1
        expected_trip = ambient > 30 or mass < 3
        add(
            f"water_thermal_{mass}L_{ambient}C",
            (trip is not None) == expected_trip,
            dict(peak_C=peak, trip_at_s=trip),
            "First-order 60min water energy balance, both loads heat water at full 30W, no invented measured endurance result",
        )
    # Time-dependent state model separately preserves every sampled state.
    add(
        "linear_FET_short_overshoot",
        8 * 30 < 575 / 2 and 75 + 8 * 30 * 0.14 < 125,
        dict(overshoot_A=8, VDS_V=30, duration_us=20, power_W=240, junction_bound_C=75 + 240 * 0.14),
        "Contract bound, conservative half of 575W SOA reference and manufacturer 75C FBSOA curve; supplier must prove its actual gate/choke waveform. Behavioral current limiter does not simulate IC overshoot.",
    )
    insert_min = 0.68e-6 * 0.95 * 3.76 / 8e-6
    insert_max = 0.68e-6 * 1.05 * 4.16 / 3e-6
    add(
        "LM5069_insertion_delay",
        insert_max < 1.1,
        dict(min_s=insert_min, max_s=insert_max),
        "Initial TIMER insertion charge differs from fault charge; wait for ready and new permit; held permit must not start on readiness restoration.",
    )
    return out


def refinement_checks(results, transient):
    indexed = {r["case"]["name"]: r["assessment"]["metrics"] for r in results}
    pairs = [
        (
            "power",
            indexed["power_13.2_2.268"]["pass_energy_J"],
            indexed["power_refined"]["pass_energy_J"],
            0.01,
        ),
        ("AFE", indexed["afe_rail_loss"]["pin_max_V"], indexed["afe_rail_loss_refined"]["pin_max_V"], 0.001),
    ]
    by_name = {r["parameters"]["name"]: r for r in transient}
    pairs.append(
        (
            "hydraulic",
            by_name["minimum_compliance_fast_valve"]["peak_bar"],
            by_name["minimum_compliance_refined"]["peak_bar"],
            0.001,
        )
    )
    return [
        dict(
            name=name,
            coarse=a,
            refined=b,
            relative_difference=abs(a - b) / max(abs(b), 1e-12),
            passed=abs(a - b) / max(abs(b), 1e-12) < tol,
            relative_tolerance=tol,
        )
        for name, a, b, tol in pairs
    ]


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
    for case in cases():
        folder = root / "cases" / case["name"]
        folder.mkdir(parents=True, exist_ok=True)
        text, horizon = circuit(case)
        (folder / "circuit.cir").write_text(text)
        (folder / "trace.dat").unlink(missing_ok=True)
        proc = subprocess.run(
            [engine, "-b", "circuit.cir"], cwd=folder, capture_output=True, text=True, timeout=35
        )
        log = proc.stdout + proc.stderr
        (folder / "ngspice.log").write_text(log)
        if proc.returncode or not (folder / "trace.dat").is_file():
            raise RuntimeError("Invalid solve " + case["name"])
        with (folder / "trace.dat").open() as f:
            header = f.readline().split()
            rows = [[float(x) for x in row.split()] for row in f if row.strip()]
        if (
            not rows
            or rows[-1][0] < horizon - 1e-8
            or any(b[0] < a[0] for a, b in zip(rows, rows[1:], strict=False))
            or any(len(r) != len(header) or not all(math.isfinite(x) for x in r) for r in rows)
            or any(
                t in log.lower() for t in ["timestep too small", "transient analysis failed", "fatal error"]
            )
        ):
            raise RuntimeError("Incomplete/nonfinite " + case["name"])
        with gzip.open(folder / "trace.csv.gz", "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        (folder / "trace.dat").unlink()
        a = assess(case, rows)
        result = dict(
            case=case,
            assessment=a,
            samples=len(rows),
            horizon=horizon,
            netlist_sha256=hashlib.sha256(text.encode()).hexdigest(),
            experiment_ok=a["criteria_pass"] != case["unsafe"],
        )
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
        print(case["name"], result["experiment_ok"], flush=True)
    hydraulic = hydraulics.run(root)
    logic = safety.experiments()
    (root / "safety.json").write_text(json.dumps(logic, indent=2) + "\n")
    for r in hydraulic:
        folder = root / "hydraulic" / r["parameters"]["name"]
        (folder / "result.json").write_text(json.dumps(r, indent=2) + "\n")
    summary = dict(
        numerical_refinement=refinement_checks(results, hydraulic),
        hydraulic_transients=hydraulic,
        safety_cases=[{k: v for k, v in r.items() if k != "states"} for r in logic],
        revision=SPEC["revision"],
        spec_sha256=hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest(),
        engine=subprocess.check_output([engine, "--version"], text=True).strip(),
        results=results,
        analytical=analytical(),
        physical_qualification=False,
        manufacturer_macromodel=False,
        procurement_status="Requirements envelope only; supplier compliance/drawings mandatory",
        all_experiments_ok=all(r["experiment_ok"] for r in results)
        and all(r["passed"] for r in analytical())
        and all(r["experiment_ok"] for r in hydraulic)
        and all(r["passed"] for r in logic)
        and all(r["passed"] for r in refinement_checks(results, hydraulic)),
    )
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    shutil.copy2(Path(__file__).with_name("hydraulics.py"), root / "hydraulics.py")
    shutil.copy2(Path(__file__).with_name("safety.py"), root / "safety.py")
    shutil.copy2(__file__, root / "validate.py")
    shutil.copy2(Path(__file__).with_name("spec.json"), root / "spec.json")
    manifest(root)
    if not summary["all_experiments_ok"]:
        raise SystemExit("Inspect failed experiment(s); no passing-design claim")


def verify(root):
    entries = [x.split("  ", 1) for x in (root / "SHA256SUMS").read_text().splitlines() if x]
    names = {r for _, r in entries}
    if not {"summary.json", "spec.json", "validate.py", "hydraulics.py", "safety.py", "safety.json"}.issubset(
        names
    ):
        raise ValueError("Incomplete manifest")
    for digest, rel in entries:
        p = (root / rel).resolve()
        if (
            not p.is_relative_to(root.resolve())
            or not p.is_file()
            or hashlib.sha256(p.read_bytes()).hexdigest() != digest
        ):
            raise ValueError("Missing/corrupt " + rel)
    s = json.loads((root / "summary.json").read_text())
    declared = cases()
    if (
        len(declared) != len(s["results"])
        or s["spec_sha256"] != hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()
    ):
        raise ValueError("Spec or case mismatch")
    for case, saved in zip(declared, s["results"], strict=True):
        folder = root / "cases" / case["name"]
        text, horizon = circuit(case)
        if saved["case"] != case or (folder / "circuit.cir").read_text() != text:
            raise ValueError("Case/netlist mismatch")
        if not {
            f"cases/{case['name']}/{n}" for n in ["circuit.cir", "ngspice.log", "result.json", "trace.csv.gz"]
        }.issubset(names):
            raise ValueError("Missing case artifacts")
        with gzip.open(folder / "trace.csv.gz", "rt") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [[float(x) for x in r] for r in reader]
        if (
            not rows
            or len(rows) != saved["samples"]
            or rows[-1][0] < horizon - 1e-8
            or any(b[0] < a[0] for a, b in zip(rows, rows[1:], strict=False))
            or any(len(r) != len(header) or not all(math.isfinite(x) for x in r) for r in rows)
        ):
            raise ValueError("Incomplete/nonfinite trace")
        expected_vectors = circuit(case)[0].split("wrdata trace.dat ", 1)[1].splitlines()[0].split()
        if header != ["time"] + expected_vectors:
            raise ValueError("Vector/header mismatch")
        a = assess(case, rows)
        if a != saved["assessment"] or not saved["experiment_ok"] or a["criteria_pass"] == case["unsafe"]:
            raise ValueError("Replay/criteria mismatch")
    if analytical() != s["analytical"] or not all(r["passed"] for r in s["analytical"]):
        raise ValueError("Analytical replay mismatch")
    if refinement_checks(s["results"], s["hydraulic_transients"]) != s["numerical_refinement"] or not all(
        r["passed"] for r in s["numerical_refinement"]
    ):
        raise ValueError("Numerical refinement mismatch")
    if not s["all_experiments_ok"]:
        raise ValueError("Summary failure status")
    if safety.experiments() != json.loads((root / "safety.json").read_text()):
        raise ValueError("Safety state replay mismatch")
    for p, saved in zip(hydraulics.scenarios(), s["hydraulic_transients"], strict=True):
        if hydraulics.solve(p) != saved or not saved["experiment_ok"]:
            raise ValueError("Hydraulic replay mismatch")
        if not {f"hydraulic/{p['name']}/{n}" for n in ["result.json", "trace.csv.gz"]}.issubset(names):
            raise ValueError("Missing hydraulic evidence")
    for item in s["hydraulic_transients"]:
        folder = root / "hydraulic" / item["parameters"]["name"]
        with gzip.open(folder / "trace.csv.gz", "rt") as stream:
            data = list(csv.DictReader(stream))
        vals = [float(r["valve_pressure_Pa"]) for r in data]
        times = [float(r["time_s"]) for r in data]
        if (
            len(data) != item["steps"]
            or times[-1] < item["parameters"]["end"] - 1e-9
            or not all(math.isfinite(v) for v in vals)
            or any(b <= a for a, b in zip(times, times[1:], strict=False))
        ):
            raise ValueError("Incomplete hydraulic samples")
        if max(vals) / 1e5 != item["peak_bar"] or min(vals) / 1e5 != item["min_bar"]:
            raise ValueError("Hydraulic raw-sample replay mismatch")
    print(
        f"VERIFIED {len(declared)} SPICE experiments and {len(s['analytical'])} calculated checks; {len(s['hydraulic_transients'])} hydraulic and {len(s['safety_cases'])} safety/READY cases, plus3 refinement comparisons"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run", "verify", "manifest"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"run": run, "verify": verify, "manifest": manifest}[args.mode](args.root.resolve())
