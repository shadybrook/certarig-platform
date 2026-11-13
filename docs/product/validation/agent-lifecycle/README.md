# Verified checks and remaining gates

These results belong to the local implementation on 13 November 2026. `summary.json` separates executed tests from outstanding qualification.

- Python regression: **398 passed, eight skipped**, three deselected; **90.75% coverage** against the unchanged 90% gate. Property and scenario tests are included.
- New platform tests: **54 passed** within that regression.
- Browser: **ten existing tests and two customer-lifecycle tests passed**. Dependencies and model responses are fixtures. Screenshots exercise desktop, 390 px mobile, role restrictions, long text and safe text rendering.
- Soak: **one simulator test passed**. Lint and typing passed.
- Signed OIDC test-server exchanges passed. **Genuine Dex remains unrun**.
- Actual Codex 0.146.1 protocol initialization and redacted account probe passed. Its dedicated profile was signed out. **No model inference occurred**.
- **All seven real-container cases remain unrun**. Preflight reports elevated macOS memory pressure and no pinned image.

A final existing-browser test revealed a template-loading timing race in the test itself. The test now waits for loaded channels and the answer-save response; the full browser suite then passed.

The source UI detector returned no findings. Rendered desktop/mobile views and affected interactions were inspected using the installed design workflow and Impeccable, preserving Studio conventions. These screenshots show test data, not physical or live-model qualification.

Continue with the remaining gates and exact commands in [the implementation guide](../../AGENT_LIFECYCLE.md). No hardware, purchase, public deployment or billing change occurred.
