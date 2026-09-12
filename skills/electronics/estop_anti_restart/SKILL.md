---
name: estop_anti_restart
domain: electronics
procedure: procedure.yaml
intents:
  - test the emergency stop
  - verify e-stop anti-restart
  - prove the estop drops the relay
---

# E-stop trip and anti-restart verification

## What this proves

- The kernel treats an open NC1 loop on GPIO24 as an emergency stop and removes the output.
- Releasing the E-stop never restarts the output (`estop_closed_reset_required`).
- A permit request after release is rejected until a human reset.

## Operator interaction

Two physical actions, each confirmed by measurement: press the E-stop (trigger `estop_active`),
then release it (trigger `not estop_active`). The steps around the press carry `allow_estop: true`
so the runner does not treat the intended press as an abort.

## Pass criteria

- Events `estop_open_forced_safe`, `estop_closed_reset_required`, `permit_rejected_reset_required`.
- Output removed within 300 ms of the press.
- Output held off for 1 s after release with reason `reset_required`.

## Notes for the agent

The NC2 contact also removes relay board power independently of software. The runtime can only
observe the commanded state (no relay feedback is fitted on wave 1); the physical drop is
confirmed by the operator's observation of the green indicator going dark, which belongs in the
report narrative, not in the deterministic result.
