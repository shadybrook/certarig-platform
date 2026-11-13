# CertaRig: customer-created agents with reviewed deployment

## 1. Goal and first demonstration

Continue from **PR #7, commit `f877d82`**. Reuse Studio, `AgentSession`, the tool registry, commissioning, approvals and evidence infrastructure.

Build one complete local workflow:

**Authenticate → enroll a simulated bench → create an agent → evaluate in Sandbox → obtain independent human review → deploy in observation mode → monitor → export evidence → revoke.**

The demonstration will use:

- One organization with separate **Author** and **Reviewer** accounts.
- Bench A: the thermal simulator.
- Bench B: the pressure/flow simulator.
- One customer-created commissioning agent.
- One genuine local Codex-backed evaluation and deployment.

The Author can use Bench A. The Reviewer can inspect both benches. The deployed agent receives access only to Bench A.

## 2. Implementation changes

### Application identity and asset access

- Add a local control-plane mode. Keep the existing Edge mode and APIs compatible.
- Use a local [Dex OIDC issuer](https://dexidp.io/docs/connectors/local/) for the demonstration. Use Authorization Code with PKCE, state and nonce validation.
- Use Requests-OAuthlib and PyJWT with cryptographic verification. Validate the configured issuer, audience, signature and token expiry.
- CertaRig creates its own expiring server-side sessions. Browser-supplied names, roles and organization IDs cannot grant access.
- Store users, memberships, asset grants, sessions and lifecycle records in SQLite transactions. Keep model and connector secrets outside exported records.
- Use loopback-only development services. Hosted HTTPS deployment is a later gate.

Enroll the two simulator instances with single-use pairing codes. Generate separate connector credentials for each asset. Store those credentials on the server; never expose them to browser clients or models.

The first connector supports registered local Edge simulators only. Arbitrary URLs, private-network discovery and physical enrollment are excluded.

### Versioned agent definitions

An agent version contains its instructions, model connection, permitted tools, asset scope, output contract and operating limits.

- Edits create a new immutable version.
- Agent tools are selected from the existing registry.
- Permissions are the intersection of the definition, asset grant, connector capabilities and deployment mode.
- Instructions cannot change that intersection.
- The first deployed agent can read configuration, telemetry and evidence. It cannot apply configuration, approve procedures, control outputs or execute generated code.
- Generated experiments and procedure proposals remain Sandbox artifacts requiring separate review.

Do not introduce another agent framework.

### Local Codex integration

Keep application login and model authentication separate.

- Add a Codex bridge under the existing provider/session infrastructure.
- Target the installed **Codex CLI 0.146.1** protocol initially. Probe required capabilities and reject incompatible versions.
- Use a dedicated local profile and managed sign-in. Keep credentials outside Sandbox workers.
- Route approved dynamic tool requests through CertaRig’s scoped registry.
- Disable shell execution, native sub-agent delegation, apps and inherited external tools. Deny file-change and permission-escalation requests.
- Record reported model identity, usage, visible messages and tool traces.
- Require explicit consent before an Author’s model connection can serve an approved deployment.
- Stop on disconnected authentication or exhausted quota. Do not switch automatically to a paid API.

OpenAI website sign-in remains a future provider option after supported registration. It must not replace CertaRig’s sessions or asset authorization. [OpenAI distinguishes identity sign-in from ChatGPT plan usage](https://developers.openai.com/siwc/quickstart.md).

### Separate evaluation from deployment

**Sandbox evaluates agents. A separate managed runtime operates approved deployments.**

During evaluation, the provider remains outside worker containers. Use an isolated fixture-tool registry rather than live equipment connectors. A trusted Sandbox verifier checks the resulting traces and evaluation contract.

Bind each evaluation to the exact agent version, model/backend, tools, asset profile, scenario suite, runner image and verifier revision. Fixture results cannot qualify a Codex-backed version.

The Reviewer cannot edit the submitted version or approve their own work. Review binds the exact evaluation and deployment permissions.

The managed runtime reuses `AgentSession` and the registry in a separate process outside Edge acquisition. It runs no customer-generated Python or shell code.

Initial runtime defaults:

- Observation mode only.
- One active deployment in the local proof.
- One assessment every 30 seconds.
- At most ten assessments within a 15-minute lease.
- One assessment in progress at a time.
- No automatic restart, catch-up burst or authority restoration after interruption.

Changes to the asset profile or permissions pause the deployment for review. New agent versions require new evaluation and approval.

Revocation immediately blocks new tool calls. Cancel active inference and discard late results. Independent bench recording continues.

## 3. Interfaces and Studio

Add control-plane API families for:

- `/v1/auth`: sign-in, callback, current user and logout.
- `/v1/assets`: enrollment, permissions and scoped reads.
- `/v1/agents`: definitions, versions and evaluations.
- `/v1/model-connections`: local Codex connection and consent.
- `/v1/deployments`: review, start, status, events, revocation and export.

Add typed organization, membership, asset-grant, agent-version, evaluation and deployment records. Update OpenAPI and add a platform client without reinterpreting existing Edge role keys as customer identities.

Extend Studio using its established design:

- Organization and asset selection.
- Agent editor with instructions, model and permitted tools.
- Evaluation results with clear fixture/live-provider labels.
- Reviewer panel showing the exact version, evidence and permissions.
- Deployment monitor showing observations, tool activity, lease and provider status.
- A visible revocation action.

Scope every transcript, artifact and download request. Historical local workspaces remain outside customer organizations until explicitly imported.

## 4. Acceptance tests

The local proof must demonstrate:

- Two genuine OIDC sessions with distinct roles.
- Author rejection when attempting self-approval or unauthorized deployment.
- Denial of Bench B access from the Bench A agent.
- Cross-organization isolation using an additional test-only organization.
- Rejection of forged roles, expired sessions, replayed login transactions and reused enrollment codes.
- Nominal, stale-data, wrong-unit, forbidden-action and cross-asset evaluation cases.
- Rejection of forged evaluation passes and mismatched version/model/profile bindings.
- One live Codex evaluation followed by reviewed observation deployment.
- Revocation, permission removal, provider failure and restart without renewed authority.
- Continued Edge recording during agent-runtime failure.
- Offline verification of exported observations, evaluations, review and lifecycle events.
- Failure after required evidence is removed or corrupted.

Complete the **seven existing real-container qualification cases** before declaring Sandbox execution qualified. Preserve lint, typing, the 90% coverage gate, property/scenario, soak and browser checks.

Verify Studio at desktop and mobile widths, including keyboard access, role restrictions and error states.

## 5. Delivery and boundaries

Use **20 November 2026 as a review checkpoint**, not a production-readiness claim.

1. Establish identity, memberships, asset enrollment and scoped access.
2. Add versioned definitions and evaluation records.
3. Integrate local Codex and the separate observation runtime.
4. Add independent review, scheduling, monitoring, revocation and portable evidence.
5. Run qualification and rehearse the demonstration.

For the five-minute presentation segment, inspect a genuine saved evaluation, then show live deployment, an access refusal and revocation.

Keep these later increments separate:

- Supervisor and specialist-agent delegation.
- Completed-run import and replay.
- Additional equipment connectors and controlled actuation.
- Hosted commercial operation and production identity hardening.
- Laptop and phone fleet management.

The physical bench remains a reference accessory with a **strict total budget below ₹3,000**. Reuse verified inventory. Leave the unidentified battery, regulators and sensor out of powered operation until identified. No propulsion or pressure-system development is included.

This plan authorizes no deployment, purchase, billing change or physical operation.
