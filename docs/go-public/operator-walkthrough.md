# 4-minute operator walkthrough — voiceover

Read this over a Studio screen recording. No slides. No roadmap. Grok-style asides stay short.

Record with:

```bash
certarig sim serve --port 8082 --config /tmp/certarig-film-cfg/rig.sim.json \
  --capabilities /tmp/certarig-film-cfg/capabilities.wave1.json \
  --evidence-dir /tmp/certarig-film-ev
CERTARIG_DEMO_URL=http://127.0.0.1:8082 node studio/scripts/record_operator_walkthrough.mjs
```

Or record yourself on the Mac and read the script below.

| t | You do | You say |
| --- | --- | --- |
| 0:00 | Login | This is a demo operator key. It stays in the tab. It is never committed. |
| 0:20 | Live | Two analog channels. Red lines are trips. Ready-to-arm is an env switch, not a chat command. The kernel owns the numbers. |
| 0:50 | Onboard → Start → paste one dump → Record facts | I describe the bench once. Modules, signals, observe-only. A photo is optional context. It never turns the relay on. |
| 1:30 | Propose map | The node proposes a diff and a next hash. I still have to apply it. |
| 1:55 | Confirm apply | Human apply. Interview cannot call permit. |
| 2:10 | Procedures → `pressure_guardrail` | Approved procedures only. The coach tells me which pot, live versus target. |
| 3:10 | Evidence → Export | Every run is a zip. SHA-256 on the export. `interview.json` is in the bundle. That is what an auditor wants. |
| 3:50 | Hold the hash | Simulator first. Same loop on metal after twin-gate. CertaRig. |

Do not show auto-energize, pin OCR, or LabVIEW.
