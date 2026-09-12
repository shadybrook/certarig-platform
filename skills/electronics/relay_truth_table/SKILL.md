---
name: relay_truth_table
domain: electronics
procedure: procedure.yaml
intents:
  - run the relay truth table
  - cycle the relay
  - check the permit output follows commands
---

# Relay command truth table

Fully automatic. Three safe/reset/permit/safe cycles, then a permit without reset that must be
rejected. Confirms the commanded output and the expected indicator model
(red = inhibited, green = permitted) after every command.

Use it as a quick health check before longer procedures, and after any change to the
transistor stage, relay board or indicator wiring. On the real bench the operator should
watch the indicators change with each cycle and note any mismatch in the report narrative.
