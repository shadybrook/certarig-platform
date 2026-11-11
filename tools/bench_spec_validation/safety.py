"""Temporal specification model of an independent safety panel, not relay firmware."""

from dataclasses import dataclass

GUARDS = (
    "estop_A",
    "estop_B",
    "stop",
    "pressure",
    "level",
    "leak",
    "thermal",
    "field_power",
    "vacuum_admission",
)


@dataclass
class Panel:
    armed: bool = False
    reset_previous: bool = False
    heartbeat_previous: bool = False
    last_edge: float = -10.0
    edges: int = 0
    command_allowed: bool = False
    was_running: bool = False
    arm_time: float = -10.0

    def step(
        self,
        t,
        *,
        reset=False,
        permit=False,
        heartbeat=False,
        guards=None,
        welded=(False, False),
        ready=True,
        bypass_command=False,
    ):
        guards = guards or dict.fromkeys(GUARDS, True)
        if t - self.last_edge > 0.200:
            self.edges = 0
        if heartbeat != self.heartbeat_previous:
            self.edges += 1
            self.last_edge = t
        healthy = all(guards.values()) and self.edges >= 2 and t - self.last_edge <= 0.200
        edge = reset and not self.reset_previous
        if (
            not healthy
            or (self.was_running and not ready)
            or (self.armed and not ready and t - self.arm_time > 1.1)
        ):
            self.armed = False
        if not self.armed or not ready:
            self.command_allowed = False
        # EDM checks both physical cutoffs open, including welded feedback.
        if edge and healthy and not permit and not any(welded):
            self.armed = True
            self.arm_time = t
        contacts = tuple(self.armed or w for w in welded)
        if self.armed and ready and not permit:
            self.command_allowed = True
        power = all(contacts) and permit and (bypass_command or (ready and self.command_allowed))
        self.was_running = power
        self.reset_previous, self.heartbeat_previous = reset, heartbeat
        return {"armed": self.armed, "power": power, "contacts": list(contacts), "healthy": healthy}


def experiments():
    cases = []

    def exercise(name, fault=None, welded=(False, False), held=False, stuck_permit=False, negative=False):
        panel = Panel()
        rows = []
        for n in range(151):
            t = n / 100
            heartbeat = bool((n // 5) % 2)
            if fault == "watchdog" and t >= 0.7:
                heartbeat = True
            guards = dict.fromkeys(GUARDS, True)
            if fault in GUARDS and 0.7 <= t < 0.9:
                guards[fault] = False
            # Baseline edge at300ms; no second reset after recovery.
            reset = (0.01 <= t <= 1.5) if held else (0.30 <= t < 0.33)
            permit = stuck_permit or (0.45 <= t)
            weld = welded if t >= 0.60 else (False, False)
            if any(welded) and 0.7 <= t < 0.9:
                guards["estop_A"] = False
            rows.append(
                dict(
                    time_s=t,
                    **panel.step(
                        t,
                        reset=reset,
                        permit=permit,
                        heartbeat=heartbeat,
                        guards=guards,
                        welded=weld,
                        bypass_command=negative,
                    ),
                )
            )
        pre = any(r["power"] for r in rows if 0.5 <= r["time_s"] < 0.6)
        tail = any(r["power"] for r in rows if r["time_s"] >= 1.0)
        expected_block = bool(fault or any(welded) or held or stuck_permit)
        criteria = not tail if expected_block else pre and tail
        if fault or any(welded):
            criteria = criteria and pre
        if fault == "watchdog":
            first_drop = min(r["time_s"] for r in rows if r["time_s"] >= 0.7 and not r["power"])
            # 10ms functional model sampling plus <=40ms measured relay release.
            criteria = criteria and first_drop - 0.65 + 0.040 <= 0.250 + 1e-9
        cases.append(
            dict(
                name=name,
                passed=criteria != negative,
                negative_control=negative,
                pre_fault_power=pre,
                tail_power=tail,
                states=rows,
            )
        )

    exercise("normal_reset_then_fresh_permit")
    for guard in GUARDS:
        exercise("trip_" + guard, fault=guard)
    exercise("heartbeat_missing_or_static", fault="watchdog")
    exercise("held_RESET_refused", held=True)
    exercise("permit_high_at_RESET_refused", stuck_permit=True)
    exercise("one_weld_K1_contained", welded=(True, False))
    exercise("one_weld_K2_contained", welded=(False, True))
    exercise("negative_both_cutoffs_and_command_bypassed", welded=(True, True), negative=True)
    # Separate recovered-fault reset with a welded EDM contact: must not arm.
    p = Panel()
    p.edges = 2
    p.last_edge = 1
    a = p.step(1, reset=True, permit=False, heartbeat=False, welded=(True, False))
    cases.append(
        dict(name="welded_EDM_prevents_reset", passed=not a["armed"], negative_control=False, states=[a])
    )
    for name, mode in [
        ("delayed_READY_fresh_permit", "good"),
        ("early_held_permit_waiting_READY", "early"),
        ("READY_loss_no_restart", "loss"),
        ("READY_never_arrives_timeout", "never"),
    ]:
        panel = Panel()
        rows = []
        for n in range(251):
            t = n / 100
            ready = False if mode == "never" else ((t >= 1.40) if mode != "loss" else not (0.7 <= t < 0.9))
            permit = t >= (0.45 if mode != "good" else 1.5)
            rows.append(
                dict(
                    time_s=t,
                    **panel.step(
                        t, reset=0.3 <= t < 0.33, permit=permit, heartbeat=bool((n // 5) % 2), ready=ready
                    ),
                )
            )
        before = any(r["power"] for r in rows if r["time_s"] < 1.4)
        tail = any(r["power"] for r in rows if r["time_s"] > 1.8)
        criteria = tail and not before if mode == "good" else not tail
        if mode == "loss":
            criteria = criteria and before
        if mode == "never":
            criteria = criteria and not rows[-1]["armed"] and not before
        cases.append(dict(name=name, passed=criteria, negative_control=False, states=rows))
    return cases
