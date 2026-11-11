# CertaRig Sandbox v1

Local commissioning experiments and trusted simulated rehearsal. **Not released for untrusted execution until the real-container qualification passes.** The implementation must never run submitted Python, SPICE or shell content on the host. The frozen Phase 3 installation, physical commissioning and human execution approvals remain separate.

## Current deployment gate

The implementation session initially found about 1.5 GiB free disk and elevated macOS memory pressure; storage subsequently exhausted completely during the final regression repeat. The exact final probe and outstanding checks are recorded in the [implementation status report](IMPLEMENTATION_STATUS.md). The approved requirements are 8 GiB free and normal memory pressure. No new Colima VM or worker image was built under those conditions. Only this task's disposable test artifacts were cleaned up; pre-existing data and unrelated workloads were preserved. No paid calls were made or hardware connected. Mocked engine tests and trusted host-side simulator tests are not container-isolation qualification.

## Prepare, qualify, then serve

Run from this source checkout after `make install`. Use the existing development virtualenv. First inspect resource blockers:

    .venv/bin/python -m certarig sandbox preflight

Once resources satisfy preflight:

    .venv/bin/python -m certarig sandbox prepare
    .venv/bin/python -m certarig sandbox qualify
    .venv/bin/python -m certarig sandbox serve

Preparation uses an explicit `colima-certarig-sandbox` Docker context and starts the separate `certarig-sandbox` profile with 2 CPUs, 2 GiB RAM, 20 GiB sparse disk, `--mount none` and `--activate=false`. It does not select or stop the existing Docker context. A curated build context includes only source/config/skills and package metadata, excluding credentials, git data, evidence and virtualenvs. ngspice 47 is compiled from its checksummed release; Python/direct dependencies are pinned and the resulting immutable image ID is retained in `~/.certarig/sandbox/image.id`.

`qualify` runs the fixed real-container test file, requires every case without skips/failures, and records a report bound to the image. The production broker refuses jobs without this qualification. Qualification mode is used only by the fixed operator test harness; it is not an API option. Rebuilding or changing the image requires a new qualification and broker restart.

In another terminal, configure fresh local operator/agent keys using the existing project setup, then launch Studio on loopback:

    CERTARIG_SANDBOX_SOCKET="$HOME/.certarig/sandbox/broker.sock" \
      .venv/bin/python -m certarig edge serve \
      --config config/rig.thermal.capstone.json \
      --capabilities config/capabilities.sandbox.json \
      --evidence-dir evidence/sandbox-demo --port 18083

Open `http://127.0.0.1:18083/#sandbox`. The Sandbox tab explains unavailable runtime states. No subprocess fallback is offered. Use an isolated development copy of a rig file if you intend to apply configuration proposals.

## Workflow and public contract

Authenticated `/v1/sandboxes` routes create/list/read workspaces; POST `/{id}/revisions` saves a new immutable revision; POST `/{id}/jobs` submits `python`, `spice` or `rehearsal`; GET `/{id}/jobs/{job_id}` reads state; GET its `/artifacts/{name}` retrieves safe artifacts; POST `/{id}/proposals` submits only `configuration` or `procedure`; GET `/{id}/export` downloads evidence; DELETE `/{id}` closes the lease/cancels workers. GET `/v1/sandboxes/preflight` reports blockers. OpenAPI describes these additions.

Snapshots support active profiles, pressure/flow and thermal fixtures, or interview drafts. Optional `recording_id: latest` copies a completed recording; active files and arbitrary host paths are refused. An incomplete draft may be analysed, but full configuration, units, calibration identities, mapping and procedure validation are mandatory before rehearsal. Fixture calibration identities do not establish physical calibration. Interview snapshots retain source references and calibration records; only a validated interview proposal can qualify, and promotion rechecks and binds the exact interview revision.

The agent tools are `sandbox_experiment` and `read_sandbox`. Experiment actions create/revise/run/propose/close. Reading optionally takes a job ID and artifact name for a bounded text preview. Plots are inspected in Studio. This is provider-neutral; deterministic demo fixtures are explicitly labelled and do not qualify a live LLM.

Proposals are inert. Only an operator can apply them through the existing rig apply or procedure-draft approval flow. Include `sandbox_id` and `sandbox_proposal_id` to bind that review to the exact receipt. The base configuration, revision, procedure/profile/model, seed, image, scenario suite and verifier revision must match. New revisions require new rehearsal. Configuration changes still invalidate existing execution grants and physical reviews. A sandbox receipt is not automatically installed into the physical twin gate; normal active-rig qualification remains required.

