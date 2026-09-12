---
name: flow_guardrail
domain: process
procedure: procedure.yaml
intents:
  - run the flow guardrail test
  - verify the flow trip
  - prove the relay drops on overflow
  - qualify the flow interlock
---

# Flow guardrail verification

## What this proves

The deterministic kernel removes the permit output when the flow concept exceeds its trip
limit (P2 / `safe_max` 15.0 L/min), does so within the configured response time, and refuses
to restore the output until a human resets the trip.

## When to use it

- After any change to the flow channel scaling, limits or wiring.
- After ADC validation of P2.
- As part of the qualification evidence package, paired with the pressure guardrail.

## Prerequisites

- Flow signal healthy and below 14.0 L/min, pressure still in the safe band, E-stop released.
- Operator present at the P2 emulator; the procedure needs two manual pot moves.
- Node must allow output actuation (`requires_output: true`).

## Operator interaction

The agent relays two instructions and waits on measured triggers, never on the operator's word:

1. Raise P2 above 15.0 L/min (trigger: `flow > 15.0`).
2. Return P2 below 10 L/min (trigger: `flow < 10.0`).

## Pass criteria (evaluated by the runtime, not the agent)

- `permit_accepted`, `flow_high_forced_safe` and `permit_rejected_reset_required` observed.
- Output removed within 500 ms of the trip.
- Output stays off for 1.5 s after flow recovers, with reason `reset_required`.
- Flow never exceeds 19.5 L/min (emulator range sanity).

## Interpreting failures

- `output_removed` timeout: relay stage or GPIO23 path did not follow the kernel. Inspect hardware.
- `no_auto_restart` failed: the kernel re-energised without a reset. This is a software defect;
  stop all runs and file an anomaly report.
- Preconditions failed: flow already high, pressure already unsafe, or E-stop pressed. Fix the bench, retry.

## Evidence

Whole-run CSV, kernel events, step timings, peaks, and the qualification report template.
