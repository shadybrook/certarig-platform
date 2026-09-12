---
name: dual_pot_guardrail
domain: process
procedure: procedure.yaml
intents:
  - run the dual pot test
  - prove both pots trip independently
  - verify pressure and flow guardrails together
  - qualify the two emulators
---

# Dual potentiometer guardrail

## What this proves

P1 (pressure) and P2 (flow) are independent required channels. Each can force the permit
output safe on its own. After the pressure trip the operator must reset before the flow trip
can be demonstrated; after the flow trip the output stays off until another human reset.

## When to use it

- After ADC validation of both pots.
- When you need one recorded run that shows both emulators, not two separate reports.
- After anyone suspects the two analogue inputs were swapped or aliased.

## Prerequisites

- Both signals healthy and in the safe band, E-stop released.
- Operator present at both pots.
- Node must allow output actuation.

## Operator interaction

1. Raise P1 past 4.2 bar; leave P2 alone.
2. Return P1 below 3.5 bar.
3. After the kernel resets and re-permits, raise P2 past 15.0 L/min; leave P1 alone.
4. Return P2 below 10 L/min.

The agent cannot acknowledge these moves.

## Pass criteria

- `pressure_high_forced_safe` and `flow_high_forced_safe` both observed.
- Each output-removed step within 500 ms.
- `permit_rejected_reset_required` after the second recovery.
- Peaks stay inside emulator range.

## Interpreting failures

- Only one of the two trip events: that channel did not move, or the map is wrong.
- Auto-restart after either recovery: software defect; stop and file an anomaly.
