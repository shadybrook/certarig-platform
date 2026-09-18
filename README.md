# CertaRig

A user-deployable test-operations platform. The LLM interprets and asks; deterministic code compares numbers, enforces limits and drives the output. The agent reaches the rig only through the Edge API, filtered by a capability manifest.

This repository is **not** the 20 Sep Phase 3 course submission. That demo stays frozen on the Pi (`certarig_edge` live-dashboard on port 8080). Do not run `deploy/install_pi.sh` on that host. The dry bench is an optional lab, not the design target.

```
Studio (browser)  ──►  Edge node  ──►  ProcessGuardrail  ──►  GPIO23 / simulator
                          │                    ▲
                     procedures,               │
                     approvals, evidence       └─ trip / E-stop / invalid sensor
                     agent tools
```

The Phase 3 PoC that this was imported from is frozen. This repo is the platform.

## Gate 0–5 evidence review and visual explainer

The 12 September dry-bench progression is analysed as six gates, numbered Gate 0 through Gate 5. The review distinguishes measured evidence from interpretation and documents the product direction that follows from the lab.

- [Evidence and product-direction report](deliverables/CertaRig_Gates_0_to_5_Evidence_and_Product_Direction.pdf) ([editable DOCX](deliverables/CertaRig_Gates_0_to_5_Evidence_and_Product_Direction.docx))
- [Phase 3 film pack](docs/explainer/phase3-film/ANIMATION.md) — paper explainer clips, then the designed Studio|bench split
- [Phase 3 submission film script](deliverables/CertaRig_Phase3_Submission_Film_Script.docx)
- [Visual explainer video script](deliverables/CertaRig_Visual_Explainer_Video_Script.pdf) ([editable DOCX](deliverables/CertaRig_Visual_Explainer_Video_Script.docx))
- [Source analysis](docs/explainer/2026-09-13-gates-0-to-5-analysis.md) and [lab explainer script source](docs/explainer/2026-09-13-video-script.md)
- [Derived hardware-run summary](docs/explainer/data/hardware_run_summary.csv), [evidence verification record](docs/explainer/data/evidence_verification.json), and [visual assets](docs/explainer/assets/)

Rebuild the derived data, plots, and editable documents with the scripts in `tools/`. The hardware exports preserve run metadata, checks, events, peaks, sample counts, and recording hashes, but do not contain the referenced raw physical CSV recordings. Accordingly, the report does not reconstruct or invent physical waveforms.

## Clone to a simulated run (under ten minutes)

You need Python 3.11+ (3.13 is fine) and Make. Node 20 is only required for Studio end-to-end tests.

```bash
git clone <this-repo>
cd CertaRig_CursorControl
make install
make check                          # lint, types, unit/contract/agent/property/scenario, 90% coverage
.venv/bin/python -m certarig sim serve --port 8080
```

Or, without a local venv:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Open http://127.0.0.1:8080/ and sign in with the demo operator key (`sim-operator-key-000001`). Optional auditor key: `sim-auditor-key-000001` (read-only). Then:

1. **Live** — ready-to-arm scorecard, generic channel meters, and on the simulator sliders for every mapped signal.
2. **Onboard** — preview a config diff (for example add a temperature channel) and apply it. MQTT and Modbus TCP are real observe-mode adapters. Save a bench briefing (P1/P2/E-stop/relay notes); it is copied into every evidence bundle.
3. **Author** — pick the soak template, bind a signal, validate, save a draft, approve it. No LLM required.
4. **Procedures** — run `relay_truth_table`, `pressure_guardrail`, `flow_guardrail`, `dual_pot_guardrail`, or `thermal_soak` (use `config/rig.thermal.sim.json`).
5. **Approvals** — grant or deny agent requests (`reset_trip`, `shutdown`). A 428 from the agent deep-links here.
6. **Agent** — type `run the relay truth table`. The pill shows Fake vs Anthropic/OpenAI. Default is Fake.
7. **Evidence** — export a checksummed zip; every bundle names the adapter class and hostname. Outcomes land in `evidence/ledger/outcomes.jsonl`.

From the shell, the same path:

