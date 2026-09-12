---
name: thermal_soak
domain: reliability
procedure: procedure.yaml
intents:
  - run the thermal soak
  - soak the jacket
  - prove the temperature abort
  - hold temperature in band
---

# Thermal soak

## What this proves

A temperature-only rig can soak in band, abort on `abort_limits.temperature`, and write a
checksummed evidence bundle with hardware identity. No pressure channel is required.

## When to use it

- After mapping a new temperature tag (MQTT, Modbus, or simulator).
- As the stranger-path demo that the kernel is concept-generic.

## Prerequisites

- Jacket (or mapped temperature concept) healthy and below 80 °C.
- Stuck-good enabled on the channel so a frozen sensor fails the soak.

## Pass criteria

- Temperature stays below 80 °C for the soak window.
- Peak stays below the 85 °C abort.
- Run ends `safe`. Last five outcomes appear on the ledger.
