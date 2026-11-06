# CertaRig: from a validated bench to a useful product

Planning date: 7 November 2026. Status: proposed product strategy, not a customer commitment or deployment approval.

## 1. Decision

Pursue the ambition, but fund the next stage with evidence rather than a large feature list. Build an AI operations workspace for engineering test rigs. Start with one repeated commissioning or revalidation workflow for one kind of team, then earn permission to cover more of the rig lifecycle.

The first promise to test is:

> When your test rig changes, CertaRig helps you establish what is installed, what needs checking, run an approved procedure and produce evidence another engineer can review.

This is not a decision to abandon control and become a report generator. Evidence review is an accessible entry point; guided operation and bounded execution are part of the same workflow. It is also not a decision to let a model freely operate arbitrary machines.

The first commercial milestone is an external engineer repeatedly completing a valuable workflow on their own rig. A polished demo, a university pass and an investor's interest are different milestones.

## 2. What we know, and what we do not

### Existing technical base

The source and research records inspected for this plan are in the isolated `research/machine-control-2026-11-07` checkout, based on platform commit `f77ccaaa3ffd12cdb87b2c3fa0a627315b556998`. The completed machine research is recorded at commit `0d8009c5f6594d0c1afd9d5af579c3a96b389685`.

* The Phase 3 evidence establishes a mapped low voltage dry bench, potentiometer based input emulation, E-stop handling, relay/indicator behavior and reset required behavior. It does not establish hydraulic commissioning, production machine reliability or a certified safety system.
* The machine research audit records 52 passing unit/agent tests and 12 passing checks against a real OctoPrint HTTP server with its official virtual printer. Decisions were scripted and approvals came from the test harness. This is not a physical print trial or a live language model evaluation. See [research audit](../research/COMPLETION_AUDIT.md).
* There is no external machine access confirmed yet and no paying customer established by this work.

### Code we should extend, not rebuild

* [Configurator](../../certarig/edge/configurator.py): configuration diffs, current/next hashes, restart requirement checks and guarded application. Missing: a user understandable dependency and revalidation plan, not the basic diff operation.
* [Approval registry](../../certarig/edge/approvals.py): exact tool/argument and contract binding, expiry and single use. It is in memory; recovery across service restarts needs hardening.
* [Twin gate](../../certarig/edge/twin_gate.py): recent simulator pass bound to procedure hash for Raspberry Pi mode. Extend the binding to the relevant rig configuration, adapter and firmware profile. A simulator pass must not be presented as proof of physical correctness.
* [Authoring](../../certarig/agent/authoring.py): procedure drafting and validation foundations. Model reliability needs its own evaluation.
* [Evidence bundles](../../certarig/edge/bundle.py): reports, events and a manifest of files present in the target directory. Verify raw recording inclusion end to end, missing artifact failure behavior and portable review; a referenced filename is not proof that the file was exported.
* [MQTT adapter](../../certarig/edge/hardware/mqtt.py): in process TagBus scaffold, not a demonstrated broker connected driver. Do not sell this as an installed network integration.
* [Rig schema](../../certarig/schemas/rig.schema.json): channel calibration references, not a full calibration or asset management product.
* [Machine gateway](../../certarig/machines/gateway.py): a separately scoped machine operation path from the research. Keep its virtual only experimental controls separate from deployed bench authority.

These foundations make the next experiment credible. They do not make the current repository a turnkey commercial platform.

### Evidence of a problem, not yet of our market

