# CertaRig expansion into CNC and additive machine control

Research and executable feasibility result, 7 November 2026.

## Decision

This is a feasible extension of CertaRig. Existing controllers already expose the job and status interfaces an LLM can use through bounded tools. The best first product is an operator assistant that prepares a job, checks it against a commissioned machine profile, requests approval, runs it through the manufacturer's controller, observes progress, and exports evidence. A controller remains responsible for trajectories and machine timing.

The first software integration succeeded against real OctoPrint 1.11.8 with its bundled VIRTUAL printer. The existing CertaRig AgentSession called the new machine tools, which used HTTP rather than an in-process imitation of the API. The experiment confirmed start, pause, resume, cancel, refusal of unapproved start and resume, and completion of a second job at 100%. The provider was FakeProvider with scripted responses; approvals came from the automated test harness. There was no physical printer and no live LLM inference.

The inspected source is CertaRig at commit `f77ccaaa3ffd12cdb87b2c3fa0a627315b556998` in the local `CertaRig_CursorControl` repository, whose remote is `shadybrook/certarig-platform`. The user called the direction Soteric; no repository or product rename is assumed. The research lives in a separate checkout and branch so the current film work can continue independently.

## What control means for this product

There are four useful levels. Each requires its own evidence.

1. **Understand:** read machine state, current job, errors, temperature, position and progress where the controller exposes them; explain those observations with their timestamps.
2. **Operate jobs:** choose a prepared artifact, queue or start it with approval, pause or cancel it, and require a fresh approval for resume. This level has an executable controller integration in this branch.
3. **Prepare parts:** convert a natural-language specification into editable CAD, use an established slicer or CAM system, inspect the resulting artifact and machine profile, then submit it for approval. CAD/CAM generation and collision validation are additional components and have not been built here.
4. **Adapt during execution:** change feed, speed, temperatures or other process parameters inside commissioned bounds using verified telemetry and controller-specific rules. This requires substantially more machine evidence. A model's reasoning latency is unsuitable as the trajectory or emergency control loop.

The ability to submit a job does not establish that its geometry, cutting conditions, supports, exposure settings or final part are correct. A successful API response also does not establish physical motion or a completed part.

## Available interfaces and realistic machine coverage

### Filament printers

