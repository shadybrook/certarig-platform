# Codex Cloud feasibility — 13 November 2026

## Decision

Use Codex Cloud for platform development, simulator services, regression tests and a task-scoped demonstration. The implemented CertaRig Sandbox cannot run unchanged: it explicitly requires a dedicated macOS Colima context/socket and an ARM64 worker image. A native Linux backend and real-container qualification are required before submitted Python or SPICE can execute there.

No Codex Cloud task, CertaRig environment, worker image or hosted service was created during this review. The app lists a runnable default cloud environment, but no published environment dedicated to CertaRig. This is configuration availability, not a measurement of a running VM's Docker capabilities.

The four Sandbox implementation commits are published on `capstone/sandbox-2026-11-13`, based on the latest published capstone progress at `6c009303960ebd9441400d01a20f6da02f2b1a5a`. Existing evidence and the later hobby-bench revision are retained. The subsequent completed-run replay feature remains planned, not implemented by this publication.

## What can run

- **Platform and Studio:** Python/Node development, fixture-agent workflows, simulator procedures, approval refusal/recovery, evidence export and automated browser checks. Start services on loopback for same-VM tests; do not expose development credentials publicly.
- **Sandbox software checks:** Contracts, broker persistence, API permissions, mocked launch policy and trusted simulator tests. These tests do not prove container isolation.
- **Disposable worker execution:** Conditional on the Linux changes and measured Docker/cgroup/seccomp enforcement below. There is no host-process fallback.
- **Physical bench:** Not part of this cloud task. No Pi deployment, private-network discovery, hardware commands or physical commissioning.

Treat Codex Cloud as a coding and demonstration workspace. Do not rely on a task for permanent hosting or durable evidence storage. Commit source and export important results before ending work; a published environment is reusable setup, not a production deployment.

## Source findings and required changes

1. `certarig/sandbox/cli.py` always starts Colima and builds `linux/arm64`. Add an explicit operator-selected native Linux backend. Detect the VM architecture and pin the resulting native image ID. Keep the existing Mac backend intact.
2. `certarig/sandbox/engine.py` requires the Colima context, home-directory socket, SSH mount check and ARM64 image. The Linux backend must target the managed local Unix Docker socket explicitly, reject remote endpoints and verify the actual security/resource controls. Worker code must not select a backend or launch options.
3. Build steps need the cloud environment's permitted package/download destinations and proxy trust. Use build-only CA secret mounts where required by curl/pip; do not bake session trust files or credentials into image layers. Resolve SourceForge redirect hosts from actual failures rather than enabling unrestricted internet access.
4. Docker clients can supply proxy variables to new containers. Explicitly clear upper/lower-case proxy variables for workers, retain `--network none`, and pass no host credentials, CA mounts, devices or Docker socket. Build networking and worker networking are separate.
5. Preserve UID 10001, read-only root, dropped capabilities, no-new-privileges, seccomp, memory/swap/PID/CPU limits, tmpfs quotas, container lifetime limits and safe artifact handling. Refuse execution when the managed daemon cannot enforce a requirement.
6. Bind qualification and receipts to the backend/platform, immutable image, launch policy and verifier. Never reuse a Mac qualification as proof of Linux isolation. Use native architecture rather than relying on unmeasured emulation.

The shared broker remains outside Edge acquisition. Edge and the broker communicate over the private Unix socket. Only the broker accesses Docker. Submitted code stays inside disposable workers.

## Capacity and capability gate

Require at least 8 GiB **free**, not total disk capacity, after checkout and dependency preparation. Measure usable VM/cgroup memory and reserve headroom for Edge, Docker and the agent before enabling jobs. The existing Linux resource probe does not yet establish this memory headroom.

The official documentation currently lists 8 GiB total disk for Plus/Edu Plus and 32 GiB for Pro/Business/Enterprise/Edu/Edu Pro. An 8 GiB total-disk VM will not satisfy the current 8 GiB-free requirement after checkout; this is an inference from the documented capacity and our policy. Prefer the 16 GiB-memory/32 GiB-disk configuration where the account provides it, and verify actual available resources. Do not provision a paid upgrade automatically.

In the actual cloud task, first inspect the attached environment's status and native architecture. Then check the managed Docker daemon without inherited endpoint selectors:

```sh
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
  -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock info
```

Inspect enforcement and run bounded qualification tests. Do not print Docker credentials or the full process environment. A ready saved environment or successful `docker info` alone is not qualification. If the daemon is inaccessible or resource controls are unavailable, report the blocker and leave execution disabled.

## First Codex Cloud task

Use the runnable default environment or prepare a private reusable CertaRig environment. Select `shadybrook/certarig-platform`, branch `capstone/sandbox-2026-11-13`, and use this work order:

> Check out the published Sandbox branch. Read the project guidance, Sandbox status and this cloud review. First record the exact commit, VM architecture, available disk/memory, managed Docker readiness and security capabilities without exposing credentials. Run platform lint, typing, coverage, property/scenario, soak and browser checks with the fixture provider. Keep physical adapters, live provider calls and public hosting disabled. Implement a native Linux Docker backend without weakening the existing Mac backend or worker isolation. Build and pin a native worker image with correct build-only proxy trust. Run every real-container isolation/fault test, both supported simulator journeys, raw-evidence verification and the success/refusal demo. If containment cannot be enforced, complete only the software checks and report the precise blocker; never execute submitted code directly on the VM. Export logs, raw traces, image/policy identities and verification results. Commit reviewable changes on a separate branch and create a draft PR. Do not merge, deploy to the Pi, buy services, or claim qualification from mocks or skipped tests.

Before calling that task started, retain its actual cloud task ID and repository/commit. Before calling the Sandbox qualified, retain the real test report and passing image/policy binding. Starting the task is a separate action from publishing source or evaluating feasibility.

## Required evidence

- Full regression with the unchanged 90% coverage gate, soak and relevant browser checks.
- Real-container host-file/credential/socket/device/network isolation; timeout; memory; process limit; excessive output; ngspice; trusted rehearsal and repeatability tests.
- Linux-specific proof that no proxy credentials or host mounts reach workers and that effective limits match the declared policy.
- Successful and refused workflows for both simulator profiles, plus a portable bundle that verifies offline and fails after corruption.
- Explicitly separated historical local results, new cloud software results and actual container qualification. Current local runtime qualification remains outstanding.

## Official references

- [Codex Cloud overview](https://learn.chatgpt.com/docs/cloud): remote coding tasks and repository workflows.
- [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments): setup, saved state, variables/network secrets, network policy and VM specifications.

The environment-specific Docker capabilities must be inspected in the running task. This review did not create one or establish an always-on hosting guarantee.
