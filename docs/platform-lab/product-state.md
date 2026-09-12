# CertaRig product state (12 Sep 2026)

Two worlds. Do not mix them.

## World A — Phase 3 course submission (frozen until 21 Sep)

- Tree: `/home/chintan/certarig-phase-2-poc` on the Pi, also the frozen Mac PoC.
- Command: `python3 -m certarig_edge.cli live-dashboard` on **port 8080**, observe-only.
- Restore: `~/certarig-platform/PHASE3_RESTORE.txt` on the Pi.
- Never run `deploy/install_pi.sh` on that host. Never write platform evidence into `phase3_evidence/`.
- GBrain: never write onto `certarig-phase3-*` pages.

## World B — this repository (the product)

A user-deployable test-operations platform: agent interprets, kernel compares numbers and owns the output.

Stranger path (no Pi):

```bash
make install && make check
.venv/bin/python -m certarig sim serve --port 8080
# or: docker compose -f deploy/docker-compose.yml up --build
```

Studio: http://127.0.0.1:8080/ with the documented demo operator key.

### What is proven

- Deterministic kernel, procedures, twin-gate, checksummed evidence, Fake agent.
- Simulator / Docker first-run.
- MQTT and Modbus TCP **observe** adapters.
- Optional dry-bench lab on a **sidecar** folder + **port 8081** (12 Sep 2026): full observe then actuated ladder. See [2026-09-12-dry-bench.md](2026-09-12-dry-bench.md).
- Studio Live graph shows **both** pot channels (pressure and flow) with trip lines.

### What is not proven / not built

- Agent-led commissioning of an *unknown* bench from a diagram (no pin OCR, no auto-energize). The thin interview is built: [commissioning-interview.md](commissioning-interview.md).
- Live Anthropic/OpenAI on a real key (adapters exist; default stays Fake).
- OPC-UA, CAN, NI-DAQ, PLC, SSO, billing.
- Installing this repo over the Phase 3 demo.

## Lab host facts (no secrets)

- Host: `certarig-pi.local`, user `chintan`, Raspberry Pi 3 Model A+. SSH key auth (`~/.ssh/id_ed25519`).
- Sidecar: `/home/chintan/certarig-platform`, port 8081, env `~/certarig-platform.env` (mode 600). After the lab, `CERTARIG_ENABLE_ACTUATION=0`.
- Start sidecar with `GPIOZERO_PIN_FACTORY=lgpio` and a venv that has `--system-site-packages` (needs system `lgpio`).
- Two kernels must not both own GPIO23 / ADS1115.
- Halt: SIGINT the dashboard/sidecar first, then `sudo shutdown -h now`, wait for the green SD LED, then pull PWR IN. `nohup` can ignore SIGINT; start with SIGINT restored or use SIGTERM only after `force_safe`.

## Next product step

Interview + Onboard add/remove + capability toggles are in this tree. Prove them on the simulator (including `config/rig.thermal.sim.json`). Do not run another actuated lab on the submission Pi before 21 Sep.
