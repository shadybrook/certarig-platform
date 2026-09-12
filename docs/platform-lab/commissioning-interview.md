# Commissioning facts (not a scripted quiz)

A stranger can describe *their* dry bench so the platform can propose a `rig.json`. The kernel still owns limits and GPIO. A diagram is context, not permission to energize.

This is the same idea as plan mode: the system holds a **required-fact list**. The agent (live LLM or Fake) must figure those facts out. It may ask in any order, in its own words, one question or several. One operator dump can fill every slot.

## Facts the agent must learn

Required:

1. Modules on the bench (ADC/pots, E-stop, relay, MQTT, Modbus, other).
2. Each analogue signal: customer name, concept, unit, trip.
3. What must stay observe-only (`none` is a valid answer).

Optional:

4. Diagram notes, a path under this node's evidence dir, or a **labeled** bench photo (`POST /v1/ops/interview/image`). Never Phase 3 trees. No unlabeled pin OCR. A photo never applies or arms.

`GET /v1/ops/interview` returns `needs`, `missing`, and `known` answers. The live model reads that instead of walking a question script. Studio Onboard shows the same checklist.

## After the facts are in

- `answer_interview` records whatever this utterance taught (partial is fine).
- `propose_rig_map` (`POST /v1/ops/interview/propose`) only when `missing` is empty.
- A human applies with `POST /v1/rig/apply` (Confirm apply in Onboard).
- `interview.json` is persisted at the evidence root and copied into every run bundle.
- Procedures that `requires_output` still need twin-gate + `CERTARIG_ENABLE_ACTUATION=1`.
- Never auto-energize from a guessed map.

Prove this on a second simulator plant (`config/rig.thermal.sim.json`) before any submission Pi.
