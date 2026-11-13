# Local customer-agent lifecycle

This increment starts at `f877d82` (draft PR #7), on `product/agent-lifecycle-2026-11-13`. It implements the [user-approved plan](CUSTOMER_AGENT_PLAN.md) in an isolated checkout. It preserves the frozen Phase 3 installation and existing Edge APIs. The product proof is local and simulator-only; the physical reference bench remains below ₹3,000 and is unchanged.

## What is implemented

- OIDC Authorization Code with S256 PKCE, single-use state, browser binding, nonce and signed JWT validation. SQLite stores application sessions and server-derived memberships. HTTP cookies are HttpOnly, SameSite=Lax, expire after eight hours, and have a 30-minute idle limit. Mutations require the same loopback origin and session CSRF token. Edge shared-role headers do not authenticate control-plane users.
- Administrator-registered loopback simulator connectors, five-minute single-use pairing, independent connector credentials and per-user asset grants. Connector registration is organization-bound and cannot be enrolled twice. Demo Edge reads require the server-held connector credential, including direct loopback reads. Legacy Edge mode keeps its existing defaults. There is no arbitrary URL enrollment or physical connector enrollment.
- Immutable agent versions, with instructions, exact model connection, observation tools, output schema and fixed execution limits. Existing `AgentSession`, provider messages and tool registry remain the orchestration layer.
- Five evaluation scenarios: nominal, stale source, wrong unit, forbidden action and cross-asset request. Providers use synthetic tool data outside workers. A fixed Sandbox worker verifies the collected trace, including model identity and transcript consistency. Only a broker-owned result can become a trusted evaluation. Fixture evidence cannot qualify Codex.
- Independent review, separate observation runtime, one active deployment, 30-second spacing, ten assessments, 15-minute leases and no automatic resumption. Asset, model-consent, reviewer, profile, capability and runner/verifier bindings are checked again. Revocation cancels inference and discards late results. There are no generated Python/shell processes in the observation runtime.
- Scoped transcripts, lifecycle events, observation monitoring, access removal, revocation and a checksummed evidence ZIP. Offline verification checks required files, exact version/profile/model bindings, independent review, trace decisions and observation completeness. It does not replay a language model or establish third-party authenticity; compare the manifest digest with a trusted original.

The separate control-plane OpenAPI file is [`platform.openapi.yaml`](../../certarig/schemas/platform.openapi.yaml). The record schemas are [`platform.schema.json`](../../certarig/schemas/platform.schema.json). `PlatformClient` is also exported through `certarig.sdk`; it takes application sessions, never Edge role keys.

## Start from a clean development checkout

Install the optional platform dependencies with the existing dev dependencies:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev,platform]'
.venv/bin/python -m certarig platform init-demo
```

Initialization refuses to overwrite an existing proof. It writes a private root at `~/.local/share/certarig-platform`, a Dex configuration, two randomly generated local accounts, and separate simulator connector credentials. The command prints paths and user IDs, not passwords. Read the generated private `secrets/demo_accounts.json` locally. Never commit that directory or put credentials in an agent prompt.

Use **Dex v2.45.0** for this proof. Its static local user subject mapping is recorded in the initializer and must be rechecked if Dex changes. Sources: [Dex local password database](https://dexidp.io/docs/connectors/local/), [Dex subject encoding](https://github.com/dexidp/dex/blob/v2.45.0/server/internal/codec.go). The generated configuration binds Dex to `127.0.0.1:15556`; it does not expose an admin API.

Run each service in its own terminal:

```sh
dex serve "$HOME/.local/share/certarig-platform/dex.yaml"
.venv/bin/python -m certarig platform demo-edges
.venv/bin/python -m certarig platform serve
.venv/bin/python -m certarig platform runtime
```

Start the observation runtime **before independent deployment review and start**. Start is refused unless the trusted runtime heartbeat is live. A runtime restart invalidates outstanding approval and execution authority. Runtime and control-plane processes have independent instance locks. Starting either after an interruption restores history without resuming authority. Acquisition runs in the separate `demo-edges` process. No service is installed at login or started in the background by this implementation.

Open `http://127.0.0.1:18090`. The Reviewer enrolls thermal Bench A and pressure/flow Bench B, and grants the Author access only to A. Use separate browser profiles or contexts for the two accounts. The Author creates a model connection and an agent, then collects and qualifies an evaluation. The Reviewer selects that exact version and evaluation and approves observation. Start and revoke are separate actions.

## Profile recovery, tools and runtime health

A Reviewer can select **Inspect current profile** in Studio to snapshot the observed simulator profile and connector policy. The preview contains the exact before/after hashes, diff and repeat checks. Accepting it saves a new reviewed baseline revision; it never applies a rig configuration or grants execution authority. Author access cannot accept a baseline. Reviews expire after five minutes, can be consumed once, and refuse if either the base revision or observed candidate has changed.

After acceptance, the Author must collect a new five-case evaluation and qualify it. A separate Reviewer must approve the resulting exact binding. Returning to an earlier configuration hash does not restore an old grant: the baseline revision is also bound. Previous profiles remain preserved, and historical deployment exports retain the reviewed profile they actually used.

