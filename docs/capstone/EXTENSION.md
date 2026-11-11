# CertaRig reviewed commissioning extension

Software checkpoint: 20 November 2026. Implemented locally on 9 November from `2f25d66`. The signed Phase 3 report (approved 19 September 2026, missions on pages 18–19) is the academic baseline. The dry bench and original installation are preserved.

## Operator journey

1. Start an isolated simulator using the installation commands below. Open **Onboard → Guided commissioning interview**.
2. Create a draft or select a saved interview. Enter equipment, safe state, supported procedures and source references. Load either the pressure/flow or thermal simulator template. Synthetic calibration references must remain labelled `SIMULATION_FIXTURE`.
3. Save and propose. Missing sources, identity, calibration, units, limits, contradictory units and unresolved text block the proposal. Drafts are inert and separate from the active configuration.
4. Inspect the configuration JSON, proposed diff and revalidation requirements. Only the operator applies the exact interview revision. Applying invalidates prior review and outstanding execution authority.
5. Review this simulated configuration for its supported procedure. Rehearse with an explicit approval. A passing simulator run produces a receipt bound to the procedure hash, normalized test profile and model revision. Run again with a fresh approval; the bundle records the previous rehearsal.
6. Deny a request to demonstrate refusal. A later request needs its own grant. Grants expire after restart; history survives.
7. Export the individual run and verify its ZIP in a separate process. The raw CSV, sources, calibration references, interview, changes, review, rehearsal, approval, events and deterministic analysis travel together.

The fixture agent can create/read/update/propose interviews. Bounded labelled answers (`equipment:`, `safe_state:`, `procedures:`) and structured JSON are supported. This is explicitly deterministic language routing, not a qualified LLM. Applying mappings, physical acceptance and granting approvals remain operator actions.

## Installation and reproduction

From a clean checkout of this branch, with Python 3.11+ (validation used Python 3.14.3) and uv:

```sh
uv venv .venv --python python3
uv pip install --python .venv/bin/python -e '.[dev,mqtt]'
mkdir -p work/capstone-local
cp config/rig.thermal.capstone.json work/capstone-local/rig.json
.venv/bin/python -m certarig sim serve --port 18090 --config work/capstone-local/rig.json --capabilities config/capabilities.capstone.json --evidence-dir work/capstone-local/evidence
```

Open `http://127.0.0.1:18090`. Use the simulator CLI's local demo credentials; never expose this development instance to a public network. One active rig per Edge instance. No fleet or multiuser hosting is added.

```sh
make check
make soak
cd studio
npm ci
npx playwright install chromium
npx playwright test
```

Reproduce a labelled automated approval fixture (choose a new private `--work` directory each time):

```sh
PYTHONPATH=. .venv/bin/python tools/run_capstone_demo.py --work work/reproduce-fixture --out work/reproduced-evidence --automated-approval-fixture
.venv/bin/python -m certarig evidence verify work/reproduced-evidence/CertaRig_thermal_simulator_evidence.zip
```

The scripted grants prove API behavior, not actual human review. No physical adapter is started by these commands.

## API and contracts

- GET `/v1/commissioning/templates`: labelled simulator starting profiles, not discovered equipment.
- GET/POST `/v1/commissioning/interviews`; GET/PATCH `/{interview_id}`; POST `/{interview_id}/answers`; POST `/{interview_id}/propose`.
- Update uses `expected_revision`, `answers`, nonempty `sources`, and optional bounded `text`. Atomic prior revisions are retained. Applying uses `/v1/rig/apply` with `document`, `expected_current_hash`, `interview_id`, `interview_revision`.
- Physical review is separate: operator POST `/v1/commissioning/physical` with `stage`, exact configuration/wiring identity, procedure IDs, explicit attestation and hash-bound check files.
- OpenAPI and rig/commissioning schemas are updated. EdgeClient and CertaRig SDK expose interview methods. Existing calls and default generic simulation remain compatible.

## Model and revalidation

