# Repeat actuated sidecar (before 21 Sep)

Not the Phase 3 submission. Same host as 12 Sep. Phase 3 on **8080** stays frozen.

## Must not happen

- `deploy/install_pi.sh` on this host
- Platform evidence written into `phase3_evidence/`
- Two kernels owning GPIO23 / ADS1115 at once
- Auto-energize from interview or a photo

## Playbook

1. Pause the frozen `live-dashboard` on 8080 (files untouched). Restore note: `~/certarig-platform/PHASE3_RESTORE.txt`.
2. On the Pi, in `~/certarig-platform` only:

```bash
export GPIOZERO_PIN_FACTORY=lgpio
# venv must have been created with --system-site-packages
.venv/bin/python -m certarig edge serve --port 8081
```

3. Observe-only. Full P1/P2 sweep. `adc_validation` must pass before anyone arms.
4. From the Mac: `certarig sim stamp-gate` then `certarig evidence accept-twin-gate --from <sim-lib> --into <sidecar-evidence>`.
5. Set `CERTARIG_ENABLE_ACTUATION=1` on the sidecar env only after the sweep. Ladder, in order: `relay_truth_table` → `pressure_guardrail` → `flow_guardrail` → `dual_pot_guardrail` → `estop_anti_restart`.
6. Optional extra: run the **text** interview on the Mac simulator, apply a trip there, then talk through the same map on the sidecar. A human still applies. Do not arm from the interview.
7. Pull zips to `evidence/lab-pulled/` (gitignored) and `/tmp/certarig-lab-pulled/`.
8. Stop 8081. Restore 8080 observe-only. `CERTARIG_ENABLE_ACTUATION=0`. Run `tests/hil/test_phase3_untouched.py`.
9. Halt: force_safe → SIGINT (serve restores it if nohup ignored it) → `sudo shutdown -h now` → wait for the green SD LED → pull PWR IN.

Film ten seconds of the pots during the actuated ladder. That is the only metal shot in the 90-second product film.

Write what actually happened into a new dated file next to this one. Empty sections stay empty.
