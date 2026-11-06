# CertaRig scheduled cloud build work order

Requested by the founder: 7 November 2026 at 09:00 Asia/Kolkata, equivalent to 2026-11-07T03:30:00Z. One run, not a daily recurrence. Scheduling time is requested, not proof a schedule has been created.

## Source

Repository: https://github.com/shadybrook/certarig-platform

Source branch: research/machine-control-2026-11-07

Read CONNECTED_RIG_PILOT_SPEC.md in this directory for the approved specification. The earlier product-development-plan document is background and is superseded by the specification on live connected workflow, audiences and initial connector scope.

## First unattended implementation run

Implement reusable commissioning and the evidence/approval prerequisites, then extend toward the integrated connected workflow in reviewed increments. Scope the run to software work that can be independently tested in the cloud.

1. Inspect the repository, AGENTS instructions, existing APIs, UI, tests and relevant skills. Preserve all unrelated work and the frozen course submission.
2. Establish baseline tests. Extend existing rig/config/briefing models into versioned commissioning profiles and statuses; add reviewed mapping/readiness UI without Pi-specific global assumptions.
3. Implement the shared connector contract with Pi compatibility, reviewed Python SDK/example and actual MQTT broker integration. Use disposable test fixtures/broker to verify behavior.
4. Fix per-run raw recording inclusion, approval-id forwarding and persisted approval/restart invalidation, with regression tests.
5. Add tests demonstrating that another profile works without source edits, stale/missing/mismatched inputs block readiness, and unsupported/unknown actions never dispatch.
6. Run relevant lint, type, unit, contract, integration and browser checks. Report exact commands and failures, not just a summary claim of passing.
7. Commit on a separate implementation branch and open a draft pull request if authorized GitHub access is available. Do not merge or deploy. Report changed interfaces, demonstrated behavior, missing prerequisites and the next bounded work item.

If a dependency prevents the entire scope, finish a coherent tested increment and clearly identify what remains; do not report the platform complete after a partial implementation.

## Permissions and cost limits

Use the user's existing cloud-task entitlement only. No new paid service provisioning, purchases, API charges, subscriptions, credentials or external outreach are authorized by this work order. Provider integrations may be coded and fixture-tested, but live provider calls wait for explicit credentials and spending limits. Do not infer that a ChatGPT subscription supplies every provider's API access.

No SSH into the rig, network discovery of private devices, GPIO writes, relay actuation, hardware deployment, production hosting changes or university submission modifications. Physical acceptance remains pending the founder and the bench.

Do not copy secrets, local memory files, machine-specific absolute paths or private addresses into GitHub. Evidence generated from software fixtures must say simulated/fixture/software integration, not physical validation.

## Scheduler requirements

Use a real server-side cloud schedule with the source branch available remotely. Do not substitute a local desktop automation, a sleeping shell, a timed local process or instructions that rely on this laptop remaining online.

Record the returned schedule/task identifier, scheduled time, target repository/branch and resulting run/PR in a receipt after they actually exist. If scheduling is unavailable, explicitly report it as not scheduled. Do not mark this requested work order as an active schedule by itself.
