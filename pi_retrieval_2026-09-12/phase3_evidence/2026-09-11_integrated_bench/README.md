# CertaRig integrated bench evidence - 11 September 2026

Current result: **GATE 1 PASS - Pi, network, I2C, ADS1115, GPIO24 E-stop sensing and forced-safe GPIO23 state verified**

Corrected Gate 1 attempt G1-A03 on 11 September 2026 resolved a software interpretation defect. `gpiozero.DigitalInputDevice.value` is an active/inactive logical value and is inverted when `pull_up=True`; it is not the raw electrical GPIO level. Direct `pinctrl get 24` verification showed GPIO24 electrically LOW with the E-stop released. The adapter and both Phase 3 loggers were corrected to read `DigitalInputDevice.pin.state`, and a regression test was added. The complete project check then passed with 6 JavaScript tests and 20 Python tests, followed by the dashboard build and four Phase 2 evidence bundles.

The fixed released-state capture recorded 98 of 98 samples as GPIO24 LOW, `estop_active=false`, and GPIO23 LOW. The corrected transition capture recorded 754 samples over 75.3 seconds and exactly six GPIO24 transitions across three operator cycles. Each latch changed LOW to HIGH and produced `estop_open_forced_safe`; each release changed HIGH to LOW and produced `estop_closed_reset_required`. GPIO23 remained LOW for every sample, and the final released state was LOW/healthy. This passes the E-stop sensing and fail-safe output conditions for Gate 1. Evidence: `gate1_estop_fixed_released.csv` and `gate1_estop_transition_corrected.csv`.

Recovery Gate 1 attempt G1-A02 on 11 September 2026: the microSD was freshly reimaged with Raspberry Pi OS Lite 64-bit, the Pi booted from PWR IN with the 1 A fuse removed, K1 contact COM disconnected, relay CH1 disconnected, and both potentiometers at zero/off. The Pi retained its private LAN address, responded to five of five ICMP requests after a clean reboot, and accepted an authenticated SSH session. The baseline reported Debian 13 (trixie), kernel `6.18.34+rpt-rpi-v8`, 117 GB root storage, `throttled=0x0`, and a temperature of 41.9 C after reboot. I2C buses 1 and 2 were present and the ADS1115 was the only detected device on bus 1 at `0x48`.

The repository was restored from GitHub at commit `a06d4d20711a01c2ad76ae10a72a097ca2b2729c`. Its complete Pi-side check passed: 6 JavaScript tests, 19 Python tests, static dashboard build, and four Phase 2 evidence bundles. A monitor-only integrated logger then captured 188 samples over 18.7 seconds in `gate1_reimage_monitor.csv`. A0 and A1 remained at 0.000000 V and GPIO23 remained LOW for every sample. GPIO24 remained HIGH for every sample, which the frozen fail-safe configuration correctly interpreted as E-stop active/open; the trip latch remained true and no permit was requested. The Pi was shut down cleanly over SSH after the capture.

The G1-A02 CSV is retained as a superseded diagnostic artifact. Its GPIO24 column was mislabeled because the logger recorded gpiozero's active-low logical value as if it were the raw electrical level. It does not prove a wiring-state mismatch. G1-A03 is the authoritative Gate 1 E-stop record.

Operator update on 11 September 2026: `K1 NO` was reported connected to breadboard `F14`. This resolved the previously missing connection in the reported topology. Acceptance remained on HOLD at that time pending the U21-U23 meter checks; the hold was later cleared by the successful 12 September integrated test.

First reported meter batch at 16:35 IST: K1 COM-NO was `OL`; K1 NO-F14 was reported as `0.4`; K1 COM-NC was reported as `12 ohm`; the two resistor-path readings were reported as `0.9` and `0.4` without displayed units; and the FUSED_5V-to-ground result could not be determined. The latter results are failed or inconclusive, so no power authorization was issued. Both potentiometers are to remain at their zero/off positions through Gate 1.

Second reported meter batch at 16:51 IST: the green and red series branches measured `0.978 kohm` and `0.98 kohm`, respectively, and now pass. FUSED_5V-to-ground produced no reading and is provisionally treated as open pending confirmation of meter mode and no sustained beep. K1 COM-NC measured `20 ohm`, which still fails unless the shorted-probe baseline explains it. The reported dead-rail voltage text was ambiguous and was not accepted. Power remains prohibited.

At 16:58 IST, the operator confirmed that the meter reads `0.02 kohm` both with its probes shorted and across unpowered K1 COM-NC. K1 therefore adds no measurable resistance on that range and U19 is accepted as a baseline-corrected pass. This removes the suspected K1 contact fault; the remaining Gate 0 continuity, no-short, identity, and dead-voltage checks still control power authorization.