**OctoPrint: implemented and tested against its real virtual-printer backend.** The job REST API supports explicit start, pause, resume and cancel operations. File selection is a separate API operation. The integration uses explicit pause and resume actions because the default pause command can toggle state. Access depends on the printer being supported by the installed OctoPrint connection and firmware. It is not universal compatibility with all printers sold by a manufacturer. Sources: [job API](https://docs.octoprint.org/en/main/api/job.html), [file API](https://docs.octoprint.org/en/main/api/files.html), [official virtual printer](https://docs.octoprint.org/en/main/development/virtual_printer.html).

**Klipper through Moonraker: strong next adapter.** Moonraker exposes status queries, print lifecycle operations and a dedicated emergency-stop endpoint. A queued `M112` sent through the G-code endpoint may wait behind other commands; the dedicated emergency-stop route has different semantics. The branch includes tested request builders, not a connected Moonraker implementation. Exact printer objects and macros must be commissioned per installation. Source: [Moonraker printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/).

**PrusaLink: a documented manufacturer route.** Prusa publishes an OpenAPI contract, and releases describe the newer API and file upload path. Map supported endpoints to the exact printer and firmware; do not assume all PrusaLink deployments implement the same capabilities. No Prusa device has been connected here. Sources: [Prusa API specification](https://github.com/prusa3d/Prusa-Link-Web/blob/master/spec/openapi.yaml), [PrusaLink releases](https://github.com/prusa3d/Prusa-Link/releases).

**Bambu: use an authorized integration route.** Current research found the manufacturer's Fleet Hub HTTP API v1.0.0 dated 20 May 2026. It provides device status, print submission and lifecycle actions, with hub activation, client certificates and session authentication. This adds hardware and onboarding requirements. The documented response is acknowledgement and status updates can lag, so polling must confirm the resulting state. Bambu also documents LAN Developer Mode, with model and firmware restrictions. This research has not validated either path on a device. Sources: [Fleet Hub API](https://portal.bblmw.com/fleet-hub/wb76oog4i8k/files/Bambu%20Fleet%20Hub%20HTTP%20API%20EN%20v1.0.0.pdf), [Bambu security white paper](https://cdn1.bambulab.com/trust-center/file/bambulab-security-whitepaper-en.pdf). Verify current eligibility and compatible hardware before any purchase.

### Desktop and industrial CNC

**GRBL: feasible through the controller's serial protocol.** Its official interface specifies status requests, feed hold, resume, line responses and streaming rules. This branch builds the documented real-time bytes for status, hold and resume; it does not yet stream cutting programs. Feed hold is not a verified emergency stop or spindle power removal. A full sender must handle alarms, homing, coordinate systems, units, buffer flow and recovery without replaying uncertain motion commands. Source: [GRBL interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md).

**LinuxCNC: feasible through a local controller service.** The Python NML interface exposes status, command and error channels, including program loading and automatic run, pause, resume and abort. A service on the LinuxCNC host can expose bounded job tools to the CertaRig edge node. It needs controller mode and state checks plus the configured machine's travel, tool and fixture information. No LinuxCNC system has been run in this experiment. Source: [stable LinuxCNC Python interface](https://linuxcnc.org/docs/stable/html/config/python-interface.html).

**FANUC and Siemens: technically possible but machine-specific integration work.** FANUC's FOCAS2 documentation describes Windows applications with read and write access to CNC data. Siemens documents Access MyMachine OPC UA permissions for CNC and PLC data and methods. Those facts do not establish a universal remote cycle-start API on every installed machine. Controller options, SDK licensing, OEM PLC logic, operating modes and owner authorization must be checked on the target installation. Sources: [FANUC FOCAS2](https://www.fanucamerica.com/products/software/cnc/focas2-library), [Siemens configuration manual](https://cache.industry.siemens.com/dl/files/214/109817214/att_1129895/v1/ONE_OPCUA_config_man_0123_en-US.pdf).

**MTConnect is useful for observation.** Its own documentation describes read-only HTTP communication. A machine exposing MTConnect therefore has an observation route, but that alone does not provide actuation authority. Source: [MTConnect](https://www.mtconnect.org/).

### Resin printers

**SDCP 3.0: a published controller protocol.** CBD/CHITU publishes device discovery, WebSocket transport, capability reporting, file transfer and print control. Start, pause, stop and continue use commands 128 through 131. The branch tests message construction only. A target device must advertise the required capabilities and accept a file sliced for its model and firmware; generic G-code from a filament printer is not a resin job. Source: [manufacturer protocol](https://github.com/cbd-tech/SDCP-Smart-Device-Control-Protocol-V3.0.0/blob/main/SDCP%28Smart%20Device%20Control%20Protocol%29_V3.0.0_EN.md).

**Formlabs: a supported preparation and job route.** Its developer portal separates PreForm preparation and submission from Dashboard fleet information. The official quickstart prepares a scene and queues a job with `print_now=False`; it also explains the alternative Print Now operation. Use the supported machine, material and printability checks. No printer or authenticated Formlabs account has been used here. Sources: [developer portal](https://developer.formlabs.com/), [first-script workflow](https://developer.formlabs.com/getting-started/quickstart/).

## Fit with the existing platform

Reusable pieces are the provider-neutral AgentSession, capability-restricted tool list, operator approval workflow, procedure runtime, simulation gate concept and inspectable evidence. The existing binary `HardwareAdapter.set_valve` and pressure/flow ProcessGuardrail should not be presented as a printer or CNC abstraction. The MQTT adapter inspected here is backed by an in-process TagBus; its name alone is not evidence of a production broker integration.

Add a machine service beside the commissioned bench path. Its contract needs commissioned machine identity, controller and firmware versions, supported actions, state and telemetry quality, job identity and immutable content hash, preparation profile, command acknowledgement, observed result, and recovery policy. Printer temperature, CNC offsets and resin exposure require different validation rules.

The flow is: operator request → model proposes typed job action → machine policy checks authority, state and artifact → adapter talks to controller → controller executes → state is observed → evidence is exported. The model gets neither an approval-minting tool nor a raw controller console. Firmware interlocks and physical emergency systems remain responsible for their specified functions.

## Executable proof in this branch

The prototype adds `certarig/machines/gateway.py`, `agent_tools.py`, `protocols.py`, a virtual integration harness and focused tests. Start and resume need an approval bound to machine, action, filename and SHA256, with expiry and one-use consumption. Unknown commands, extra tool fields, invalid paths and unexpected states are refused. A dispatch exception latches uncertainty and prevents another start or resume in the same gateway instance.

The HTTP adapter deliberately requires a literal loopback address and verifies that OctoPrint's active serial port is `VIRTUAL` before any job write. This is a working controller integration experiment. A physical adapter needs a commissioned profile and the additional checks below before lifting that restriction.

The final evidence folder is `evidence/machine-control/octoprint-virtual-final`. Its `result.json`, sanitized agent transcript, hash-chain audit, source manifest and cleanup record establish what actually ran. The harness generates temporary credentials and stops the temporary server. Test approvals are explicitly labelled `automated_test_harness`; they are not claimed as an operator approval trial. Focused tests cover 21 gateway, protocol and agent-boundary cases. The verification script checks the actual action sequence, 100% completion, audit chain, matching source hashes and controller shutdown.

## Remaining engineering work

- Physical adapters must identify the actual printer or CNC and reconcile controller state with physical readiness. A recent HTTP response can still contain old firmware telemetry. Device timestamps, event progression and disconnect behavior need validation.
- Bind approval to machine configuration, slicer or CAM profile, firmware, tool and fixture setup as well as file content. The research gateway binds the job intent only.
- Prevent remote artifact mutation and concurrent-client races between validation, selection and start. The existing API calls do not provide an atomic compare-and-start transaction. Use unique immutable job storage and exclusive controller ownership where possible.
- Make uncertainty and anti-restart state durable across process restarts. The prototype latch is in memory. Add state reconciliation and explicit operator recovery before a physical release.
- Ensure pause, cancel, hold and emergency actions have tested machine-specific effects. A failed network path cannot guarantee a machine stop. Retain controller-native and physical protections.
- Add real model trials using the existing provider adapters after the deterministic path is validated. Test misleading filenames, embedded instructions, model retries, conflicting operator requests and refusal handling. No paid provider was used in this study.
- Close the part-quality loop using dimensions, photographs, inspection criteria and process outcomes. Controller completion is only one result.

## Recommended delivery sequence

First use one accessible OctoPrint or Klipper filament printer for a complete approved job lifecycle. Commission its exact firmware, material and slicer profile; capture status before and after every operation and inspect the completed part. Success means a repeatable part plus a complete evidence record, including one intentional refusal and one interrupted-job recovery.

Next validate a GRBL or LinuxCNC machine with supervised air motion and the spindle disabled using the machine's normal procedure, then a defined cutting task after setup and fixture checks. Record homing, offsets, requested moves, actual state and the inspected part. CNC proof cannot be substituted by the printer experiment.

Then add one specific SDCP resin printer or a Formlabs machine. Validate material and sliced file compatibility, local preparation acknowledgement, upload, start, controlled pause or stop, completion and post-processing inspection. Resin proof cannot be substituted by the protocol frame tests.

Only after those routes work should we expand to other OEMs and parameter adaptation. A useful customer test is a university fabrication lab or prototype shop with repeated jobs and mixed equipment. Measure operator time per job, intervention count, refusal accuracy, trace completeness and acceptable-part rate. The commercial hypothesis is reduced setup and recovery effort with accountable execution; that requires customer evidence.

## Differentiation and conclusion

Natural-language printer control already exists in projects such as [PrintMCP](https://printmcp.org/). A chat interface by itself is therefore a weak differentiator. CertaRig's credible direction is a common commissioning, approval, execution and evidence workflow across specific supported controllers, with tested recovery behavior and part acceptance criteria.

The research establishes technical feasibility across CNC, filament and resin ecosystems, and one working real-controller software integration. Physical compatibility, live model behavior and production reliability remain separate milestones. The next choice should follow the machine we can actually access, rather than a speculative hardware purchase.
