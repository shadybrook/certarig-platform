# CertaRig Phase 3 live guardrail and dashboard SOP

Status: software-validated; physical shadow and armed runs pending  
Scope: low-voltage dry bench and panel indicators only

## What this stage proves

The Raspberry Pi reads P1 on ADS1115 A0, P2 on A1 and the E-stop NC1 input on BCM GPIO24. A deterministic process guardrail decides whether BCM GPIO23 may be HIGH. The same Pi hosts a browser console with live values, rolling charts, guardrail state, expected K1/red/green state and CSV recording.

The dashboard does not override the guardrail. It only submits authenticated `safe`, `reset` and `permit` requests. The current bench has no K1 feedback sensor, so relay and panel-light fields are expected values derived from GPIO23 and the verified K1 NC/NO contact wiring. Physical observations must still be entered in the test record.

## Fixed limits

| Channel | Input | Engineering scale | Safe range | Approximate upper-limit voltage |
|---|---|---|---|---:|
| Pressure emulator P1 | ADS1115 A0 | 0–3.302 V = 0–10 bar | 0–4.2 bar | 1.387 V |
| Flow emulator P2 | ADS1115 A1 | 0–3.300 V = 0–20 L/min | 0–15 L/min | 2.475 V |

The limits come from `config/rig.wave1.json`. Do not change them during a test to make a result pass.

## Deterministic safety contract

GPIO23 is forced LOW at startup and on shutdown. Permit is possible only when:

1. output actuation was explicitly enabled when the service started;
2. E-stop NC1 reports healthy/released;
3. every required sample exists, is finite, has `good` quality and is within its valid range;
4. P1 and P2 are both inside their configured safe ranges;
5. the operator has issued `reset` and then `permit`.

An E-stop, unsafe channel, invalid/missing channel, ADC/runtime exception or output-driver exception clears the permit and latches a trip. Recovery never re-energizes K1. A healthy state followed by a new reset and permit is required.

## Stage 1 laptop validation

Use a private, temporary operator key. Do not write it into the repository or documentation.

```bash
export CERTARIG_OPERATOR_KEY='replace-with-a-private-key-of-12-or-more-characters'
python3 -m certarig_edge.cli live-dashboard \
  --config config/rig.example.json \
  --evidence-dir /tmp/certarig-live-mock \
  --bind 127.0.0.1 \
  --port 8080
```

Open `http://127.0.0.1:8080/#live-bench`. Confirm live telemetry, enter the temporary operator key in the unsaved browser field, test reset, permit, safe, start CSV, stop CSV and download.

Run the full repository check:

```bash
npm run check
```

## Stage 2 Pi shadow run: no relay authority

Keep both potentiometers at minimum before power-up. Keep the E-stop released and the circuit exactly as shown in the final as-built diagram. Power the Pi only through PWR IN. Stop immediately for heat, smell, smoke, sparking, unstable wiring or unexpected relay operation.

Do not set `CERTARIG_ENABLE_ACTUATION` for the shadow run:

```bash
export CERTARIG_OPERATOR_KEY='private-session-key'
python3 -m certarig_edge.cli live-dashboard \
  --config config/rig.wave1.json \
  --evidence-dir phase3_evidence/live_runs \
  --bind 0.0.0.0 \
  --port 8080
```

Open the Pi address from the Mac at `http://PI_ADDRESS:8080/#live-bench`. Verify:

1. P1, P2 and E-stop respond correctly.
2. The service says `MONITOR ONLY`.
3. Reset may clear the software trip when inputs are safe.
4. Permit is rejected with `permit_rejected_monitor_only`.
5. K1 never energizes.
6. Start CSV, move each potentiometer slowly through safe and unsafe regions, operate and release the E-stop once, stop CSV, download it, then force safe and stop the service.

Investigate any invalid or negative near-zero readings. Do not relax the valid range merely to hide them.

## Stage 3 armed dry-bench run

Only after the shadow CSV is reviewed, restart the service with explicit dry-bench actuation authority:

```bash
export CERTARIG_ENABLE_ACTUATION=1
python3 -m certarig_edge.cli live-dashboard \
  --config config/rig.wave1.json \
  --evidence-dir phase3_evidence/live_runs \
  --bind 0.0.0.0 \
  --port 8080
```

The supervised sequence is:

1. Confirm E-stop released, P1 about 2 bar and P2 about 8 L/min.
2. Start CSV.
3. Reset, then permit. Expect K1 on, red off and green on.
4. Raise P1 above 4.2 bar. Expect immediate GPIO23 LOW, K1 off, red on and green off.
5. Attempt permit while P1 remains high. Expect rejection.
6. Return P1 safe. Confirm no automatic restart. Reset and permit again.
7. Raise P2 above 15 L/min. Expect the same forced-safe sequence.
8. Return P2 safe. Confirm no automatic restart.
9. Reset and permit at normal values. Operate the E-stop. Confirm NC2 removes relay-board power while NC1 causes the software forced-safe event.
10. Release E-stop. Confirm reset remains required. Finish in safe state, stop CSV and stop the service.

## CSV evidence fields

Each row records timestamp, elapsed time, both raw voltages and engineering values, per-channel status, E-stop, process health, trip latch, permit request, GPIO23 command, expected relay state, expected red/green state, event and guardrail reason. Stopping a recording returns a SHA256 checksum.

Create the summary and plot with:

```bash
python3 tools/phase3_analyze_live_csv.py phase3_evidence/live_runs/FILE.csv
```

Retain the original CSV, analysis JSON, Markdown summary, SVG plot, checksum, test observations, operating-state photographs and final safe shutdown evidence.

## Claim boundary

Successful completion is evidence consistent with a university low-voltage breadboard PoC. It is not industrial safety certification, relay feedback verification, sensor calibration traceability, hydraulic validation or authorization to connect mains, pumps, valves, motors or pressure-bearing hardware.
