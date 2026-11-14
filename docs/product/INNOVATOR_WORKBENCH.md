# CertaRig Innovator Workbench

The product is a local software workspace for engineering bench owners. A project groups benches; it grants no equipment permissions. A task selects one permitted bench. Independent agents and reviewed supervisor teams share the existing customer lifecycle.

## Open the product

From the repository root, use Python 3.11+ and Node 20+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,platform,mqtt,serial]'
cd studio
npm ci
cd ..
.venv/bin/python -m certarig platform init-demo
```

`init-demo` creates private local settings and distinct Author/Reviewer accounts. It refuses to overwrite an existing installation. Follow `docs/product/AGENT_LIFECYCLE.md` to start Dex, the two simulator Edges, the qualified Sandbox broker, the platform and the separate observation runtime. Open **http://127.0.0.1:18090/**. Application identity and model consent remain separate.

Genuine Dex/Codex sign-in and the Sandbox image/seven real-container qualification cases are the next verification stage. Fixture-provider tests are not substitutes. A broker without qualified isolation refuses execution; no submitted source runs on the host.

## Workspace

- **Benches:** projects, explicitly granted benches, conversations and immutable agent/team versions.
- **Commission:** deterministic guided drafting, questions/requirements, editable proposals, optimistic revision checking and explicit immutable save. Advanced permissions expose reviewed analysis tools and lower runtime limits. The readiness output contract remains fixed in this release.
- **Review:** five evaluation cases, independent deployment review, health/lease monitoring, revocation and ordered task activity. Collection and qualification run as separate cancellable background tasks.
- **Teams:** select an evaluated supervisor and one to three evaluated specialists on the same bench. The independent review covers the complete exact-version team. Tools, models, profile, member evaluations and operating limits are bound together.
- **Sandbox:** author immutable Python/SPICE definitions, declare inline input/output schemas and one to three exact expected-output tests, run tests, obtain independent review, and inspect inert artifacts. Changed source is a new tool definition and requires new tests/review. No dependency installation is allowed inside jobs.
- **Connectors:** propose public channel mappings and calibration/limits. Review produces an installation proposal, not an applied configuration. Endpoints, device paths and credentials stay in operator-controlled Edge settings.
- **Evidence:** filter deployment records, verify complete exported bundles and download them. Inspect raw observation/tool traces in each deployment; analysis results and artifacts are available under Sandbox.

Drafts use revision checks. A conflicting tab must reload the saved draft; it cannot overwrite another revision silently. Messages and artifacts render as text; PNGs are the only image preview format. Raw HTML is never rendered.

## Teams and execution boundaries

Delegation is sequential, depth one, with at most three selected specialists. The supervisor can suggest a new specialist but the suggestion cannot run. Native Codex delegation remains disabled; CertaRig orchestrates existing `AgentSession` instances.

The team uses the most restrictive selected member bounds: minimum model calls, assessment count and lease, maximum interval. At most eight model calls are shared across one assessment, ten assessments per lease, one active local deployment and a maximum 15-minute lease. Selecting stricter limits can intentionally make a team unable to complete its test; evaluation uses those same limits.

Every member/tool checks current membership, asset grant and exact review bindings. Revocation blocks new work, cancels current inference/jobs and discards late results. Runtime and control-plane restart restore history without authority. Recording stays in Edge's independent acquisition path.

Analysis tools receive copied measurements and parameters through `/scratch/parameters.json`, plus an immutable public profile snapshot at `/scratch/snapshot.json`. Imported data, when selected, is `/scratch/recording.csv`. They write `/out/result.json` matching the declared output schema; other allowed artifacts can be inspected. Analysis results never become trusted commissioning receipts. A deployment can call only its selected, independently reviewed tool versions through the broker.

CSV imports require `channel_id,value,unit,captured_at,quality`. Imported provenance is labelled unverified; replay cannot claim live acquisition or physical qualification.

## API additions and compatibility

See `/v1/openapi.json` for the complete platform contract. New families are `/v1/projects`, `/v1/drafts`, `/v1/tasks`, `/v1/teams`, `/v1/tools`, `/v1/analyses`, `/v1/replays`, `/v1/connector-profiles`, `/v1/evidence` and `/v1/workbench-tools`.

`POST /v1/tasks` accepts `kind` (`evaluate`, `qualify`, `team_evaluate`) and `target_id`. Read progress at `/v1/tasks/{id}`; request ordered events with `POST /v1/tasks/{id}/events` and `{"after": 0}`; cancel through `/cancel`. Task events use audit sequence cursors. No queued/running work resumes after restart.

Draft updates require `expected_revision`; committing requires the current revision and resolved blockers. The authoring-tool manifest exposes draft collection, evaluation submission and reviewed analysis only. No agent tool can apply profiles, grant permissions or approve deployment.

The existing synchronous agent evaluation APIs and legacy Edge Studio remain compatible. Ordinary historical exports retain `certarig-agent-evidence/1`; workspace/team/analysis exports use `/2`. Both formats support offline verification:

```sh
.venv/bin/python -m certarig platform verify /absolute/path/to/bundle.zip
```

Version 2 requires selected member/tool definitions, conversation provenance, connector proposals, replay records and every submitted deployment analysis. Nested Sandbox bundles include source, parameters, snapshots, logs, engine/resource records, artifacts and checksums. Verification checks cross-bindings and completeness without executing exported code. Hashes establish integrity/internal consistency, not authorship: compare the manifest digest with a trusted original.

## Demonstration sequence

1. Author selects the thermal bench and creates a commissioning draft.
2. Add a freshness/calibration requirement; inspect the proposed instructions and tool permissions. Save and reopen the draft, then commit its exact version.
3. Collect evaluation traces in the background. Inspect nominal success, stale-data refusal, wrong-unit refusal, forbidden action and wrong-asset refusal.
4. With qualified isolation, obtain a trusted Sandbox pass. Reviewer inspects the exact version and approves observation. Start the separate runtime, observe health, then revoke access.
5. Repeat using two evaluated independent versions as a supervisor team; inspect recorded delegations and its shared budget.
6. Test and review an analysis tool; inspect its raw artifacts. Propose MQTT/serial/Modbus mappings without granting physical authority.
7. Export a bundle and verify it offline. Remove a required file or alter source/parameters: verification must fail.

The coding evidence uses clearly labelled identity/provider/engine doubles. Complete genuine identity, live-provider and container verification before claiming a qualified demonstration. Physical connector commissioning, public hosting and equipment actuation remain separate gates.