```bash
CERTARIG_AGENT_KEY=sim-agent-key-0000000001 \
  .venv/bin/python -m certarig agent run --url http://127.0.0.1:8080 \
  "run the relay truth table"

.venv/bin/python -m certarig sim run-library --out /tmp/certarig-sim-lib
.venv/bin/python -m certarig evidence pull --url http://127.0.0.1:8080 \
  --operator-key sim-operator-key-000001 --out /tmp/pulled

# SDK (same 50-line path)
python - <<'PY'
from certarig.sdk import CertaRig
rig = CertaRig("http://127.0.0.1:8080", "sim-operator-key-000001")
print(rig.health()["ready_to_arm"])
print(rig.live()["guardrail"]["reason"])
print(rig.run("relay_truth_table")["run_id"])
print(rig.pull_evidence("/tmp/pulled-sdk")["saved_to"])
PY
```

## What is deterministic vs what is the model

| The kernel / runner | The agent |
| --- | --- |
| Compares numbers to limits | Chooses which *approved* procedure to run |
| Owns GPIO23 | May `force_safe` on its own |
| Anti-restart (`reset` before `permit`) | Needs a human to `reset_trip` or `shutdown` |
| Ends every run with `safe` | Cannot acknowledge a physical step |
| Writes CSV, `run.json`, `report.md`, SHA256 | Writes a transcript and an optional narrative, labelled as narrative |

`bypass_interlock` and `override_limits` do not exist as callable tools.

## Repository layout

| Path | Role |
| --- | --- |
| `certarig/edge/` | Kernel, Edge HTTP API, procedures, ops, evidence |
| `certarig/sim/` | Digital twin, scenario DSL, invariants |
| `certarig/agent/` | Provider-neutral orchestrator (Fake / Anthropic / OpenAI) |
| `certarig/schemas/` | Rig, procedure, capability, scenario, evidence contracts |
| `skills/` | Documented procedures (`SKILL.md` + `procedure.yaml` + scenarios) |
| `studio/` | Operator console (vanilla ESM, served by the Edge node) |
| `deploy/` | systemd unit, sudoers rule, `install_pi.sh` |
| `config/` | Example rig / capability documents — **no secrets** |

## Tests

```bash
make test-fast      # unit + contract + agent
make property       # Hypothesis state machine on the kernel
make scenario       # every shipped scenario against the twin
make soak           # one simulated hour, accelerated
make e2e            # Playwright against `certarig sim serve` (needs Node 20)
```

Hardware-in-the-loop tests are marked `hil`. Platform HIL defaults to port **8081** and skips unless `/health` has `ready_to_arm`. Phase 3 on `:8080` is checked only as “still the frozen dashboard.” `make check` never requires the Pi.

A procedure whose hardware mode is `raspberry_pi` will not start unless the same procedure hash has passed on the simulator within the last 24 hours (the digital-twin gate). Simulator passes write `evidence/twin_gate/<hash>.json`.

## Raspberry Pi (new install only)

`deploy/install_pi.sh` is for a **new** user Pi. It is unsafe on the Phase 3 submission host: it rsyncs `--delete` to `/opt/certarig` on port 8080 and will refuse if it finds `certarig_edge/cli.py`. The systemd unit’s `WatchdogSec=30` is a supervisor heartbeat, not a SIL loop.

`CERTARIG_ENABLE_ACTUATION` stays `0` until the bench has been inspected. `POST /v1/ops/shutdown` still needs a human approval, refuses while a procedure run is active, forces the kernel safe, flushes evidence, then runs `CERTARIG_POWEROFF_CMD` if set.

## LLM providers

The default is `fake` (rule-based policy). To use a real model on an engineering computer — not on the Pi:

```bash
export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY / OPENAI_BASE_URL
export CERTARIG_AGENT_PROVIDER=anthropic
.venv/bin/python -m certarig agent chat --url http://127.0.0.1:8080 --provider anthropic
```

Adapters are untested live in this tree; every CI path uses FakeProvider.

## Safety notes

- The kernel is the only thing that may energise GPIO23.
- Operator keys must be at least 12 characters and must differ from the agent key.
- Change any password that has ever been pasted into a chat window.
- `.env`, `/etc/certarig/`, and `~/.ssh` are the only places keys belong.

## Provenance

Imported from the frozen PoC at commit `23988a3`. See `docs/PROVENANCE.md`.
