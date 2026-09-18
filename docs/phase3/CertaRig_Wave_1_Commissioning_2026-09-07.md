# CertaRig Wave 1 commissioning record

Date: 7 September 2026. Phase 3 deadline: 20 September 2026.

## Current evidence and corrections

- Photo `81046122762__46DB2DDE-0CDD-439B-AFA9-3E1374C8F2F0.heic` confirms the Mac USB cable terminates at the Pi's micro USB socket labelled `PWR IN`. The steady red light is a power indication, not proof of boot or stable power under load.
- Mac `system_profiler SPUSBDataType` reports two USB controllers and no attached USB devices. This is expected because the Pi 3 A+ `PWR IN` connector is the power input and does not provide the USB device data path.
- User reports soldering headers to an ADS1115 module. Visual and electrical acceptance remain pending; do not mark the module tested.
- User now reports no microSD card available. This supersedes the available status in the 6 September inventory baseline.
- User now reports no multimeter available. This supersedes the available status in the 6 September inventory baseline.
- Separate regulated 5 V relay supply remains unconfirmed.
- All eight local CertaRig reference software tests passed on the Mac using `python3 -m unittest discover -s tests_py -v` from `work/certarig-poc`. The first sandboxed run could not bind the temporary API test port; rerunning with approved localhost access passed all tests. These are mock/software evidence only; they do not establish Pi or ADC operation.
- The complete repository check also passed on 7 September: 6 browser tests, 8 Python tests, static site build and regeneration of 4 evidence bundles. This is the frozen pre-hardware software baseline.

## Boot options

The Pi 3 A+ micro USB socket supplies power; it is not the USB data connection used to load software from the Mac. A prepared microSD remains the preferred persistent installation route.

The official rpiboot project supports Pi 3 A+ and macOS and can load a temporary Linux environment into memory over the USB data connection. Correct cable, power arrangement, boot configuration and a compatible image must be established before attempting it. Stock provisioning firmware is not a complete persistent CertaRig installation.

On 7 September, Homebrew `libusb` 1.0.30 and current `pkgconf` were installed. The official `raspberrypi/usbboot` source at commit `3090a13e` was cloned to `/tmp/certarig-usbboot-20260907` and built successfully as an Apple Silicon ARM64 executable. A verbose handshake attempt reached `Waiting for BCM2835/6/7/2711/2712...` and detected no target, as expected through the current power-only connection. The attempt was stopped without changing the Pi.

A subsequent two-cable experiment used the black Mac-to-`PWR IN` cable and a white cable between the Pi USB A socket and the Mac USB C socket. `rpiboot` continued to detect no target, `system_profiler` listed no USB device, and macOS identified an AC charger. This indicates an unsuitable USB role/power arrangement rather than a Pi data connection. The white cable was rejected for this use and the user was instructed to disconnect it to avoid a power loop between Mac ports. No boot files reached the Pi and no permanent setting was changed.

The user then powered `PWR IN` from an external source while retaining the white Pi USB A to Mac USB C cable. A fresh check again showed no enumerated USB device, while macOS continued to report an AC charger. The external supply therefore did not correct the cable's USB role: the Pi USB A VBUS was presented toward the Mac. The data cable remains rejected and should be disconnected. The planned persistent connection is external 5 V, 2.5 A power plus microSD boot and Wi-Fi/SSH, with no USB data cable.

Raspberry Pi Imager 2.0.11.1 was installed in `/Applications` so the arriving microSD can be provisioned immediately. The intended persistent route is Raspberry Pi OS Lite 64-bit with hostname, Wi-Fi and SSH preconfigured in Imager, followed by Pi-only boot and CertaRig mock deployment.

For a Pi 3 A+ USB gadget/device connection, the data path is the full-size USB A socket. The reference gadget project calls for a custom USB A to USB A data cable with the 5 V conductor disconnected. Provide the Pi's power separately through `PWR IN`; do not join two independently powered USB 5 V outputs. Even after a successful rpiboot handshake, a normal persistent CertaRig deployment still requires boot storage or a purpose-built RAM image.

USB flash-drive boot is a different mode. Pi 3 A+ normally requires prior enablement of a permanent OTP setting, documented using an SD boot. Do not assume a flash drive works on a factory board. No OTP change is planned.

Sources:
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#usb-boot-modes
- https://github.com/raspberrypi/usbboot

## Revised ten-step sprint

