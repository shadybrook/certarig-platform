# CertaRig capstone checkpoint

The current extension is documented in [EXTENSION.md](EXTENSION.md), with [signed mission/rubric mapping](REQUIREMENTS.md) and [hardware design/procurement holds](HARDWARE_REVIEW.md). Start there. The older workflow notes below describe the initial baseline; current results are in the release validation receipt.

# CertaRig capstone connected workflow

Working milestone: 20 November 2026. This increment delivers configuration-only thermal simulator onboarding, reviewed readiness, human-approved execution and a portable raw-data evidence bundle. The final university submission date is unconfirmed.

## Run locally

```sh
make install
mkdir -p work/capstone-local
cp config/rig.thermal.capstone.json work/capstone-local/rig.json
.venv/bin/python -m certarig sim serve --port 18090 --config work/capstone-local/rig.json --capabilities config/capabilities.capstone.json --evidence-dir work/capstone-local/evidence
```

Open http://127.0.0.1:18090. This is a loopback-only simulator. The simulator CLI prints/uses its documented demo operator key; these demo keys are not suitable for a remote installation. Leave `CERTARIG_AGENT_PROVIDER=fake` (the default). No live provider calls are needed.

1. Sign in as an operator. Onboard shows the active rig and a full configuration editor. Change channel IDs, concept mappings, units, limits or source metadata in this configuration, preview the diff, then apply. The simulator reloads the mapping without application-source edits.
2. Select **Jacket thermal soak** in the commissioning review and explicitly review the current configuration. `simulation_ready` is software readiness, never physical acceptance.
3. In Procedures, choose the thermal soak and Start. The first start is blocked until commissioning. After commissioning it opens an approval request showing exact arguments and the requesting principal.
4. Deny the first request to demonstrate refusal. Start again, inspect the request and grant it. This explicit operator action permits one run only. The local runner determines its result.
5. Evidence → **Export this run** downloads a ZIP with raw CSV, configuration, commissioning review, consumed approval history, procedure revision, events, deterministic report, sample summary and checksums.
6. Verify the downloaded ZIP offline:

```sh
.venv/bin/python -m certarig evidence verify path/to/downloaded.zip
```

The verifier checks artifact hashes, recording references and the sample summary recalculated from CSV. It rejects missing/corrupt files and unsafe ZIP paths. Checksums establish internal consistency, not an externally signed attestation or safety certification.

## Reproducible automated demonstration

```sh
PYTHONPATH=. .venv/bin/python tools/run_capstone_demo.py --work work/demo-runtime-1 --out work/demo-outputs-1 --automated-approval-fixture
```

The runtime directory must not already exist. The explicit flag allows the demonstration harness to exercise the operator API; its receipt labels this as an automated approval fixture, not a human-attended test or live-model qualification. Manual approval is demonstrated separately through the browser UI tests.

## Interface additions and compatibility

- `commissioning_required` in rig configuration opts into the new enforcement. It defaults to false for legacy profiles. The supplied capstone profile enables it; the workspace cannot switch it off at runtime.
- `GET /v1/commissioning?procedure_id=thermal_soak` returns readiness, blockers, evidence kind, configuration/adapter identity and the current review. Omit the query for reviewed procedures as a group.
- `POST /v1/commissioning/review` takes `expected_config_hash` and a nonempty `procedure_ids` list. Only an operator can review. Software review accepts simulator/mock profiles only; physical acceptance remains unavailable.
- `POST /v1/procedure_runs` accepts optional `approval_id`; it is required for all principals in a capstone profile. The client and SDK retain their existing entry points. Existing callers receive a structured 428 when approval is needed.
- Approval records bind role and principal name, exact arguments, current contract, adapter and procedure hash. Denial, expiry, consumption and restart invalidation are retained in `approvals.json`. Pending/granted authority expires on every process restart, including clean restarts.
- Configuration changes invalidate grants and require a new matching review. Configuration is refused while a recorder/run owns the rig. Unsupported physical identity changes are rejected without rewriting the active file. Simulator maps hot-reload under the same runtime lock.
- The OpenAPI snapshot documents the added routes and procedure-start responses. `commissioning.schema.json` validates stored reviews.

Existing operator/agent credentials are shared role credentials with caller-supplied display names. Principal binding prevents accidental cross-client use within that model; independent authenticated user identities, roles and rig isolation remain a later pilot milestone.

## Validation commands

```sh
make check
make property
make scenario
make soak
make e2e
.venv/bin/pytest tests/contract/test_capstone_workflow.py -q
```

`make check` includes lint, mypy and the existing 90% coverage gate, excluding HIL, live-model and slow tests. Browser acceptance configures a second rig, demonstrates blocked readiness and denial, grants a request, completes a run and downloads its evidence. The fixture evaluation covers skill routing, unsupported tool refusal, inability to acknowledge physical steps, approval waiting and provider failure during acquisition.

## Claim boundaries

This increment is local simulator software. No Pi deployment, new wiring, water loop, live-provider evaluation, remote service, real MQTT broker qualification or unattended physical operation was performed. The physical Phase 3 package is historical evidence and is unchanged. Generic MQTT/Modbus scaffolds are not qualified network connectors.

Preserved thermal procedure checks use degrees Celsius; unconverted Kelvin/other engineering units are blocked for these reviewed procedures. Unsupported units need an explicit compatible procedure/conversion, not relabelling. The first new sample and continuing source timestamps must be valid; stopping acquisition or a non-advancing source blocks readiness. Physical interlocks remain independent of the agent.

## Academic delivery

The report follows the supplied six-chapter outline and formatting requirements. The ten-slide deck follows the university template. Future progress rows are planned, not completed. Supervisor remarks, approval of scope, current supervisor assignment, academic year, final deadline and student declaration remain for authentic confirmation. No supervisor email has been sent.