## Containment and quotas

The broker alone accesses Docker. Edge uses a private Unix socket, and workers receive no broker/Edge credentials, device passthrough, host mounts or Docker socket. Submitted content enters over stdin. The root filesystem is read-only, UID 10001, capabilities are dropped, default seccomp retained, networking disabled, and resource controls fixed. Read-only rootfs is not used as an excuse to write inputs into the container's root filesystem.

One concurrent job; 1 CPU; 512 MiB RAM with no swap; 64 PIDs. Analysis/SPICE wall limit 120 s, trusted rehearsal 300 s, clipped to a 15-minute workspace lease. A separate container PID1 timeout bounds lifetime even if the broker exits; the broker also has a deadline watchdog and cancellation. Completed workers stay alive briefly so the broker can pause them, collect tmpfs artifacts without writer races, then remove only owned containers. On restart, previous active leases expire, unfinished jobs become interrupted and no jobs resume automatically.

Input 64 MiB, output 128 MiB, scratch 256 MiB and workspace artifacts 256 MiB. Admission additionally caps 3 active / 32 retained workspaces, 50 revisions and a 1 GiB broker store. Export/archive evidence before reaching these limits; no automatic audit deletion is performed. The closed workspace history is retained.

Inputs and artifacts use separate host directories to prevent filename collisions. Artifact collection rejects traversal, links, directories, duplicate names, unsupported types and excessive sizes. PNG previews are static,≤8 MiB and ≤4 MP; HTML is never executed. SPICE jobs are exploratory: ngspice process completion/exit 0 does not prove convergence, full horizon, physical SOA or circuit qualification.

## Trusted rehearsal and evidence

Generated code never shares a container with the trusted rehearsal harness. The mandatory suite runs the candidate procedure plus independently fixed stale-source, dropout and overrange trials. Trials must demonstrate permit, a forced-safe event, clearing the fault and refusal to restart without reset. Raw CSV safety invariants are recomputed by the verifier. The existing pressure-emulator procedure has explicit simulated raise/lower stimuli; its 4.2 bar threshold is not a physical water-loop target. Unsupported/manual interactions without harness stimuli cannot be called qualified.

Only the broker signs a successful trusted receipt with its private local HMAC key. Analysis files claiming success are ignored. Files, metadata, input hashes, raw recordings, source/decks, engine versions, revisions and receipt/proposal history are exported. Missing or altered required artifacts refuse export/verification. Offline verification reproduces checks and consistency; receipt authenticity requires the original trusted broker. Replacing all hashes and evidence is not prevented by checksums alone.

    .venv/bin/python -m certarig sandbox verify path/to/sandbox.zip

Raw-sample summaries (counts, channel extrema and units) and supported procedure checks are recomputed outside the worker and replayed offline.

The inspectable examples are [thermal analysis](examples/thermal_analysis.py) and [inductive flyback protection](examples/flyback_protection.cir). The SPICE example uses a 12 V source, a 20 mH / 12 Ω load, an ideal switch and a diode model; it does not establish real device SOA, thermal behavior or valve release time. Both examples are submitted as data to containers, never executed by the host demo driver.

The real demo entrypoint is `tools/run_sandbox_demo.py`. It checks preflight and refuses when blocked. It deliberately refuses a bad thermal mapping, corrects it, runs bounded analysis/SPICE, obtains trusted rehearsal, submits a reviewable proposal and verifies the exported bundle. It never applies the proposal or operates equipment automatically.

## Verification boundaries

Run `make lint typecheck coverage`, property/scenario/soak tests and the Studio browser suite. Normal CI skips `tests/sandbox/test_runtime.py`; that skip means runtime isolation is **unqualified**. Use `sandbox qualify` after resources are available, not a mocked test result, to release an image. This v1 is single-user local infrastructure, not public multi-tenant hosting or safety certification.

Primary implementation references: [Colima commands](https://colima.run/docs/commands/), [Docker resource controls](https://docs.docker.com/engine/containers/resource_constraints/), [Docker network none](https://docs.docker.com/engine/network/drivers/none/), [Docker seccomp](https://docs.docker.com/engine/security/seccomp/), [ngspice 47 release/checksum metadata](https://formulae.brew.sh/api/formula/ngspice.json).