| Step | Work and completion evidence | Current status |
|---|---|---|
| 1 | Identify both cable ends, document Pi power LED and host detection | Complete: current cable reaches `PWR IN`; red LED steady; no host detection, as expected |
| 2 | Inspect ADS1115 soldering with clear front and rear photographs | Soldered per user; inspection pending |
| 3 | With power disconnected, use multimeter to check header continuity and investigate possible shorts | Waiting for multimeter |
| 4 | Prepare boot path: microSD preferred; assess temporary rpiboot only with verified connection | Mac mediator built; waiting for storage or correct USB A data connection plus separate power |
| 5 | Boot Pi alone; verify model, OS, access and power status under load | Not started |
| 6 | Deploy CertaRig in mock mode on Pi; check API and software tests | Mac baseline exercised; Pi test pending |
| 7 | Connect one accepted ADS1115 at 3.3 V; enable I2C and verify communication | Not started |
| 8 | Add one pot, then a second; measure voltages and record calibration | Not started |
| 9 | Validate safety logic; commission E-stop, protected relay interface and fused indicator branch | Waiting for prior checks, resistors and confirmed separate supply |
| 10 | Execute named faults and soak test; save measured evidence and complete Phase 3 report | Not started |

Pre-card actions and professor scope questions are controlled in:

- `output/CertaRig_Pre_SD_Action_Plan_2026-09-07.md`
- `output/CertaRig_Professor_Meeting_Questions_2026-09-07.md`

## Next physical action

Obtain a microSD card for the preferred persistent commissioning route. If a temporary USB device boot experiment is still desired, use a correctly prepared USB A data cable with its 5 V conductor disconnected and power the Pi separately through `PWR IN` with the official 5 V, 2.5 A supply. Keep the ADS1115 and output circuits disconnected until inspection and electrical checks are complete. A steady red LED alone is insufficient to mark the Pi accepted.

## Researched boot and connection fallback ladder

The observed steady red PWR LED and inactive ACT LED without a microSD are consistent with normal pre-boot behaviour on a Raspberry Pi 3. They are not evidence of CPU, RAM, SD-slot or Wi-Fi failure. Use the following gates after the card arrives:

1. In Raspberry Pi Imager select Raspberry Pi 3 Model A+, the current Raspberry Pi OS Lite 64-bit image, and the target microSD by verified capacity.
2. Configure hostname `certarig-pi`, user credentials, Wi-Fi SSID/password, wireless country India, timezone Asia/Kolkata and SSH before writing.
3. Complete Imager's write verification. Do not skip verification.
4. Remove all GPIO, ADC, relay and USB-data connections. With Pi power removed, insert the microSD and then apply the official 5 V, 2.5 A supply.
5. Allow up to five minutes on first boot. Evidence of card access is irregular green ACT activity while the red PWR LED remains steady.
6. Try `ssh <configured-user>@certarig-pi.local`. If `.local` discovery fails, obtain the Pi IP from the router/DHCP client list and connect to that IP. A discovery failure does not prove a boot failure.
7. If network access fails but ACT activity occurred, connect a full-size HDMI monitor and USB keyboard to distinguish OS boot from Wi-Fi configuration failure.
8. If the Pi does not boot, record the repeating ACT flash sequence. Relevant documented codes include three short flashes for generic boot failure, four for missing `start*.elf`, seven for missing kernel, and two long plus one or two short flashes for a partition/read failure.
9. Re-image and complete verification; then try a second known-good microSD. A current fresh image is preferred over a card copied from an older Pi or legacy OS release.
10. If HDMI confirms boot but Wi-Fi remains unavailable, use a compatible USB Ethernet adapter or a 3.3 V USB-to-TTL serial adapter as the next diagnostic connection. UART uses Pi GPIO14/TX pin 8, GPIO15/RX pin 10 and GND pin 6; never connect 5 V serial signalling.

USB mass-storage boot is not the first fallback on a factory Pi 3 A+. It normally requires an SD boot to program the permanent USB-host OTP setting. Enabling that setting on a 3 A+ permanently prevents USB device boot, so do not program it during initial commissioning. The already-built `rpiboot` remains an optional specialist RAM-boot diagnostic with a correct 5 V-isolated USB A data cable.

Research basis:
- https://www.raspberrypi.com/documentation/computers/getting-started.html
- https://www.raspberrypi.com/documentation/computers/configuration.html#led-warning-flash-codes
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#usb-boot-modes
- https://github.com/raspberrypi/usbboot
- https://forums.raspberrypi.com/viewtopic.php?t=58151
- https://forums.raspberrypi.com/viewtopic.php?t=389623
- https://forums.raspberrypi.com/viewtopic.php?t=355061

Retain the original Phase 3 scope: dry low-voltage bench with deterministic interlocks, advisory AI and reproducible evidence. Water-loop work remains dependent on advisor scope confirmation.
