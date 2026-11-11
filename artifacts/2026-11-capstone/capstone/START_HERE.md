# CertaRig capstone checkpoint handover

Implemented on 9 November 2026 for the working 20 November milestone. The local workflow configures a second simulator rig, verifies reviewed readiness, requires explicit approval, runs the thermal procedure and exports evidence that verifies independently.

## Review the academic pack

- `CertaRig_Capstone_Report_Draft.pdf`: six-chapter, 18-page draft. The PDF embeds Times New Roman; the editable DOCX is included.
- `CertaRig_Capstone_Demo_Review.pptx`: ten slides using the supplied university template, with fifteen-minute speaker notes including a five-minute demonstration.
- `demo-rehearsal.md`: timed run-of-show and viva preparation.
- `rubric-checklist.md`: evidence mapped to all 100 rubric marks, without predicting a grade.
- `progress-and-supervisor-log.md` and `supervisor-update-draft.md`: genuine records and an unsent update. Planned work is labelled planned; supervisor remarks are blank.

Student declaration, academic year, current supervisor assignment, actual supervisor feedback, spoken rehearsal, new video link if required, and final university deadline remain for authentic confirmation/completion. No submission or email was sent.

## Run the software

The isolated worktree is:

`/Users/chintandedhia/Documents/Codex/2026-11-09/okay-we-should-start-working-on/work/certarig-capstone`

Branch: `capstone/connected-workflow-2026-11-09`

- `bbebcea`: implementation and acceptance tests.
- `df05bc3`: runbook, reproducible fixture demonstration and validation receipts.

See `README.md` in this pack for the local simulator command and UI instructions. Provider defaults to `fake`. No Pi deployment or new physical trial occurred. The original research checkout retains its previous untracked roadmap and the frozen submission is unchanged.

The patch and Git bundle preserve the two local commits. The bundle requires base commit `d81c3c099b79a9cf86ad1d7ecec7b96e333f84c2` already present in the platform repository. It is not a full repository backup. To import it into a repository with that base:

```sh
git fetch /absolute/path/CertaRig_capstone_commits.bundle capstone/connected-workflow-2026-11-09:capstone/connected-workflow-2026-11-09
```

Do not apply the patch on top of the same imported commits. No new branch has been pushed or merged remotely.

## Inspect the evidence

- `CertaRig_thermal_simulator_evidence.zip`: verified local simulator run. Its receipt explicitly identifies the automated approval fixture.
- `screenshots/browser-thermal-run.zip`: run exported through the automated browser test exercising the human-facing controls.
- `demo-receipt.json`: exact raw sample count, extrema, hashes and evidence scope.
- `validation/`: complete passing command logs and the browser-export verification result.
- `expected-failure/`: intentionally damaged COPY for the refusal demonstration. This is not valid evidence; rejection is expected.

Current verification: 247 selected software tests pass, 90.03% coverage, lint and mypy pass, seven browser tests pass, and one separately run accelerated simulator soak passes. Hardware/live-model tests were not included. Offline verification checks integrity and recalculates the raw-sample summary; it is not a safety certificate or a complete independent physical replay.

The two reference demonstrations have different run IDs and sample totals because they are separate executions. The report's numeric example refers to `demo-receipt.json`. Earlier refusal toasts can remain briefly visible in the browser screenshots; the procedure result panel records the run outcome.
