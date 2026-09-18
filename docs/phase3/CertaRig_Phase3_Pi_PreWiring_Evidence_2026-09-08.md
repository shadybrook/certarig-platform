# CertaRig Phase 3 Raspberry Pi Pre-Wiring Evidence

Date: 8 September 2026  
Evidence capture time: 14:21 IST  
Scope: Low-voltage dry hardware bench preparation before ADS1115 wiring

## Result

The Raspberry Pi 3 Model A+ was successfully commissioned on the local network. Remote SSH access, I2C support, the CertaRig software toolchain, the repository test suite, the mock edge service, and the Pi-hosted dashboard were all verified. No GPIO output, relay, ADS1115, potentiometer, indicator, or emergency-stop wiring was connected during this stage.

## Raspberry Pi identity and connectivity

| Check | Verified result |
| --- | --- |
| Hostname | `certarig-pi` |
| Local address | `certarig-pi.local` |
| IPv4 address at capture | Redacted from the public evidence copy |
| Operating system | Debian GNU/Linux 13 (trixie), Raspberry Pi OS 64-bit image |
| Kernel | `6.18.34+rpt-rpi-v8` |
| Architecture | `aarch64` |
| SSH | Enabled and verified from the Mac |
| Wi-Fi | Connected and reachable from the Mac |

The numeric IPv4 address is assigned by the router and may change after a reboot. The preferred connection name is `certarig-pi.local`.

## Installed toolchain

| Tool | Verified version |
| --- | --- |
| Git | 2.47.3 |
| Python | 3.13.5 |
| Python virtual environments | Available |
| Node.js | 20.19.2 |
| npm | 9.2.0 |
| i2c-tools | 4.4 |
| gpiozero | 2.0.1.post3, isolated project environment |
| smbus2 | 0.6.1, isolated project environment |

## I2C readiness

- I2C is enabled in the Raspberry Pi boot configuration.
- `/dev/i2c-1` and `/dev/i2c-2` are present.
- The `chintan` account belongs to the `i2c`, `gpio`, `spi`, and `sudo` groups.
- A pre-wiring scan of bus 1 completed successfully and returned no detected addresses, which is the expected safe baseline while the ADS1115 is disconnected.
- The expected ADS1115 address after correct wiring is `0x48`.

## Repository deployment

| Check | Verified result |
| --- | --- |
| Repository | `https://github.com/shadybrook/certarig-phase-2-poc` |
| Pi checkout | `/home/chintan/certarig-phase-2-poc` |
| Verified commit | `6cc4e75944aca748f4a7f7840f99b0b5293eae8b` |
| Branch | `main`, tracking `origin/main` |
| Initial clone status | Clean |

Runtime validation created three untracked local-only artifacts: the SQLite WAL and shared-memory files and editable-install metadata. These are execution by-products, not source-code changes.

## Automated validation

The complete repository check was run directly on the Raspberry Pi with `npm run check`.

| Validation | Result |
| --- | --- |
| JavaScript test cases | 6 passed, 0 failed |
| Python unit and HTTP workflow tests | 8 passed, 0 failed |
| Static dashboard build | Passed |
| Phase 2 evidence generation | 4 bundles generated |
| Python tests repeated inside the Pi virtual environment | 8 passed, 0 failed |

The verified cases include the approved baseline, swapped channels, missing calibration, pressure-limit abort, safe-state behavior, approval gating, stable configuration hashing, and stable evidence checksums.

## Running mock services

| Service | Pi endpoint | Mac verification |
| --- | --- | --- |
| CertaRig edge API | `http://certarig-pi.local:8080` | `/health` returned `status: ok` |
| Pi-hosted dashboard | `http://certarig-pi.local:8000` | HTTP 200 |

The API reported `hardware_mode: mock` and `output_safe: true`. Its `actuation_enabled: true` field denotes that mock test transitions are permitted; it does not represent a physical GPIO output. The server was started with physical actuation disabled, and no output wiring was attached.

The dashboard was opened from the Mac using the Pi hostname. Case 4, pressure safety limit breach, was selected and run through the browser interface. It completed with the expected `Safe abort` decision and displayed a maximum synthetic pressure of 6.04 bar. A dashboard capture was retained in the task output.

These two services were started manually for this validation session. They will stop when the Pi is shut down and must be restarted after boot unless a reviewed system service is installed later.

## Safe power cycle procedure

1. From SSH, run `sudo shutdown -h now`.
2. Wait until SSH disconnects and green SD-card activity has stopped.
3. Remove power from the Pi PWR IN connector.
4. To restart, reconnect the same regulated Pi supply and wait approximately one to three minutes.
5. Reconnect with `ssh chintan@certarig-pi.local`.
6. Restart the edge API and dashboard if required, because they are currently manual processes.

After reconnecting, the manual restart sequence is:

```bash
cd ~/certarig-phase-2-poc
CERTARIG_OPERATOR_KEY='<enter the local operator key>' CERTARIG_ENABLE_ACTUATION=0 nohup .venv/bin/python -m certarig_edge.cli serve --config config/rig.example.json --bind 0.0.0.0 --port 8080 > ~/certarig-edge.log 2>&1 &
nohup python3 -m http.server 8000 --bind 0.0.0.0 --directory dist > ~/certarig-dashboard.log 2>&1 &
```

The operator key must be supplied at runtime and must not be committed to Git, placed in evidence, or saved in GBrain.

The operating system, hostname, Wi-Fi profile, SSH configuration, installed packages, repository, and project files persist on the microSD card. A shutdown only loses unsaved in-memory state and stops running processes.

## Gate before ADS1115 wiring

- Shut the Pi down cleanly and remove power before making any wire connection.
- Keep the relay, indicators, emergency stop, and all output GPIO disconnected.
- Wire only ADS1115 VDD, GND, SDA, and SCL in the next controlled stage.
- Use 3.3 V for ADS1115 VDD and ensure all analogue inputs remain within 0 to 3.3 V.
- Inspect the completed wiring before power-up.
- After power-up, rerun `i2cdetect -y 1` and accept only the expected `0x48` result before proceeding.

## Current conclusion

The pre-wiring software and network gate is passed. The next controlled activity is the four-wire ADS1115 connection and I2C address verification. This is readiness evidence for the Phase 3 dry bench; it is not evidence of hydraulic commissioning, which remains reserved for the capstone.
