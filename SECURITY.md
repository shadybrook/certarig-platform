# Security

CertaRig's safety claim is a **deterministic kernel**, not a polite model. Report anything that lets an agent energise output, skip the twin-gate, or rewrite limits.

## How to report

Email the maintainer listed in `pyproject.toml` with:

- Edge version / `config_hash` / `manifest_hash` (no operator or agent keys)
- What you called, what the kernel did, and the `run_id` if a procedure was involved
- Whether `CERTARIG_ENABLE_ACTUATION` was `1`

Do not attach evidence zips that contain secrets. Do not paste keys.

## What is in scope

- An agent tool that can call `set_valve` or skip `ProcessGuardrail`
- A capability that can set `bypass_interlock` or `override_limits` to anything but `never`
- Twin-gate bypass on `raspberry_pi`
- Interview / vision attach that applies a map or arms output without a human
- Path traversal into Phase 3 trees from diagram upload

## What is out of scope

- Demo keys in the README (`sim-operator-key-000001` and friends) — change them before any real node
- SIL / IEC 61508 certification — this repo is not certified
- The systemd `WatchdogSec` — supervisor heartbeat, not a safety loop

## Hard rules we will not relax

- `bypass_interlock` and `override_limits` stay `never` for every principal
- `request_auto_arm` defaults to `never` and never calls `set_valve`
- A photo or diagram fills interview slots only. A human applies. The env switch arms.
