# Gate 1 reimage recovery summary

> Superseded interpretation notice: this recovery capture used gpiozero's active-low logical `DigitalInputDevice.value` and mislabeled it as the raw electrical GPIO24 level. Direct `pinctrl` verification and corrected G1-A03 captures subsequently proved released=LOW/healthy and latched=HIGH/active. The reimage and software recovery results below remain valid; the GPIO24 interpretation does not.

Date: 11 September 2026  
Capture window: 21:03:15 to 21:03:34 IST  
Scope: Pi-only recovery and monitor-only dry-bench verification

## Configuration held safe

- 1 A branch fuse removed.
- K1 contact COM disconnected.
- Relay CH1 disconnected from the BC547 collector path.
- Both potentiometers at zero/off.
- Pi powered only through micro-USB PWR IN.
- No `permit` command issued.

## Verified recovery

| Check | Result |
|---|---|
| Host | `certarig-pi`, private LAN address redacted from the public record |
| OS | Debian GNU/Linux 13 (trixie), aarch64 |
| Kernel | `6.18.34+rpt-rpi-v8` |
| SSH | Active and authenticated |
| Root filesystem | 117 GB total, 110 GB available at baseline |
| Throttling | `0x0` |
| Temperature after reboot | 41.9 C |
| I2C | `/dev/i2c-1` and `/dev/i2c-2` present |
| ADS1115 | Detected at `0x48` on bus 1 |
| Repository commit | `a06d4d20711a01c2ad76ae10a72a097ca2b2729c` |
| Software check | 6 JavaScript tests and 19 Python tests passed; build and evidence generation passed |

## Monitor-only result

Evidence file: `gate1_reimage_monitor.csv`  
SHA-256: `140eca6680c7bd2958a92c7772fe28008f63370789dcb67e34838599385efa5a`

| Signal | Result across 188 samples |
|---|---|
| ADS1115 A0 | 0.000000 V minimum and maximum |
| ADS1115 A1 | 0.000000 V minimum and maximum |
| GPIO23 command | LOW throughout |
| GPIO24 raw input | HIGH throughout |
| E-stop interpreted state | Active throughout |
| Trip latch | Latched throughout |

## Decision

The HOLD recorded at the time of this capture was superseded by G1-A03 after the raw-level bug was corrected. The authoritative corrected capture proves the physical pin 18 (BCM GPIO24) through NC1 to physical pin 20 (GND) loop produces LOW when released and HIGH when latched. Gate 1 is passed; the project may proceed to the isolated Gate 2 relay-characterization procedure.
