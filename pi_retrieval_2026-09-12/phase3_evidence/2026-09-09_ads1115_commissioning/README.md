# CertaRig Phase 3 Evidence Record

## Evidence ID

`CERT-P3-COMM-ADS-001`

## Test objective

Demonstrate that the CertaRig Raspberry Pi dry-bench controller boots from its configured microSD card, joins the local wireless network, accepts SSH connections, exposes the I2C controller, and communicates repeatably with the wired ADS1115 analogue-to-digital converter at the planned address `0x48`.

## Scope and safety boundary

- Low-voltage Raspberry Pi and ADS1115 commissioning only.
- ADS1115 analogue inputs A0 to A3 were not intentionally stimulated.
- The relay, indicators, emergency-stop output branch, servo, and hydraulic hardware were not commissioned during this test.
- Successful I2C communication demonstrates digital connectivity. It does not by itself prove analogue calibration, sensor accuracy, wiring insulation, hydraulic performance, or final-system readiness.

## Configuration under test

- Controller: Raspberry Pi 3 Model A Plus Rev 1.1
- Hostname: `certarig-pi`
- Operating system: Debian GNU/Linux 13, arm64
- Network interface: `wlan0`
- SSH service: active
- I2C bus under test: `/dev/i2c-1`
- Expected ADS1115 address: `0x48`
- Pi power-health indicator: `throttled=0x0`

## Procedure

1. The Pi was powered through its normal PWR IN connector.
2. The Mac discovered the Pi at its local IPv4 address and confirmed that TCP port 22 was open.
3. The presented SSH ED25519 key was checked against the previously trusted `certarig-pi.local` identity.
4. An authenticated SSH session was opened as the configured non-root user.
5. Host identity, operating-system, uptime, memory, storage, network, SSH, user-group, Python, and Git evidence was collected.
6. I2C configuration, device nodes, and adapter enumeration were checked.
7. Power throttling and SoC temperature were recorded.
8. `i2cdetect -y 1` was executed five times, with one second between scans.
9. A non-destructive ADS1115 configuration-register read was performed with `i2cget -y 1 0x48 0x01 w`.
10. Kernel logs were searched for undervoltage, I2C failure, and SD/MMC failure messages.
11. The raw transcript was copied from the Pi to the project evidence folder and hashed.

## Results

| Check | Acceptance criterion | Observed result | Status |
|---|---|---|---|
| Boot and identity | Pi boots with planned hostname | `certarig-pi`; uptime 21 minutes | Pass |
| Board identity | Hardware model is recorded | Raspberry Pi 3 Model A Plus Rev 1.1 | Pass |
| Wireless network | `wlan0` is up with a valid local address | Up; IPv4 address assigned | Pass |
| SSH | SSH service is active and login succeeds | Authenticated session completed | Pass |
| I2C configuration | I2C enabled and `/dev/i2c-1` present | Enabled; bus nodes present | Pass |
| ADS1115 discovery | Address `0x48` appears consistently | `0x48` detected in 5 of 5 scans | Pass |
| ADS1115 register communication | Device returns a register word | Returned `0x8385` | Pass |
| ADS1115 supply measurement | VDD to GND is approximately 3.3 V | 3.3 V reported by the operator after the SSH test | Pass |
| Power health | No current or historical throttling flags | `throttled=0x0` | Pass |
| Thermal snapshot | Temperature is recorded | 38.6 degrees Celsius | Pass |
| Targeted fault-log search | No matching undervoltage, I2C, or SD/MMC failures | No matching messages found | Pass |

## Observations

The journal contained repeated IPv6 MLD QRV-clamping warnings. These are network multicast-management warnings and did not prevent IPv4 connectivity, SSH, or I2C communication. They are retained in the raw transcript for completeness and are not classified as an ADS1115 commissioning failure.

The five consistent address scans plus the register response provide strong evidence that VDD, ground, SDA, and SCL are functionally connected well enough for digital communication. After the SSH test, the operator measured 3.3 V from ADS1115 VDD to GND with a multimeter. This value is recorded as operator-reported evidence and was not observed remotely by Codex.

## Remaining gates before analogue acquisition

1. Confirm whether the additional 100 nF VDD-to-GND capacitor is fitted. If omitted for this short digital test, record it as a temporary deviation and fit it before final analogue-quality evidence.
2. Connect and verify only one 10 kohm potentiometer channel first.
3. Measure the potentiometer end terminals and wiper with the Pi powered off before connecting the wiper to A0.
4. Capture minimum, midpoint, and maximum raw ADC values and measured voltages before applying engineering-unit calibration.

## Evidence files and integrity

- `phase3-ads1115-commissioning-2026-09-09.txt`
  - SHA-256: `242904800de341035308a81f8217f853f88ef21879096969ad2a7e6309cefa8c`
- `IMG_1874_ads1115_wiring.png`
  - SHA-256: `09d2bc9cecb9dcd36fc917451573099a6c0da2a57faf090111694ed7c2a2c563`

## Phase 3 report-ready conclusion

The dry-bench controller successfully booted, joined the configured network, and supported an authenticated SSH commissioning session. The Raspberry Pi I2C interface was enabled and the ADS1115 was detected at the planned address `0x48` in five consecutive scans. A direct configuration-register read also succeeded, while the Pi reported no throttling flags or targeted hardware-failure messages. This establishes repeatable digital communication between the Raspberry Pi and ADS1115 and clears the project to proceed to controlled single-channel analogue-input commissioning. The result is evidence consistent with laboratory dry-bench readiness; it is not evidence of hydraulic or capstone-system validation.
