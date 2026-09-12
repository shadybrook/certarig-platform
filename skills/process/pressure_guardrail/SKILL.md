---
name: pressure_guardrail
domain: process
procedure: procedure.yaml
intents:
  - run the pressure guardrail test
  - verify the pressure trip
  - prove the relay drops on overpressure
  - qualify the pressure interlock
---

# Pressure guardrail verification

## What this proves

The deterministic kernel removes the permit output when the pressure concept exceeds its trip
limit, does so within the configured response time, and refuses to restore the output until a
human resets the trip. This is the single most important interlock on the bench.

## When to use it

- After any change to the pressure channel scaling, limits or wiring.
- Before an ignition-readiness or soak run.
- As part of the qualification evidence package.

## Prerequisites

- Pressure signal healthy and below 4.0 bar, E-stop released.
- Operator present at the P1 emulator; the procedure needs two manual pot moves.
- Node must allow output actuation (`requires_output: true`).

## Operator interaction

The agent relays two instructions and waits on measured triggers, never on the operator's word:

1. Raise P1 above 4.2 bar (trigger: `pressure > 4.2`).
2. Return P1 below 3.5 bar (trigger: `pressure < 3.5`).

## Pass criteria (evaluated by the runtime, not the agent)

- `permit_accepted`, `pressure_high_forced_safe` and `permit_rejected_reset_required` observed.
- Output removed within 500 ms of the trip.
- Output stays off for 1.5 s after pressure recovers, with reason `reset_required`.
- Pressure never exceeds 9.5 bar (emulator range sanity).

## Interpreting failures

- `output_removed` timeout: relay stage or GPIO23 path did not follow the kernel. Inspect hardware.
- `no_auto_restart` failed: the kernel re-energised without a reset. This is a software defect;
  stop all runs and file an anomaly report.
- Preconditions failed: pressure already above 4.0 bar or E-stop pressed. Fix the bench, retry.

## Evidence

Whole-run CSV, kernel events, step timings, peaks, and the qualification report template.
