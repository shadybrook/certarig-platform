# Demo shot list

Two artifacts. Do not show auto-energize, pin OCR, or LabVIEW. Those are not true yet.

## 90 seconds, silent, captions (Apple-style)

| t | Shot | Caption |
| --- | --- | --- |
| 0–12 | Problem: a tribal bench, one person, a spreadsheet | Test benches still run on memory. |
| 12–18 | Title card | The model asks. The kernel decides. |
| 18–38 | Studio Live: dual pot traces and a trip line | Kernel owns the numbers. |
| 38–62 | Onboard: one description → Record facts → Propose map → Confirm apply | A human applies the map. |
| 62–78 | Procedures: trigger coach (which pot, live vs target) | Approved procedures only. |
| 78–86 | Evidence: zip name + SHA-256 | Checksummed evidence. |
| 86–90 | Optional 4 s of real Pi pots (sidecar 8081) then end card | CertaRig · certarig.dev |

No voice. No roadmap slide.

## 4 minutes, voice (ChatGPT-style)

You are the operator. Same loop, slower.

1. Login with the demo operator key (say it is a demo key).
2. Live: ready-to-arm, two channels, trip line.
3. Onboard: Start → paste one bench dump → Record facts → Propose → Confirm apply.
4. Procedures: start `relay_truth_table` or `pressure_guardrail`. Read the trigger coach aloud.
5. Evidence: export. Open the hash. Mention `interview.json` in the bundle.

Grok-style asides stay in this cut only, and stay short. The 90-second film stays cold.

## How to record from sim Studio

Use a **fresh** sim config copy. Interview apply mutates `rig.json` in that directory.

```bash
mkdir -p /tmp/certarig-film-cfg
cp config/rig.sim.json config/capabilities.wave1.json /tmp/certarig-film-cfg
.venv/bin/python -m certarig sim serve --port 8082 \
  --config /tmp/certarig-film-cfg/rig.sim.json \
  --capabilities /tmp/certarig-film-cfg/capabilities.wave1.json \
  --evidence-dir /tmp/certarig-film-ev
```

Then, in `studio/`:

```bash
CERTARIG_DEMO_URL=http://127.0.0.1:8082 node scripts/record_product_film.mjs
# restart sim with a fresh config copy before the next cut
CERTARIG_DEMO_URL=http://127.0.0.1:8082 node scripts/record_operator_walkthrough.mjs
```

Voiceover for the long cut: [`operator-walkthrough.md`](operator-walkthrough.md). Pi metal shot: only after [`../platform-lab/2026-09-sidecar-repeat.md`](../platform-lab/2026-09-sidecar-repeat.md).

