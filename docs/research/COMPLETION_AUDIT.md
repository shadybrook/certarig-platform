# Machine integration research audit

Objective: research whether the next CertaRig platform can let LLMs operate existing CNC, filament, resin and related bench machines, and find a concrete path to a successful implementation.

Audit performed 7 November 2026. This concludes the research and software feasibility experiment. Deployment on particular physical machines remains the next implementation phase.

## Requirements and authoritative evidence

- **Inspect the current platform:** source commit `f77ccaaa3ffd12cdb87b2c3fa0a627315b556998`, current README, `HardwareAdapter`, MQTT TagBus adapter, `AgentSession`, `ToolExecutor`, provider model and transcript classes were inspected. The machine tools use the existing AgentSession without altering its code.
- **Find CNC integration abilities:** upstream GRBL and LinuxCNC interfaces, FANUC's FOCAS2 description and Siemens' Access MyMachine OPC UA manual were checked. The research report explains their different access conditions and distinguishes data interfaces from motion authority. The GRBL request bytes are tested; connected CNC execution remains pending.
- **Find filament printing abilities:** OctoPrint and Moonraker APIs, PrusaLink's published specification, and Bambu's Fleet Hub API were reviewed. OctoPrint's real controller backend was exercised locally, while the other routes are explicitly labelled as documented or format-tested.
- **Find resin printing abilities:** manufacturer-published SDCP 3.0 and Formlabs' developer portal and quickstart were checked. SDCP command frames were tested. Connected resin execution remains pending.
- **Demonstrate a concrete software success:** `evidence/machine-control/octoprint-virtual-final/result.json` records 12 passing checks, six agent tool outcomes, observed controller transitions and a short virtual job completed at 100%. The result labels the virtual machine, scripted provider and automated approval harness.
- **Verify authority boundaries:** 21 focused gateway, protocol and tool tests passed. Existing agent tests also passed, giving 52 tests in the generated JUnit report. Tests include approval replay, expiry, different artifact, wrong identity, non-finite or stale observations, ambiguous dispatch, extra tool arguments, redirects and refusal of a hardware serial port.
- **Verify evidence and cleanup:** `tools/verify_machine_evidence.py` validated all 12 checks, 15 audit records, six tested source file hashes, six agent transcript results and normal controller shutdown. Type checking passed for all four machine package files. Lint and `git diff --check` passed. The canvas compiled against the installed host declarations.
- **Explain next steps without inflating the result:** the report specifies a physical filament trial, a separate CNC trial, a separate resin trial, live-model evaluations and customer evidence. It identifies missing durable recovery, telemetry freshness, configuration-bound approvals, exclusive controller ownership and atomic job validation.

## Boundaries of this result

This experiment does not prove physical machining, print quality, a certified safety system, compatibility with every OEM machine, or live LLM decision quality. It establishes documented control routes for the requested categories and a working real-controller software path through the existing CertaRig agent architecture. Controller-specific deployment must preserve these distinctions.

The original checkout and its uncommitted film edits were left intact. All additions live in the separate `research/machine-control-2026-11-07` checkout. No research code was published to GitHub during this task.