First Gate 1 attempt on 11 September 2026: the 1 A branch fuse was removed, both potentiometers were at zero/off, and the E-stop was reset before PWR IN was applied. The Pi answered one ICMP echo at its private LAN address; mDNS did not resolve; SSH reached authentication but no authenticated session was opened. The operator then reported that the red PWR LED was not visible while the green ACT LED flashed irregularly. The test was immediately aborted, the pending SSH session was closed, and the operator disconnected PWR IN. Raspberry Pi documentation identifies an off or flickering red PWR LED on Pi 1-4 boards as an undervoltage indication. No relay-output test occurred.

Post-abort no-short checks at 17:48 IST found no continuity beep from the Pi-side fuse-holder input to ground, but the pin-17 shared 3.3 V hub measured a confirmed `9 ohm` with a sustained beep and no `k` symbol. This was a Gate 0 failure and a plausible cause of the observed undervoltage. A subsequent operator-performed isolation sequence reproduced the fault only when the physical-pin-17 branch was added to the relay lower/control COM terminal. Pi-only, pin25-to-A6, and pin16-to-A2 configurations retained a stable red PWR indication; adding pin17-to-lower-COM extinguished it; removing only that branch restored it. The earlier potentiometer-wiper hypothesis is therefore superseded by stronger isolation evidence, although S06 must still be repeated before power.

The corrected wiring keeps physical pin 17 dedicated to P1 and P2. Relay lower/control COM is externally disconnected with S1 on COM-LOW. The control path is DC+ through NC2, DC- to common ground, CH1 to the BC547 collector, and CH2 unused. The module-specific low-trigger behaviour was later characterized and passed in the 12 September integrated output test.

The isolation observations are operator-reported and preserved in `relay_com_isolation_diagnostic.csv`. They establish the wiring correction but do not by themselves authorize power. Required next evidence is an unpowered S06 repeat near the expected parallel-pot resistance, S08 open-circuit confirmation, and then the staged Gate 1 retry.

## Scope

This folder retains the as-built photo set and will receive the unpowered meter register, SSH transcripts, integrated CSV, plots, truth tables, and test-case result after the controlled commissioning gates pass.

The superseded recovery monitor CSV SHA-256 is `140eca6680c7bd2958a92c7772fe28008f63370789dcb67e34838599385efa5a`. The fixed released-state CSV SHA-256 is `27be36f98d63a5c2a98972801868b82a229a1aab5bdc869dff3d3daf8d5c6d8a`; the corrected transition CSV SHA-256 is `0433825ca11f38127031db715c591cd4f56f88365813a9f19c282ea542d0b871`.

The photographs show physical assembly but do not prove continuity, polarity, terminal identity, or safe energization. The inspection and test plan is [`docs/phase3/INTEGRATED_BENCH_PREPOWER_AND_TEST_PLAN_2026-09-11.md`](../../docs/phase3/INTEGRATED_BENCH_PREPOWER_AND_TEST_PLAN_2026-09-11.md).

## Source-photo mapping

| Evidence copy | User-supplied source | Source SHA-256 | Evidence-copy SHA-256 |
|---|---|---|---|
| `pre_power_photos/01_overall_bench.jpg` | `IMG_1909.HEIC` | `8f91cc7cf69aa6954ea8376d36fbc8abc9debc354e7c1d5b43b4e9e481bd693b` | `31643bf4fab38949f5caed85974d9e84b5b2e11afafb75a240f4e5718125b50f` |
| `pre_power_photos/02_relay_breadboard_pi_overview.jpg` | `IMG_1896.HEIC` | `a232c6869a91c16a351ae54a9f0a9c84d7a21ac332312399f3a655e1b0aeb041` | `202798090ab83bbab5e0bcdf1a0d135dd0bd5a00539772d41de3b50264888b0c` |
| `pre_power_photos/03_pi_ads1115_potentiometers.jpg` | `IMG_1900.HEIC` | `3597daf0a08f0189f3749a96a44085ad487ef5df1d65440dbf6fb3d4eab4bc43` | `0fbad297888e540b7703dc7d4595e92d7b51a122475ff62edcd1d75e46e2102d` |
| `pre_power_photos/04_estop_fuse_breadboard.jpg` | `IMG_1901.HEIC` | `5d533f7702bf8d9d21d6706454674156112726d204642e3b19d189135c509fb7` | `a021a50f5f8c9986a57c2b15f0a192a2fd8329dafb27237acacd6b6da712131f` |
| `pre_power_photos/05_relay_and_breadboard_closeup.jpg` | `IMG_1903.HEIC` | `b4eae33424af269a07d67324a7fe94fea673f115ef1b989f29dacbda48273741` | `84d66f6d1cd03a5f24ea187231b7b59a57f2455b82296d0a0e3eebd0d71f60f6` |

## Review finding

Only two wires are clearly visible on one three-screw relay contact group. The inhibited/permitted changeover requires measured K1 COM, NC, and NO connections. This and every other Gate 0 reading must be resolved before the circuit is powered.

The inhibited indicator is red in this build. Earlier references to yellow describe the same safe/inhibited function and were updated in the controlled relay SOP and diagram.
