# CertaRig

A test-operations platform for a real low-voltage dry bench. The LLM interprets and asks; deterministic code compares numbers, enforces limits and drives the output. The agent reaches the rig only through the Edge API, filtered by a capability manifest.

```
Studio (browser)  ──►  Edge node  ──►  ProcessGuardrail  ──►  GPIO23 / simulator
                          │                    ▲
                     procedures,               │
                     approvals, evidence       └─ trip / E-stop / invalid sensor
                     agent tools
```

The Phase 3 PoC that this was imported from is frozen. This repo is the platform.

## Clone to a simulated run (under ten minutes)

You need Python 3.11+ (3.13 is fine) and Make. Node 20 is only required for Studio end-to-end tests.

```bash
git clone <this-repo>
cd CertaRig_CursorControl
make install
make check                          # lint, types, unit/contract/agent/property/scenario, 90% coverage
.venv/bin/python -m certarig sim serve --port 8080
```

Open http://127.0.0.1:8080/ and sign in with the demo operator key printed at startup (`sim-operator-key-000001`). Then:

1. **Live** — telemetry and, on the simulator, sliders for the two pots plus an E-stop toggle.
2. **Procedures** — start `relay_truth_table` (fully automatic) or `pressure_guardrail` (raise P1 past 4.2 bar, then bring it back below 3.5).
3. **Approvals** — grant or deny agent requests (`reset_trip`, `shutdown`).
4. **Agent** — type `run the relay truth table`. No LLM API key is required; a transparent rule-based policy drives the same tools a real model would.
5. **Evidence** — export a checksummed zip (`SHA256SUMS.txt` + `export_manifest.json`).

From the shell, the same path:

```bash
CERTARIG_AGENT_KEY=sim-agent-key-0000000001 \
  .venv/bin/python -m certarig agent run --url http://127.0.0.1:8080 \
  "run the relay truth table"

.venv/bin/python -m certarig sim run-library --out /tmp/certarig-sim-lib
.venv/bin/python -m certarig evidence pull --url http://127.0.0.1:8080 \
  --operator-key sim-operator-key-000001 --out /tmp/pulled
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

Hardware-in-the-loop tests are marked `hil` and skip unless `certarig-pi.local:8080` answers. The bench is not required for `make check`.

A procedure whose hardware mode is `raspberry_pi` will not start unless the same procedure hash has passed on the simulator within the last 24 hours (the digital-twin gate). Simulator passes write `evidence/twin_gate/<hash>.json`.

## Raspberry Pi (wave-1 bench)

The Pi (`certarig-pi.local`, user `chintan`) is installed with:

```bash
sudo deploy/install_pi.sh
```

That creates `/etc/certarig/edge.env` (operator and agent keys, shown once), copies `config/rig.wave1.json`, enables `certarig-edge.service`, and installs a sudoers rule that allows **only** `systemctl poweroff`. Keys never go in the repo or in chat.

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
