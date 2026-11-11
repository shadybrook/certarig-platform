# CertaRig Phase 3 dry-bench index

Phase 3 validates the control and evidence architecture on a low-voltage dry bench. Hydraulic commissioning, pumps, mains loads and pressure-bearing claims remain capstone work.

Visitor map for the whole submission pack: [`../phase3-submission/README.md`](../phase3-submission/README.md).

Raw CSVs, plots and photographs from the Pi: [`../../pi_retrieval_2026-09-12/phase3_evidence/`](../../pi_retrieval_2026-09-12/phase3_evidence/).

## Current verified status

- Raspberry Pi 3 Model A+ boot, SSH and I²C commissioning passed.
- ADS1115 detected at `0x48`.
- P1 on A0 and P2 on A1 acquired together at about 10 Hz.
- Fail-safe E-stop: GPIO24 LOW is healthy; HIGH/open is active.
- Relay feedback disabled; physical pin 22 / GPIO25 remains disconnected.
- Pin 17 supplies only P1 and P2. Relay lower/control COM has no external wire.
- 12 September integrated test: transistor-controlled K1 permit/safe, three cycles, E-stop forced-safe, reset-required anti-restart. Broken-wire injection was **not** performed.
- As-built drawing: fused 5 V before NC2, red inhibited lamp, green permitted lamp.

## Controlled documents

- [Wave 1 wiring guide, PDF](CertaRig_Wave_1_Wiring_and_Circuit_Guide_2026-09-07.pdf)
- [Wave 1 wiring guide, editable DOCX](CertaRig_Wave_1_Wiring_and_Circuit_Guide_2026-09-07.docx)
- [Hardware inventory register, PDF](CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.pdf)
- [Hardware inventory register, Markdown](CertaRig_Phase_3_Hardware_Inventory_Register_2026-09-06.md)
- [Wave 1 commissioning plan](CertaRig_Wave_1_Commissioning_2026-09-07.md)
- [Pi pre-wiring evidence](CertaRig_Phase3_Pi_PreWiring_Evidence_2026-09-08.md)
- [E-stop SOP](NEXT_STAGE_ESTOP_SOP.md)
- [Relay and indicator SOP](NEXT_STAGE_RELAY_OUTPUT_SOP.md)
- [Integrated bench pre-power plan](INTEGRATED_BENCH_PREPOWER_AND_TEST_PLAN_2026-09-11.md)
- [Live dashboard / shadow-run SOP](LIVE_GUARDRAIL_DASHBOARD_SOP.md)
- [Completion plan](PHASE3_COMPLETION_PLAN_2026-09-12.md)
- [Single-rail relay wiring SVG](diagrams/CertaRig_Relay_Output_Single_Rail_Wiring.svg)
- [Final as-built circuit PNG](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.png) · [SVG](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.svg) · [PDF](diagrams/CertaRig_Phase3_Final_AsBuilt_Circuit.pdf)

The relay SOP revision 1.2 supersedes the separate-supply assumptions in the 7 September wiring guide for this indicator-only bench. It must not be used for motors, pumps, valves, mains or capstone hydraulics.

## Physical evidence (Pi retrieval)

- [ADS1115 commissioning](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-09_ads1115_commissioning/README.md)
- [P1 as-built photograph](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-09_p1_potentiometer/README.md)
- [P1 functional sweep](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-09_p1_sweep/README.md)
- [Dual P1/P2 sweep](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-10_dual_pot_sweep/README.md)
- [Physical E-stop GPIO24](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-10_estop/README.md)
- [Integrated bench 11 Sep](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-11_integrated_bench/README.md)
- [Integrated relay 12 Sep](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-12_integrated_bench/README.md)
- [Observe-only shadow run](../../pi_retrieval_2026-09-12/phase3_evidence/2026-09-12_sensor_guardrail_shadow/README.md)

## Canonical physical pins

| Function | Raspberry Pi physical pin | BCM name |
| --- | ---: | --- |
| ADS VDD | 1 | 3V3 |
| ADS SDA | 3 | GPIO2 / SDA1 |
| ADS SCL | 5 | GPIO3 / SCL1 |
| ADS GND | 6 | GND |
| P2 ground | 9 | GND |
| P1 ground | 14 | GND |
| Relay command | 16 | GPIO23 |
| Potentiometer 3.3 V hub | 17 | 3V3 |
| E-stop sense | 18 | GPIO24 |
| E-stop ground | 20 | GND |
| Feedback, unused | 22 | GPIO25 |

Physical pin 16 is GPIO23 and is never a ground. GPIO and ADS inputs must never receive 5 V.

Raw credentials, Wi-Fi setup screenshots and unredacted SSH passwords are not in this repository.
