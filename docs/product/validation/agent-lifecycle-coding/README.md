# Coding completion checks

This follow-up starts at `dd63f8e` and finishes the three code gaps from the approved customer-agent plan: reviewed profile recovery, the full observation-tool selector, and runtime/provider health. The source remains on `product/agent-lifecycle-2026-11-13`.

The checks in this directory use synthetic application identities, model responses, simulator data and Sandbox engine doubles. They are code and UI checks. They do not qualify genuine Dex, Codex, a Sandbox image or container isolation.

## Covered behavior

- Reviewer-only, expiring, single-use profile previews and acceptance; stale or contradictory candidate rejection.
- Fresh evaluation and independent review after profile or connector-policy changes, including a return to an old configuration hash.
- Preserved immutable baseline revisions and valid historical exports after a newer baseline is accepted.
- All seven connector-supported observation tools in Studio; controls and approval tools stay excluded. Unsafe run identifiers and cross-asset arguments are refused.
- One-second runtime heartbeat, five-second freshness limit, visible provider activity, interruption on failure/restart and no restoration from a late heartbeat.
- Independent heartbeat/cancellation while inference or connector checks are blocked; provider-cleanup failure pauses the lease.
- Model status polling cannot undo a concurrent disconnect, and consent is removed before provider cleanup.
- Desktop/mobile profile recovery, tool selection and offline-runtime presentation.

Verified results: **412 regression tests passed**, **8 skipped**, **90.95% coverage** against the unchanged 90% gate. The regression includes **68 platform tests**. All **13 browser checks**, lint, typing and the simulator soak check passed. `summary.json` and the saved logs record the completed runs. Screenshots show explicit test data. The UI preserves Studio conventions using the installed design workflow and Impeccable.

## Deferred by the user

Do these after the coding stage:

1. Verify genuine Dex Author and Reviewer login.
2. Verify managed sign-in to the dedicated Codex profile and the pinned protocol boundary.
3. Build the pinned Sandbox image and run all seven real-container tests.
4. Capture one genuine Codex evaluation, independent review, observation deployment, refusal/revocation and verified evidence bundle.

No real sign-in, image build, container qualification, paid model call, public deployment, hardware operation or purchase was performed in this coding follow-up. See [the setup guide](../../AGENT_LIFECYCLE.md) for the exact service and verification commands.
