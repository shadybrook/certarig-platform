# Fifteen minute capstone demonstration

Status: software sequence exercised in the browser; spoken student rehearsal pending. The deck contains speaker notes and references. Allocate five minutes to the live demonstration and ten minutes to explanation.

| Slide | Time | Purpose |
| --- | --- | --- |
| 1 Title | 0:00–0:30 | Introduce CertaRig and this local checkpoint |
| 2 Problem | 0:30–1:30 | Connect rig changes, approval and reviewable evidence |
| 3 Objectives | 1:30–2:30 | State the complete workflow and simulator/fixture scope |
| 4 Existing system | 2:30–3:30 | Explain the prior foundation and concrete software gaps |
| 5 Architecture | 3:30–5:00 | Distinguish assistant proposals from local execution authority |
| 6 Stack | 5:00–5:45 | Explain reuse of the existing stack |
| 7 Live demo | 5:45–10:45 | Configure, block, review, deny, approve, run, export, verify |
| 8 Results | 10:45–12:15 | Show test receipts and reproduce the raw-sample summary |
| 9 Limitations | 12:15–13:30 | Describe restart, UI and evidence failures; state unqualified work |
| 10 Conclusion | 13:30–15:00 | State demonstrated capability and next gated increments |

## Live demonstration cues

1. Start the loopback simulator from the runbook using a fresh copied configuration. Leave the provider on `fake`. Use Onboard to rename the thermal channel; preview and apply. Select `thermal_soak` and demonstrate that an unreviewed start is refused.
2. Review that exact procedure/configuration. Request a run and deny its first approval. Show that no run was started.
3. Request again, inspect the requester and exact arguments, then grant. Show the procedure passes and ends safe.
4. Export this run. Stop the service and verify the downloaded ZIP with `python -m certarig evidence verify ...`. Explain CSV, configuration, procedure revision, approval, events, hashes and the reproducible sample summary.
5. Verify the deliberately corrupted example in `expected-failure/`. Explain why its rejection is the expected result. Preserve the untouched original ZIP.

If a live UI fails, disclose it and use the labelled screenshots and verified exported ZIP. Do not describe a recorded/software fallback as a successful live execution. The prepared ZIP's receipt labels automated approval as a fixture, not a human hardware trial.

## Viva preparation

- Why does a model failure not stop acquisition? Acquisition, numerical checks and recording run locally outside inference.
- What survives restart? Audit history survives; outstanding authority expires. Reset/reconnect never automatically restores an output.
- What binds an approval? Requesting role/name, exact arguments, configuration/capability contract, adapter and procedure hash.
- What does commissioning prove here? Reviewed software readiness for the simulator. Physical commissioning is explicitly false.
- What reproduces offline? Artifact integrity, referenced raw recording, row counts, channel extrema and the recorded-command invariant. It is not an externally signed certificate or a full independent replay of physical behavior.
- What remains? Independent identities, live-provider qualification, real connectors and separately accepted physical trials, plus genuine academic reviews.
