# Innovator Workbench coding validation — 14 November 2026

Implementation commit: `07fb874` on `product/agent-lifecycle-2026-11-13`.

See `summary.json` for the actual final counts, `regression.txt` for coverage/property/scenario/soak results, `browser-platform.txt` and `browser-edge.txt` for the two rendered suites, and `lint.txt`/`typing.txt` for static checks. `wheel-build.txt` records packaging. `coverage-summary.json` retains file-level totals without committing the verbose coverage database.

Desktop and mobile screenshots are `workbench-desktop.png` and `workbench-mobile.png`. They show explicit fixture identities/model results. Browser acceptance covers drafting, retained requirements after immediate commit, reopening the conversation, task progress, review, revocation, safe text, profile recovery, mobile panels and automatic analysis progress.

Independent review identified and resolved draft requirement loss, stalled task cursors after unrelated audit traffic, inconsistent model limits, incomplete analysis evidence binding, revoked-grant worker cleanup and cached analysis progress. Tests include real loopback Modbus TCP exchanges, malformed replies, read-only function enforcement, serial transport doubles, shared team budgets and rechecksummed evidence omission/substitution attempts.

The clean wheel check installed the platform, MQTT and serial extras into a new temporary environment, imported from outside the checkout, and verified packaged schemas/tool manifests and current cleanup code. It did not start Dex, sign into Codex, build a Sandbox image or qualify a real container.

Ten expected skips comprise seven real-container cases, one opt-in MQTT broker integration and two unavailable physical HIL cases. No equipment was energized. Genuine two-user Dex login, live Codex evaluation/deployment, Sandbox image/seven-container qualification and an attended final demonstration remain the next gates. This record establishes local coding checks, not hosted or physical readiness.

GBrain was repaired independently by restoring its broken CLI symlink to its existing installation and restarting the existing loopback LaunchAgent. MCP initialization, discovery, keyword search and page retrieval succeeded with vectors/query expansion disabled. The client must reload/restart to expose native tools. Durable repair record: `operations/gbrain-local-cli-symlink-repair-2026-11-14`. No GBrain credentials are included here.

Durable implementation record, saved and verified by readback: `projects/certarig-innovator-workbench-local-implementation-2026-11-14`. It identifies the local implementation commit and keeps live-provider/container/physical qualification separate.
