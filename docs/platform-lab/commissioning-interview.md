# Future: agent-led commissioning interview

Stored for a later product track. **Do not build this until the dry-bench lab is done, or the operator asks.**

## Intent

A stranger can describe *their* dry bench so the platform can propose a `rig.json`. The kernel still owns limits and GPIO. A diagram is context, not permission to energize.

## Interview (agent asks, operator answers)

1. What modules are present (pots, ADC, E-stop, relay, MQTT/Modbus, other)?
2. Which customer signal is which concept (pressure, flow, temperature, …)?
3. What are the trip numbers and units?
4. Optional circuit diagram or photo path (sidecar evidence only — never Phase 3 trees).
5. What must stay observe-only?

## After the interview

- Agent proposes a signal map.
- A human applies it with `POST /v1/rig/apply`.
- Procedures that `requires_output` still need twin-gate + `CERTARIG_ENABLE_ACTUATION=1`.
- Never auto-energize from a guessed map.

## What already exists instead

Onboard is a writable config table plus a typed bench briefing. That briefing is copied into every bundle. It is not discovery.
