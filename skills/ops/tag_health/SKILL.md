---
name: tag_health
domain: ops
procedure: procedure.yaml
intents:
  - watch tag health
  - prove mqtt dropout
  - prove a stuck register
---

# Tag health

Observe-only health check used by MQTT dropout and Modbus stuck-register twins.
The procedure never requests a permit.
