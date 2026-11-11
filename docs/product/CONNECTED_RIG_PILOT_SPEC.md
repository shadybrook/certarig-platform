# CertaRig connected rig pilot: implementation specification

Approved direction from the founder conversation on 7 November 2026. This specification supersedes the earlier evidence-first proposal where the two differ. Implement in the platform repository, not the frozen course submission.

## Product outcome

An invited engineer can register a supported rig, commission its connection, inspect readiness, approve a named test, run it and independently review/export the evidence. The reference Pi bench demonstrates the workflow; the product must also accommodate a user's own rig through commissioned connectors.

Audiences are small R&D teams, commissioning integrators and university labs. Use a shared workflow, not three separate products. The founder selected live AI with approvals, all three offered connector routes, and private-VPN remote self-service with limited unattended tests.

## First user workflow

1. My rigs: connect a setup or explore the labelled reference bench.
2. Commission: identify owner, components, connector, signals, units, scale, valid/safe ranges, named controls, permitted parameters, safe state, software versions and calibration references.
3. Start observe-only. Record connection, source identity, signal and scaling checks. Separate software connection from physical commissioning.
4. Show draft, connected, observation verified, control verification required or commissioned for specified procedures. Unknowns remain explicit.
5. Select a reviewed procedure; explain blockers and expected operations. Human approval binds execution to the procedure, arguments and commissioned configuration revision.
6. Run workspace: telemetry, recorder, operator stop, state/permission indicators and timeline. Show measured, controller-reported and command-derived states separately.
7. Review: time-series with units, limits/events, deterministic results and source-linked AI explanations. Compare compatible runs. Export raw data, metadata, revisions and events with verifiable checksums and a print-ready report.

A failed/missing measurement, absent recording or uncertain command is not a pass. Unsupported devices receive an integration checklist, never a false readiness badge.

## Components and interfaces

### Versioned commissioning

Extend the existing configuration and briefing rather than invent a competing rig model. Add versioned profiles and commissioning records, reviewed by a named engineer. A relevant configuration, mapping, limit, operation or adapter identity change invalidates affected readiness evidence and outstanding execution authority. Keep explicit unknown impact when dependencies are incomplete.

Extend twin readiness to relevant configuration/adapter identity, not procedure hash alone. A software simulator pass is one prerequisite and cannot replace physical acceptance.

### Three connector routes

Provide a common versioned contract for device description/capabilities, timestamped observations, named bounded operations, command outcomes and requesting the declared safe state.

* Raspberry Pi: reuse the existing GPIO/ADS1115 adapter and reconcile the canonical as-built circuit before physical work. No general UI hardcoding of its channel names or pressure/flow limits. No wiring changes for software acceptance.
* Python: provide a small local SDK plus a reviewed example that connects an existing test program. The rig owner installs its integration. No uploaded executable scripts, model-generated shell execution or arbitrary code as an agent tool.
* MQTT: use an actual broker client, not the current in-process TagBus. Include source timestamp/sequence quality, command identity, expiry and application acknowledgement. Handle duplicated/out-of-order/retained messages and reconnects. Delivery acknowledgement is not actuation feedback; do not replay retained control messages.

Controls exist only if explicitly registered and commissioned. Preserve the rig's existing controller and interlocks. Broad CNC motion, arbitrary G-code and hydraulic/production control are not accepted by this release.

Contract tests and local test devices can establish software interoperability. Label that evidence separately from a user's physical commissioning. A new customer installation remains observe-only until its owner and a qualified engineer accept its physical checks.

### AI and workspace host

The initial desktop-hosted architecture runs the UI/agent gateway on a workstation and deterministic acquisition/execution at the edge. To remove the founder laptop from the operational path, that gateway must later move to an explicitly provisioned persistent server. A transient coding sandbox is not production hosting. The Pi requires its own online connection.

Reuse the existing remote EdgeClient and neutral AgentSession/tool model. Support administrator-configured OpenAI Responses, Anthropic Messages and xAI/Grok Responses profiles, with explicit model, credential reference and request limits. Preserve a compatible endpoint extension without claiming every API is supported. Existing legacy adapters may remain for compatibility; do not silently change a user's selected model.