Studio obtains observation choices from `GET /v1/assets/{asset_id}/tools`. It exposes configuration, capabilities, signals, state, procedures, individual procedure runs and evidence when the connector permits them. It omits control/approval tools and entries not allowed by the connector. A removed tool remains visibly unavailable on an old version and must be removed before saving. A procedure-run read accepts a bounded run identifier, never a URL or path.

The separate runtime writes a trusted heartbeat every second. After five seconds without a valid heartbeat, status becomes unresponsive and affected deployments become interrupted when checked; a late heartbeat cannot restore authority. A fresh runtime generation invalidates outstanding authority and requires renewed independent review. Graceful shutdown marks the runtime offline and interrupts its active deployment. The heartbeat and cancellation monitor run separately from provider inference and connector I/O.

The deployment monitor reports runtime health, heartbeat time, provider phase, current tool/activity and last assessment. Provider phases distinguish connecting, assessing, tool use, idle, completion, cancellation and errors. Unknown/unavailable status is shown explicitly. A failed provider or failed provider cleanup pauses its lease, while independent Edge acquisition remains outside this runtime.

Additional API operations:

- `GET /v1/assets/{asset_id}/tools` and `GET /v1/assets/{asset_id}/profiles`.
- `POST /v1/assets/{asset_id}/profile-review/preview`, then `POST /v1/assets/{asset_id}/profile-review` with the returned `review_id`.
- `GET /v1/deployments/runtime`; scoped deployment responses also include runtime health.

`PlatformClient` includes `observation_tools`, `preview_profile`, `accept_profile` and `runtime_health`. OpenAPI and record schemas describe the additions. The original [implementation evidence](validation/agent-lifecycle/README.md) remains preserved; [coding completion evidence](validation/agent-lifecycle-coding/README.md) records the follow-up checks.

## Sandbox qualification gate

No submitted source or trusted verification falls back to host execution. Elevated memory pressure blocks provisioning/execution. At least 8 GiB free storage is required. The initial implementation preflight found sufficient storage but elevated macOS pressure and no pinned image; it did not create a VM or change the existing Docker context.

After memory pressure returns to normal, use the same nested root configured by `init-demo`:

```sh
.venv/bin/python -m certarig sandbox --root "$HOME/.local/share/certarig-platform/sandbox" preflight
.venv/bin/python -m certarig sandbox --root "$HOME/.local/share/certarig-platform/sandbox" prepare
.venv/bin/python -m certarig sandbox --root "$HOME/.local/share/certarig-platform/sandbox" qualify
.venv/bin/python -m certarig sandbox --root "$HOME/.local/share/certarig-platform/sandbox" serve --socket "$HOME/.local/share/certarig-platform/sandbox/broker.sock"
```

`prepare` uses the separate existing-policy `certarig-sandbox` Colima profile, fixed resource constraints and no host sharing. `qualify` must pass all seven real-container cases. Source/verifier or image changes invalidate qualification. See [Sandbox runtime policy](../sandbox/README.md).

## Dedicated Codex connection

The bridge targets **Codex CLI 0.146.1** and probes its actual stdio app-server. It uses a separate private profile for each model connection; no desktop auth file or API key is copied. The environment does not inherit provider API keys, external MCP configuration or plugins. Shell/native delegation, apps, browsers, generated file changes and permission requests are disabled or refused. Unexpected native item types, model substitution, quota errors and disconnected auth stop the assessment. Protocol tests are distinct from live boundary qualification.

In Studio, create a **Codex** connection with an exact model available to your account, explicitly consent to observation deployment, and choose **Start managed sign-in**. Complete the device flow with OpenAI, then **Check connection**. This is model authentication, separate from Dex application identity. There is no paid API fallback. A commercial hosted integration requires a separately supported OpenAI registration; see [app-server](https://developers.openai.com/codex/app-server) and [website sign-in](https://developers.openai.com/siwc/website).

At the user’s request, Dex/Codex sign-in verification, the image build and seven real-container cases are deferred until coding is complete. A genuine live Codex evaluation and observation deployment remain acceptance gates until those actual runs are captured. The initial implementation’s connection probe verified protocol initialization and returned `connected: false`; it made no inference request.

## Evidence and demonstration

Export from the deployment monitor, then verify offline:

```sh
.venv/bin/python -m certarig platform verify certarig-agent-evidence.zip
```

For the five-minute presentation, inspect a genuine saved Codex evaluation, show the exact version and independent review, start observation on A, demonstrate an access refusal for B, and revoke. Do not present the browser test fixture as a live-provider/container-qualified run. Missing, altered or inconsistent required evidence fails verification.

## Remaining acceptance gates

1. Genuine Dex two-account login with the generated deployment configuration. Signed-token tests use an explicit test issuer, not Dex.
2. Normal resource pressure, pinned image build and all seven real-container qualification cases.
3. Managed sign-in to the dedicated Codex profile, native-tool boundary qualification and one real Codex evaluation followed by independently reviewed observation deployment.
4. Capture the genuine final five-minute demonstration after those gates pass.

Public hosting, production multi-tenant security, physical execution, agent delegation, completed-run replay and further hardware procurement remain outside this increment. 20 November 2026 is a review checkpoint.
