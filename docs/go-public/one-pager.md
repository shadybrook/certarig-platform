# CertaRig — one-pager for pilots and investors

**The model asks. The kernel decides.**

CertaRig is a test-operations platform for a *mapped* rig. An agent interprets intent and gathers facts. Deterministic code compares numbers, owns trips, and is the only path to the output. Every run leaves a checksummed evidence bundle.

Public name: **CertaRig**. Schemas already cite `https://certarig.dev`. Confirm that domain before printing stickers. GitHub: `shadybrook/certarig-platform`. License: MIT (kernel you can audit). Charge later for hosted Studio, support, and signed skill packs.

## Who it is for

R&D labs and HIL cells that today run “LabVIEW + a person.” They can declare signals and limits, let the kernel own trips, let an agent run only approved procedures, and hand an auditor a zip with hashes.

## What is true today

- Simulator / Docker stranger path: interview → human apply → twin-gate stamp → procedure → export
- Fact-gathering interview (required slots, not a quiz). Propose only. A human applies.
- Dry-bench sidecar on a Pi (port **8081**, 12 Sep 2026): observe, then actuated ladder. Kernel owned the trips. Phase 3 on **8080** stayed frozen.
- Capability contract: ALLOWED / HUMAN_APPROVAL / NEVER. `bypass_interlock` and `override_limits` cannot be called.
- Twin-gate: a Pi procedure will not start unless that hash passed on the simulator in the last 24 hours.
- `CERTARIG_ENABLE_ACTUATION` defaults to 0. Interview never calls permit.

## Ask

2–3 design-partner pilots on *their* mapped bench (our node, their signals). Use of funds: vision propose from a labeled photo, real MQTT/Modbus/OPC-UA observe, SSO for anyone who is not us.

## Not claiming

- Unknown-bench pin OCR as a product
- Silent auto-energize from a guessed map (the optional `request_auto_arm` tool is **never** by default and still cannot skip apply, twin-gate, or the env arm)
- SIL certification
- Installing this repo over someone else's frozen demo

## Proof to show in a room

1. Ninety-second silent film of Studio on the simulator.
2. 12 Sep sidecar Gates 0–5 write-up (`docs/platform-lab/2026-09-12-dry-bench.md`).
3. This month's repeat sidecar lab (same host, Phase 3 restored) plus a live Anthropic/OpenAI chat on the Mac against sim — keys never in git.
