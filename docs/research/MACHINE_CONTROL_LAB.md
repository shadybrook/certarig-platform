# Run the CertaRig machine control lab

This branch tests the existing CertaRig agent tool loop against an actual OctoPrint server with its official VIRTUAL printer. No hardware serial port is accepted. The provider and operator approvals are scripted by the test harness. See the [feasibility study](2026-11-07-machine-control-feasibility.md) for CNC, resin and OEM paths.

Use Python 3.11 for this pinned OctoPrint experiment. From this checkout:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
python3.11 -m venv .venv-controller
.venv-controller/bin/python -m pip install 'OctoPrint==1.11.8'
.venv/bin/python -m pytest tests/unit/test_machine_gateway.py -q
PYTHONPATH=. .venv/bin/python tools/run_machine_virtual_lab.py --out evidence/machine-control/my-new-run
PYTHONPATH=. .venv/bin/python tools/verify_machine_evidence.py evidence/machine-control/my-new-run
```

Each output directory must be new. The temporary server listens on a dynamically allocated loopback port, connects only to `VIRTUAL`, and stops in a `finally` block. The harness disables access control solely for its short-lived loopback-only controller fixture; do not reuse that configuration for a networked installation. API keys and approval IDs are generated for each run and redacted from the exported transcript. The original job contains only unit selection, positioning mode and dwell commands; it requests no heat, spindle or physical travel.

The experiment checks six agent tool outcomes: start refused without approval, start accepted with approval, pause accepted, resume refused without approval, resume accepted with fresh approval, and cancel accepted. Controller polling separately confirms Operational, Printing, Paused, Printing and Operational. A second short job must finish at 100%, giving 12 integration checks.

## Evidence and verification

The final validated run is [octoprint-virtual-final](../../evidence/machine-control/octoprint-virtual-final). The source manifest binds the run to the experimental files; the source commit records the parent checkout. Verification also checks audit integrity and successful server cleanup. A hash chain detects edits only when its final hash is trusted separately; it is not a digital signature.

Earlier attempts are kept to make failures inspectable. The first two encountered OctoPrint's temporary startup server returning an incomplete response or resetting its connection. The harness now retries those startup conditions. The third attempt completed all 12 checks. The final attempt regenerates complete source-bound evidence after formatting and test improvements. No physical machine is represented by any of these runs.

## Agent integration

`MachineTools` implements the existing `ToolExecutor` interface. Pass it to `AgentSession` with a machine-specific system prompt. Any existing compatible provider can supply typed tool calls; the test uses `FakeProvider` so results do not depend on a paid API. The model sees `machine_status` and `machine_command`, with no tool for minting approvals. Only the trusted operator process calls `Gateway.approve`.

`protocols.py` contains request builders for Moonraker, GRBL and SDCP 3.0. These are format tests, not live integrations. The feasibility report identifies the additional work for each controller and the limits of this prototype.
