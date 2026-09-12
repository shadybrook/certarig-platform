from __future__ import annotations

from .models import CommissioningPlan, PlanState, RigConfig, RigSnapshot

ALLOWED_ACTIONS = {"set_valve", "hold", "sample"}


def validate_plan(
    config: RigConfig,
    snapshot: RigSnapshot,
    plan: CommissioningPlan,
) -> list[str]:
    findings: list[str] = []
    if plan.rig_id != config.rig_id:
        findings.append("plan rig_id does not match the loaded rig")
    if plan.config_hash != config.config_hash:
        findings.append("plan configuration hash is stale")
    if snapshot.config_hash != config.config_hash:
        findings.append("snapshot configuration hash is stale")
    if snapshot.emergency_stop_active:
        findings.append("emergency stop is active")
    if plan.pressure_limit_bar <= 0 or plan.pressure_limit_bar > config.pressure_abort_bar:
        findings.append("plan pressure limit exceeds the approved abort limit")
    if not 1 <= len(plan.steps) <= 20:
        findings.append("plan must contain between 1 and 20 steps")

    samples = {sample.channel_id: sample for sample in snapshot.samples}
    for channel in config.channels:
        if channel.required and not channel.calibration_id:
            findings.append(f"{channel.channel_id} has no calibration identifier")
        sample = samples.get(channel.channel_id)
        if channel.required and sample is None:
            findings.append(f"{channel.channel_id} is missing from the current snapshot")
        elif sample is not None and sample.quality != "good":
            findings.append(f"{channel.channel_id} sample quality is {sample.quality}")

    for index, step in enumerate(plan.steps):
        if step.action not in ALLOWED_ACTIONS:
            findings.append(f"step {index} uses unsupported action {step.action}")
        if step.duration_ms < 0 or step.duration_ms > 10_000:
            findings.append(f"step {index} duration is outside 0 to 10000 ms")
        if step.action == "set_valve" and step.valve_open is None:
            findings.append(f"step {index} must define valve_open")
        if step.expected_pressure_min is not None and step.expected_pressure_max is not None:
            if step.expected_pressure_min > step.expected_pressure_max:
                findings.append(f"step {index} expected pressure range is reversed")
            if step.expected_pressure_max > plan.pressure_limit_bar:
                findings.append(f"step {index} expected pressure exceeds the plan limit")

    if findings:
        plan.state = PlanState.BLOCKED
    else:
        plan.state = PlanState.VALIDATED
    plan.findings = findings
    return findings