A customer authored Stäubli case describes fragmented software, calibration and test records around otherwise automated testing. This supports the existence of operational pain, but it is a vendor hosted enterprise example, not proof that small Indian labs will buy CertaRig. [Stäubli case](https://www.ni.com/en/solutions/electronics/case-studies/staubli-modernized-test-operations-global-laboratories.html)

NI SystemLink already addresses test operations, assets and data, including third party integrations. Therefore, “all rig information in one dashboard” is not a defensible novelty claim. We must test whether our focused workflow is easier to adopt and more useful for a specific underserved team. [SystemLink product description](https://www.ni.com/en-gb/shop/product/systemlink.html)

## 3. First customer hypothesis

Start with a small R&D or validation team operating custom electromechanical test benches. Favor teams that change sensors, fixtures or software frequently and manually connect Python or LabVIEW scripts, CSVs, setup notes and reports.

* User: test, commissioning or lab engineer who prepares and executes a test.
* Champion: senior engineer responsible for reproducibility and handover.
* Buyer: lab head, R&D manager or owner of a small engineering company.
* Possible channel: a test system integrator who installs and supports similar rigs for several customers.

These roles are hypotheses to confirm in interviews. A university lab may provide excellent learning and access but have little purchasing authority. An integrator may value delivery documentation more than daily operation. Do not combine them into one undifferentiated customer.

Qualify a prospective pilot by asking whether there was a recent real setup change, missing result, difficult recovery or repeat test; whether we can observe the workflow; and whether someone owns the cost. Disqualify early requests for unrestricted remote production control, extensive bespoke drivers before any trial, or unsupported claims of compliance.

We should not simultaneously target hobby printers, resin labs, CNC factories and hydraulic certification facilities. Printer research is an integration proving ground unless users demonstrate a stronger business opportunity there.

## 4. First product: one complete journey

Example scenario, proposed rather than a recorded customer incident: an engineer replaces a sensor, updates its scale and wants to rerun the affected bench test. Today the engineer must reconcile the rig setup, scripts, limits, calibration and previous results. CertaRig should guide this exact journey.

### A. Establish the rig passport

Record rig ID, owner, components, connection map, supported commands, channel units, sensor ranges, safe state, software/firmware versions, calibration references and the last reviewed configuration. Allow an explicit unknown state.

Import existing documents and CSVs rather than requiring a complete migration. The AI can suggest mappings with source references; an engineer confirms the actual installed configuration. A photograph is context, not electrical continuity verification.

### B. Show readiness and explain changes

Compare desired and observed configuration. Show what changed, which evidence it invalidates, whether a software restart is required and which checks are affected. Separate deterministic dependency rules from AI suggestions. Incomplete knowledge must produce “impact unknown; review required”, not an invented minimal test set.

### C. Prepare an approved test

Select a reviewed procedure or draft one from an existing SOP. Validate units, channels, limits, timing and available capabilities. Link the procedure to the approved configuration and its simulator result. Present the exact physical actions and expected safe state before permission is granted.

### D. Run under bounded authority

The operator authorizes a named procedure, device, configuration and time window. Local deterministic checks control dispatch. Show live measured values, commands, acknowledged state and unknown state separately. Do not label a commanded relay state as a physically measured contact state.

### E. Troubleshoot with evidence

For a failure, show observations, possible explanations, confidence and the next discriminating check. Example: “Controller is reachable but source samples stopped advancing; inspect the acquisition process before considering a restart.” This is a hypothesis with a check, not a proven diagnosis.

Distinguish application restart, device reboot, trip reset and permission to resume outputs. Each has different prerequisites. A restart should not silently restore output authority.

### F. Close the evidence and handover loop

Produce raw recordings, procedure/configuration versions, events, operator decisions and deterministic results in one verifiable bundle. AI explanations cite particular runs and time ranges and remain separate from measurements. Another engineer should be able to open the export without the founder, locate a plotted sample in the raw data and understand why the result passed, failed or remains inconclusive.

The first release is useful only when this whole journey works. Six disconnected attractive screens are not an alternative.

## 5. How the broader vision fits

### Evidence review: first release

Search and compare runs; inspect raw data; flag missing or inconsistent evidence; generate a reviewable report. Never convert missing evidence into a pass. Support offline import so a user can obtain value before granting machine control.

### Guided setup and troubleshooting: first release

A reviewed checklist, sourced instructions, known diagnostic trees and proposed next checks. Capture the outcome of each check so the system learns rig specific history without treating every previous chat answer as truth.

### Reset and restart assistance: first release, constrained

Show the required action and why. Initially require approval for recovery operations that can change physical behavior. Permit automatic recovery only for explicitly classified non-actuating services after testing their effects. Preserve an unknown/blocked state after ambiguous dispatch.

### Calibration: record first, perform later

Track sensor IDs, certificates, due dates, coefficients and links to affected runs. Later guide a calibration procedure against a suitable reference, compute proposed coefficients and uncertainty information, and require qualified review. Turning a potentiometer or fitting a line does not certify a pressure sensor. Never let the AI manufacture a certificate or silently accept new coefficients.

### Inventory: rig assets first

Track what is installed, its version, compatible replacements, location and calibration status. Add spare availability only when users need it. Do not build warehouse management, accounting, automated purchasing or a full ERP as the first version.

### Control: expand by validated profile

Support named operations through documented controllers. Keep the existing OEM/local controller and interlocks in charge of physical constraints. Validate each profile independently. Start with one authorized external rig; add another device family because a user needs it, not because an API exists.

### Fleet operation: after repeated single rig use

Add scheduling, utilization and shared procedure libraries after the single rig workflow is installed repeatedly. Do not make multi-site orchestration a dependency for learning whether the first user benefits.

## 6. AI ownership and authority

The ambition can be AI owned coordination without unrestricted model owned actuation.

1. **Observe and explain:** read permitted telemetry and documents, summarize runs, track assets and remind operators. Record sources and uncertainty. Sensitive files require explicit access and model data policies.
2. **Prepare:** draft procedures, propose mappings, explain change impact and recommend recovery. Drafts cannot approve themselves.
3. **Execute an authorized envelope:** run a named reviewed procedure with device/configuration binding, bounded arguments, expiration and local checks. Require new permission for material changes.
4. **Automate a proven routine:** allow a specific repeat workflow without per-step approval only after a responsible owner authorizes that envelope and we test failures and recovery. This is procedure specific, not general autonomy.

Outside the model: physical E-stop, hardware interlocks, deterministic limits, identity/permission enforcement, stale signal rules and fail-safe recovery. No internet facing actuator endpoint in an early pilot. Credentials belong in a secret store, never project reports or model transcripts.

## 7. Proposed product architecture

Retain a browser workspace connected to a local edge service. Use the edge service for commissioned adapters, deterministic procedure execution and local recording. Use the AI for interpretation, preparation and source linked review through typed tools. A cloud workspace can later synchronize approved metadata and reports; local operation must not depend on uninterrupted AI access.

The shared model should link:

* Rig and component identities.
* Configuration revisions and channel mappings.
* Calibration records with provenance and validity.
* Reviewed procedure versions and declared dependencies.
* Runs, raw artifacts, events and review decisions.
* Issues and approved recovery actions.

Example dependency: sensor replacement → channel mapping/calibration change → invalidate affected readiness evidence → review procedure impact → approve rerun → attach results to the new revision. It must also permit an unknown dependency rather than claim a complete graph.

Start with one organization and one installation. Before central hosting for multiple customers, implement tenant isolation, access control, retention, backups and customer data rights. Do not prematurely build an enterprise SaaS layer to avoid testing a local workflow.

## 8. Engineering work order and acceptance tests

### P0: trustworthy evidence and recovery, before external actuation

* Persist approval histories and relevant blocked/uncertain states. After restart, reconcile actual controller state and require fresh authority; do not restore a consumed or ambiguous permit.
* Bind test readiness to procedure, rig/configuration revision and relevant adapter/firmware identity. A material change invalidates affected readiness evidence.
* Preserve device source timestamps/sequence quality. A newly received stale value is still stale. Test dropout, clock changes and missing data.
* Verify complete raw exports. Corrupt or remove a referenced artifact and require the reviewer to flag it. Hashes detect alteration relative to a manifest; they are not an independent certification or a trusted digital signature.
* Separate commanded, controller acknowledged and physically measured states in the UI and reports.
* Commission the selected real driver. In process MQTT/Modbus scaffolds are not field connections.

### P1: usable first workflow

* Rig passport import and review screen; reusable profile for the existing dry bench.
* Configuration change summary and rule based affected check list, with unknown impact path.
* Readiness queue and procedure approval/run/review flow.
* Source linked evidence viewer, deterministic checks and reviewer corrections.
* Guided recovery checklist tied to observed state, not a generic chat answer.

### P2: only after repeated user demand

* Calibration lifecycle with qualified reference procedures.
* Rig inventory/spares beyond installed asset identity.
* A second real adapter and reusable onboarding profile.
* Team scheduling, fleet views and carefully authorized routine autonomy.

### Live model evaluation, distinct from tool tests

Create a versioned evaluation set from real tasks with consent. Test missing units, wrong channel names, stale telemetry, incompatible procedures, changed configuration, expired calibration, prompt injection in imported manuals, missing evidence, ambiguous command outcome and E-stop recovery. Score factual citations, unsupported claims, correct abstention, operator interventions and attempted unauthorized actions.

Run live model evaluations first with no actuation. A deterministic tool refusal is useful evidence but does not mean the model made a correct decision. Zero observed incidents in a small trial is not proof of safety.

## 9. Twelve week plan with decision gates

This is a planning estimate for a small founder led effort. Access, driver complexity and user availability determine pace. If access is delayed, continue the import/review workflow; do not substitute virtual tests for a physical acceptance gate.

### Weeks 1–2: discover and complete an evidence workflow

Founder: conduct ten focused conversations, observe at least two real workflows and ask for permission to use two redacted example data packs. These are proposed learning thresholds, not achieved traction.

Build: a reviewed rig passport plus import → inspect → compare → export on existing evidence. Add explicit missing-file handling. Document current gaps and choose one external pilot workflow.

Gate: an engineer can review a real result and identify its configuration and evidence without the founder explaining every click. At least one team agrees to a specific trial with an owner and a date. If not, diagnose pain/access rather than add modules.

### Weeks 3–4: first external pilot, observe first

Build: setup/readiness and change impact screens using existing configurator foundations; harden restart/authority handling. Connect a permitted device in read only mode, or ingest its real exported data if control is not permitted.

Measure the current workflow before changing it. Agree on one acceptance outcome, support limits and who can authorize operations. A read only pilot can prove review value but cannot prove control value.

Gate: user completes the chosen task on their own artifacts, can explain a failure/unknown and asks to use it on the next real task. Obtain explicit further approval before supervised control trials.

### Weeks 5–8: supervised operation and repeat use

Build: one physically validated adapter/profile, approved test execution, recovery and portable evidence. Run on the internal dry bench first and then the authorized customer installation within its agreed scope. Work toward two independent organizations using the same core workflow.

Gate: repeat use without the founder doing the core task, a demonstrated improvement against baseline and a buyer willing to discuss a paid scoped pilot. Two organizations and a paid conversation are goals, not forecasts.

### Weeks 9–12: product package or revise the approach

Build: repeatable install, profile validation, backup/restore, supported upgrade/rollback, user roles, support boundaries and a concise onboarding guide. Add one adjacent feature only when usage supports it.

Gate: sell a limited scope pilot with explicit deliverables and exclusions. Attempt a second installation without a source code fork. If every installation needs substantial custom engineering, narrow the supported rig family or charge for integration separately rather than pretending it is pure software margin.

## 10. Finding users from Mumbai

Location is not itself evidence of demand or inability to sell. It gives us places to ask for observation and introductions; the actual buying process remains unvalidated.

* Ask the professor and alumni for introductions to engineers who run tests, not just other startup enthusiasts. Request observation of the last real workflow before pitching every feature.
* Approach small test system integrators and hardware R&D teams with a single task offer: turn an existing test and its scattered evidence into a repeatable reviewed run.
* Investigate riidl's Mumbai Fab Lab as an access and operator learning route. Its published facilities are not an endorsement of our product. [riidl Fab Lab](https://riidl.org/laboratory/fab-lab)
* Investigate SINE's published lab access process. Its guidelines describe external access, training and authorization; facility access does not authorize installing our controller software. [SINE guidelines](https://sineiitb.org/assets/pdf/Guidelines.pdf)
* Offer remote artifact based review to teams outside Mumbai. Machine control is not required to learn about report preparation or evidence gaps. Agree confidentiality and model processing before uploading their files.

Suggested message, not sent:

> I am building CertaRig after validating a small physical test bench. I am trying to understand how engineers prepare tests and review evidence after a rig changes. Could you show me a recent example in a 20 minute call? I am not asking to control your equipment. If useful, I can help organize a redacted test pack and show a prototype on your workflow.

Use ten conversations to learn, not to collect compliments. Ask: “Show me the last time”; “What took longest?”; “What happened when it failed?”; “Who reviewed it?”; “How often?”; “What tool have you tried?”; “Who could pay to change this?”; “What data/control permissions could we get?”

## 11. Pilot scorecard and business test

Collect baseline and pilot values for the same task complexity. Separate test elapsed time from operator active time; do not claim faster physics because report preparation improved.

* Operator minutes to prepare a ready test and to produce a reviewable evidence pack.
* Number of interventions needed from the founder or senior expert.
* Required evidence artifacts present and internally consistent, including raw data.
* Ability of a second engineer to reproduce the review conclusion.
* Repeat use on the next naturally occurring task, without founder prompting.
* Unexpected/blocked commands and recovery outcomes in a declared failure test set.
* Installation/support effort and hosting/model costs per active rig.
* Named budget owner and willingness to pay for a specific outcome.

Suggested pilot success criterion: at least a meaningful measured reduction in operator effort, complete required evidence, successful independent review and voluntary repeat use. Agree a numeric improvement target with each pilot after measuring baseline; do not invent a universal percentage.

Pricing is not validated. Offer a bounded paid pilot for one workflow/rig, then test a per active rig or lab subscription. Integration work should have a separate scope. A free university trial is learning, not proof of commercial willingness to pay. Do not use market size estimates as a substitute for these tests.

After six weeks of genuine discovery, revisit direction if nobody shares artifacts, observes a task with us or commits time. If evidence review is wanted but control is blocked, sell that workflow first. If only custom system building sells, decide whether to pursue an integration business or narrow the product. Do not respond to weak demand by building a larger inventory module.

## 12. YC relevance and defensibility

YC's current Winter 2027 RFS introduction includes specialized software bringing AI into the real economy. That makes this direction thematically relevant, not endorsed or likely to be accepted. Its broader advice emphasizes early launch, direct user learning and manual initial recruitment rather than building a comprehensive platform before use. [Current RFS](https://www.ycombinator.com/rfs), [essential startup advice](https://www.ycombinator.com/blog/ycs-essential-startup-advice)

A credible eventual pitch, once supported by users, is: “CertaRig helps test engineers commission and rerun changing rigs, combining guided setup, approved execution and traceable evidence.” Today we should attach our dry bench and virtual controller boundaries, not claim customer deployments or general autonomy.

Possible defensibility must be earned through:

* A reliable rig/configuration/procedure model and validated recovery behavior.
* Reusable device profiles that reduce each new installation's work.
* Historical test/recovery outcomes with customer permission and reliable labels.
* Workflow adoption, review trust and distribution through relevant engineers/integrators.

APIs, a chat window, an MCP server and access to a frontier model are not themselves a moat. Existing vendors can add AI. Our test is whether users choose our workflow and whether delivery becomes more repeatable as we learn.

## 13. Immediate next actions and ownership

### First seven working days

1. Freeze this as a proposed direction, not an irreversible company pivot. Keep the university submission untouched.
2. Prepare a three minute demonstration: a configuration change, an affected readiness check, one approved dry bench run and a source linked review. Label virtual/physical and measured/derived states.
3. Founder: request five introductions and schedule the first two workflow observations. Do not buy a printer or industrial machine to avoid making these requests.
4. Engineering: assemble a single real evidence pack and deliberately test a missing raw file. Specify the passport and acceptance test before polishing the dashboard.
5. Jointly choose the first external workflow based on actual artifacts and access. Keep the adapter decision open until then.
6. Engineering: deliver the persistent recovery and configuration bound readiness design and tests before any new external actuation.
7. Founder and pilot engineer: agree a baseline, one success criterion, data permissions and a next use date. Review what changed in the plan after the first observations.

The assistant can prepare code changes, schemas, tests, UI, import tools, sourced explanations and reviewable outreach. The founder must obtain equipment access, observation/data permissions, qualified operating oversight and purchase decisions. The assistant cannot independently establish those relationships or certify physical readiness.

## 14. Provenance and limitations

Local source inspected on 7 November 2026; previous technical test results are referenced from their stored audit, not newly rerun for this planning task. External sources above were checked for this plan. Vendor case studies establish examples, not market prevalence. Roadmap, segment, pricing model and adoption targets are hypotheses.

GBrain tools were unavailable in this session. Local source and research records were used instead; this plan has not been saved to GBrain or pushed to GitHub. No customer outreach, hardware actuation or production deployment was performed for this plan.
