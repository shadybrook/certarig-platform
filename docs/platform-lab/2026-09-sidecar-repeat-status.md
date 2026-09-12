# Sidecar repeat — status (12 Sep 2026)

Playbook: [`2026-09-sidecar-repeat.md`](2026-09-sidecar-repeat.md). Same host as 12 Sep. Phase 3 on **8080** stays frozen.

This file is the dated log the playbook asked for. Empty sections stay empty until the lab actually runs on the Pi.

## What happened

Not run from the cloud agent. `certarig-pi.local` does not resolve here. No SSH path to the dry bench. No `deploy/install_pi.sh`. No write onto `phase3_evidence/`.

Run the playbook from the Mac on the 12 Sep host before 21 Sep. Then fill the tables below and film ten seconds of the pots.

## Gate results

| Gate | Result |
| --- | --- |
| 0 Read-only | |
| 1 Sidecar on 8081 | |
| 2 Observe (`adc_validation`) | |
| 3 Twin-gate stamps | |
| 4 Actuate ladder | |
| 5 Restore 8080 | |

## Pulled bundles

Gitignored destination: `evidence/lab-pulled/` and `/tmp/certarig-lab-pulled/`.

| Procedure | Run | Outcome | Archive SHA-256 |
| --- | --- | --- | --- |
| | | | |

## Halt

force_safe → SIGINT → shutdown → green SD LED → PWR IN. Not performed from this environment.

## Metal shot

Not filmed. The 90-second product film ends on the Studio end card (`certarig.dev`) until this lab produces four seconds of real pots.