Provider keys stay server-side. Changing providers starts a new session. No automatic cross-provider fallback or physical command replay after API failure. Require explicit provider access and configured usage limits for live API tests; tests without keys use deterministic fixtures and are labelled accordingly.

The AI explains readiness, proposes a reviewed procedure, asks for authorization and reviews results. It never grants approval or acknowledges a physical step.

### Permissions and unattended access

Private VPN access is the chosen first route. Plan Tailscale access rules so visitors reach the workspace, not Pi management interfaces or brokers. Require application authentication as well.

Add individual identities and rig-specific roles: owner/commissioner, operator and reviewer. Only owners/commissioners edit profiles/limits or commission operations. Operators can approve/run already commissioned procedures; reviewers cannot actuate. One control lease per rig; another user cannot take over an active lease or read unauthorized evidence.

Reference unattended defaults: monitor plus approved relay/indicator routines only; at most five seconds energized per activation; at most three activations per run; fifteen-minute lease with continuous browser heartbeat. Loss of heartbeat, lease expiry or invalid telemetry cancels permission and requests the declared safe state locally. Implement and test an explicit bounded heartbeat timeout, not an unbounded browser-presence assumption.

These software measures are not independent hardware protection against every failure. Process crashes and uncertain physical state must not be reported as verified de-energization without feedback. Uncertainty blocks further execution pending reconciliation.

Physical potentiometer movements and E-stop tests remain attended. No remote or AI acknowledgement of those actions. Existing relay and indicator states remain labelled expected/command-derived unless feedback hardware is actually fitted and tested.

### Evidence and recovery prerequisites

Persist approval history and invalidate outstanding grants after restart. Fix approval propagation through ToolRegistry -> EdgeClient -> procedure start. Bind exact procedure/arguments/configuration revision to approval; prevent replay.

Do not automatically restore output after reconnect, reset or restart. Preserve unknown/blocked states and reconcile observed state before fresh permission. Device-source freshness is distinct from HTTP receipt time.

Fix individual-run exports so they include the referenced raw recording. Verify path safety, content hashes, missing/corrupt artifact reporting and portable offline review. Hashes alone are not certification.

Do not store credentials, private network addresses or raw authentication material in reports, transcripts, source or durable project memory.

## Delivery order

1. Reusable commissioning: profiles, review/status flow, all three connector implementations and shared contract tests.
2. Connected workflow: integrated UI, live AI plumbing, durable approval/recovery, complete evidence review/export.
3. Private remote pilot: named users/roles, leases/heartbeat, VPN runbook and locally commissioned reference bench. No unattended physical access until local acceptance.

Deliver reviewable commits and a draft pull request. Do not merge automatically or deploy to hardware. Keep interface additions documented and maintain the existing simulator, SDK and approval paths unless an intentional compatibility change is documented and tested.

## Acceptance

* A second rig profile does not require editing application source.
* Missing channels, wrong units, unknown controls, stale signals and uncommissioned configurations block readiness.
* All connectors pass shared tests; MQTT uses a real disposable broker in integration tests.
* Denied, expired, replayed, wrong-user or configuration-mismatched approval cannot execute.
* AI failure cannot stop local recording or grant output authority.
* Each enabled live provider passes the same opt-in evaluation; absent credentials are a reported untested gate.
* Individual-run export contains the raw samples necessary to reproduce displayed results; removed/corrupted files fail verification.
* Invitation, permissions, rig isolation, single control lease, disconnect, expiry and restart paths are tested.
* Manual acknowledgement is unavailable to AI and unattended procedures.
* Hardware gates are only recorded as passed following actual observed physical checks. No real machine access or certification is inferred from software tests.

## Frozen submission boundary

Never run deploy/install_pi.sh on the existing course-submission installation. It can replace deployed files. Use a separate platform SD card for future physical testing, and require explicit founder participation. Do not change the frozen repository or existing submission evidence to make software tests pass.
