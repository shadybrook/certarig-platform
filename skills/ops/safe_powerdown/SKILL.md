---
name: safe_powerdown
domain: ops
procedure: procedure.yaml
intents:
  - shut down the rig
  - power down the pi
  - safe shutdown
  - i want to switch the bench off
---

# Safe power-down of the edge node

## Sequence the agent follows

1. Run this procedure. It forces safe, verifies no recording is active, and waits for the
   operator to confirm the bench state.
2. Call `export_evidence` so every run since boot is bundled and checksummed.
3. Call `shutdown`. On wave 1 this needs a human approval; request it with the reason
   "bench work complete" and wait for the operator to grant it in Studio.
4. Tell the operator to wait for the SD activity LED to go idle, then remove PWR IN and the
   external 5 V supply.

## Why a procedure and not just the shutdown tool

On 2026-09-12 the shutdown was improvised over SSH: a live recorder was still writing, the
data had to be pulled by hand and checksummed, and the password travelled through a chat
window. Every one of those steps is now either a deterministic step here or a manifest-governed
tool call with an audit entry.

## What the agent must not do

- Do not stop a recording that belongs to an active procedure run; abort the run instead.
- Do not request `shutdown` while a procedure run is active.
- Do not claim the supplies are removed; only the operator can confirm that.