Opt-in `hardware.simulator.plant=thermal_rc` implements the exact discrete solution of C dT/dt = Q − k(T−Ta). Parameters, seed, fixed sample interval and revision `thermal-rc-v1` are recorded; no physical heater is added. Legacy profiles retain the generic simulator. Cooling, equilibrium, heat-trip, dropout and stale-source scenarios are executable tests.

Channel changes are compared by channel ID and fields, including source, units, scaling, calibration and limits. The checklist identifies invalidated channel qualification and repeat procedures. Unclassified/rig-level changes require full qualification. This conservative rule set does not claim a mathematically minimal retest set. Receipt identity includes profile semantics and model revision, so a changed mapping, calibration, parameter or implementation revision cannot reuse an old rehearsal.

## MQTT observation

Install the mqtt extra. `config/rig.mqtt.broker.json` connects to loopback port 18883; in-process TagBus remains the default fixture for legacy profiles. Network adapters reject control requests and never publish equipment commands, including on local safe/close.

```sh
docker run --rm --name certarig-mqtt-demo -p 127.0.0.1:18883:1883 -v "$PWD/deploy/mosquitto.local.conf:/mosquitto/config/mosquitto.conf:ro" eclipse-mosquitto:2.0
CERTARIG_MQTT_TEST_PORT=18883 .venv/bin/pytest tests/contract/test_mqtt_broker.py -q
```

Payload on an exact mapped topic: `{"value":1.0,"unit":"bar","captured_at":"<current UTC ISO timestamp>"}`. Missing, malformed, wrong-unit, retained, nonfinite, stale/future or disconnected data cannot be healthy. State includes transport/connection and source timestamps. Remote equipment output state is unknown. This local anonymous broker configuration is for loopback testing only.

## Mixed sensing and physical review boundary

New Pi sources support ADC scaling, pulse flow, explicit 1-Wire identity/CRC and INA219 shunt voltage. Background per-source readers leave the deterministic sampling path unblocked by a stuck device read; old cached timestamps become stale. Python cannot kill a wedged kernel I/O transaction: independent physical cutoff remains required. Choose source-specific `max_age_ms` from measured acquisition cadence; a 1-Wire source cannot use a 20 ms freshness assumption.

Pulse zero is a valid fresh acquisition. A silent or broken pulse wire can also yield zero; independent source-health and commanded-response checks are required during physical integration. Raw measurements, coefficients, source time and quality are retained. Required electrical GPIO feedback is separate from commanded output; unknown/mismatched feedback forces a trip and safe command. INA219 measures load response, not mechanical valve position. Transition intervals bracket sampled electrical changes; they do not establish relay contact timing. New physical capstone profiles cannot issue direct reset/permit HTTP commands; output-bearing procedures must declare `requires_output` and require reviewed trial authority.

Stages are observation → attended trial → accepted, bound to adapter/configuration/wiring/calibration/procedures/reviewer. Trial authority expires after 30 minutes and restart. Each check file identifies its stage, exact config/wiring and supporting raw artifacts. The service verifies local hashes and embeds artifacts in portable bundles. It checks consistency of a human attestation; it cannot establish the truth of a forged laboratory record. Accepted procedures need passing physical trials. No real physical record has been produced in this implementation.

## Evidence and limits

Offline verification recalculates raw row counts/extrema and supported peak/event/step checks, validates approval and provenance consistency and rejects missing or corrupted artifacts. Event checks reproduce recorded software events; unsupported latency checks are disclosed as not independently reproduced. Checksums establish integrity relative to the bundle, not external authorship or certification. A reviewed profile is valid for supported mapped equipment; arbitrary novel machinery is outside this increment.

Outstanding: matched hardware design and delivered quote, physical integration/calibration, independent cutoff validation, attended 60-minute acquisition and repeated cycles, live-provider comparison, actual student rehearsal/video, final university deadline and supervisor feedback. See HARDWARE_REVIEW.md and REQUIREMENTS.md.
