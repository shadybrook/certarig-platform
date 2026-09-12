# Live Anthropic / OpenAI (Mac only)

Adapters already exist. CI and `make check` stay on Fake. Never put a key in the repo, GBrain, or a Studio screenshot.

```bash
# On an engineering computer — not on the submission Pi
export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY / OPENAI_BASE_URL
export CERTARIG_AGENT_PROVIDER=anthropic
.venv/bin/python -m certarig agent chat --url http://127.0.0.1:8080 --provider anthropic
```

Prove two utterances against `certarig sim serve`:

1. `commission this bench` — model asks in its own words or accepts a dump; calls `propose_rig_map` only when `missing` is empty; stops. A human applies.
2. `run the relay truth table` — `read_skill` → `run_procedure` → `wait_for_run`. If 428, explain and `request_approval`.

Studio Agent pill should leave `fake`. Keys live in `~/.env` or the shell. The pytest marker `live_llm` is skipped unless those env vars are set.

## What CI proves (and what it does not)

`make check` stays on Fake. `make_provider("anthropic")` and `make_provider("openai")` raise if the key is missing. A cloud or CI box without `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` must skip `live_llm` — that is not a failed proof, it is the rule.

The two utterances above are proven only on an engineering computer that already has a key. Do not paste a key into GBrain, a screenshot, or this repo to make the test go green.

