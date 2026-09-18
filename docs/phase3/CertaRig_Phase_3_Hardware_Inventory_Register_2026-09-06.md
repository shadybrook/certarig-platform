# CertaRig Phase 3 Hardware Inventory Register

Baseline: 06 September 2026  
Deadline: 20 September 2026  
Source: Robu invoice INV2627/225826 dated 04 September 2026

> Receipt, electrical acceptance and integrated verification are separate statuses. This editable companion is the working register; generate a new dated PDF revision after material updates.

## Status snapshot

- 17 of 17 Robu physical product lines are visually mapped to photographs.
- 0 of 17 items have recorded electrical acceptance tests in this baseline.
- The separate regulated 5 V, 1-2 A relay and indicator supply is not evidenced and is the only Wave 1 output-test procurement gate.
- Three Amazon listings remain pending; none blocks Pi provisioning or passive testing.
- Wave 2 water-loop hardware is deferred until advisor scope is frozen on 07 September.

## Robu inventory

| ID | Robu code | Item | Qty | Role | Photo | Wave | Receipt status | Electrical acceptance | Evidence file |
|---|---|---|---:|---|---|---|---|---|---|
| R01 | 1364532 | Green 3-9 V, 6 mm metal indicator with 15 cm cable | 1 | Healthy / permitted-state indicator | IMG_1837 | Wave 1 | Received - visual match | NOT TESTED - Polarity and current test | |
| R02 | 1364728 | Yellow 3-9 V, 8 mm metal indicator with 15 cm cable | 1 | Warning / inhibited-state indicator | IMG_1837 | Wave 1 | Received - visual match | NOT TESTED - Polarity and current test | |
| R03 | 24438 | MB102 830-point solderless breadboard | 1 | Low-voltage prototype interconnect | IMG_1850 | Wave 1 | Received - visual match | NOT TESTED - Rail continuity and split-rail map | |
| R04 | R185776 | Rubycon 100 uF, 50 V radial electrolytic capacitor | 1 | Local low-voltage bulk decoupling | IMG_1841 | Wave 1 support | Received - visual match | NOT TESTED - Capacitance / condition; observe polarity | |
| R05 | 1897057 | BF-013A 5 x 20 mm fuse holder | 1 | Fused low-voltage actuator branch | IMG_1839 | Wave 1 | Received - visual match | NOT TESTED - Continuity and mechanical retention | |
| R06 | R257326 | 24 AWG silicone wire - red | 1 | Labelled positive low-voltage wiring | IMG_1842 | Wave 1 | Received - visual match | NOT TESTED - Inspect insulation; label both ends | |
| R07 | 1825005 | 24 AWG flexible silicone wire - green | 2 | Labelled signal / interconnect wiring | IMG_1842 | Wave 1 | Received - visual match | NOT TESTED - Inspect insulation; do not rely on colour alone | |
| R08 | R165252 | LANBOO LB16SM 16 mm latching emergency-stop switch, stated 2C-2NC | 1 | Two independent low-voltage inhibit / sense loops | IMG_1846 | Wave 1 | Received - visual match | NOT TESTED - Map both NC contact pairs with multimeter | |
| R09 | R195523 | ALPS RK09K1130A5R 10 kohm rotary potentiometer | 3 | Breadboard calibration controls and spares | IMG_1838 | Wave 1 support | Received - visual match | NOT TESTED - End-to-end resistance and smooth wiper sweep | |
| R10 | R122767 | Littelfuse 0217001.MXP, fast-acting 1 A, 250 V, 5 x 20 mm | 5 | Low-voltage branch protection | IMG_1845 | Wave 1 | Received - visual match | NOT TESTED - Continuity; confirm fit in holder | |
| R11 | 662929 | 100 nF, 50 V through-hole disc capacitor | 8 | Local logic / ADC decoupling | IMG_1840 | Wave 1 support | Received - visual match | NOT TESTED - Visual condition; install close to load | |
| R12 | R181433 | Murata 22 pF, 50 V, 0402 C0G SMD capacitor | 6 | Parts stock; not required for the Phase 3 bench | IMG_1844 | Deferred | Received - visual match | NOT TESTED - No bench test required | |
| R13 | 43582 | ADS1115 16-bit, 4-channel I2C ADC module | 2 | Two analogue sensor-emulation channels; one spare module | IMG_1836 | Wave 1 | Received - headers loose | NOT TESTED - Solder header, 3.3 V power, I2C scan, stable readings | |
| R14 | R260139 | 2-channel 5 V relay module with optocouplers and guide rail | 1 | Low-voltage output switching for indicators only | IMG_1849 | Wave 1 | Received - visual match | NOT TESTED - Document pins; test coils from separate 5 V supply | |
| R15 | 1163662 | TE 23ESA103MMF50AF 10 kohm panel potentiometer | 3 | Panel controls: pressure, flow and spare / fault injection | IMG_1835 | Wave 1 | Received - exact code visible | NOT TESTED - End-to-end resistance, wiper sweep, terminal map | |
| R16 | 169868 | Raspberry Pi 3 Model A+ | 1 | Edge computer, deterministic interlocks, logs and API | IMG_1847, IMG_1848 | Wave 1 | Received - board and model confirmed | NOT TESTED - Boot, power stability, Wi-Fi, SSH, GPIO and I2C | |
| R17 | R224115 | BC547-TA NPN transistor | 3 | Protected relay-input interface / spares | IMG_1843 | Wave 1 support | Received - exact code visible | NOT TESTED - Identify E-B-C pinout; diode-test junctions | |

## Photo mapping

| Photo | Inventory ID | Identification | Evidence basis |
|---|---|---|---|
| IMG_1835 | R15 | Three TE 23ESA panel potentiometers | Exact Robu code 1163662 is visible on all three bags. |
| IMG_1836 | R13 | Two ADS1115 ADC modules | Exact Robu code 43582 is visible. Loose header strips are present and must be soldered. |
| IMG_1837 | R01, R02 | Green and yellow metal indicators | Exact Robu codes 1364532 and 1364728 are visible. |
| IMG_1838 | R09 | Three ALPS RK09 10 kohm potentiometers | Exact Robu code R195523 and quantity 3 are visible. |
| IMG_1839 | R05 | BF-013A fuse holder | Exact Robu code 1897057 is visible. |
| IMG_1840 | R11 | Eight 100 nF disc capacitors | Exact Robu code 662929 and quantity 8 are visible. |
| IMG_1841 | R04 | Rubycon 100 uF radial electrolytic capacitor | Exact Robu code R185776 and quantity 1 are visible. |
| IMG_1842 | R06, R07 | Red and green 24 AWG silicone wire | Exact Robu codes R257326 and 1825005 are visible. |
| IMG_1843 | R17 | Three BC547-TA NPN transistors | Exact Robu code R224115 and quantity 3 are visible. |
| IMG_1844 | R12 | Six complimentary 22 pF 0402 SMD capacitors | Exact Robu code R181433 and quantity 6 are visible. |
| IMG_1845 | R10 | Five Littelfuse 1 A fast-acting fuses | Exact Robu code R122767 and quantity 5 are visible. |
| IMG_1846 | R08 | LANBOO latching emergency-stop switch | Exact Robu code R165252 is visible; electrical contact arrangement remains to be measured. |
| IMG_1847 | R16 | Raspberry Pi 3 Model A+ retail box | Model identity is clearly visible. |
| IMG_1848 | R16 | Raspberry Pi 3 Model A+ board | Board marking and Robu code 169868 are visible. |
| IMG_1849 | R14 | Two-channel 5 V optocoupled relay module | Exact Robu code R260139 is visible. |
| IMG_1850 | R03 | MB102 solderless breadboard | Product format and MB-102 marking are visible. |

## Existing support inventory

| Item | Status |
|---|---|
| 32 GB Class 10 A1/A2 microSD card | Available |
| USB microSD card reader | Available |
| Official 5 V, 2.5 A micro-USB Raspberry Pi supply | Available |
| Male-male, male-female and female-female Dupont jumpers | Available |
| MB102 power module or suitable supply breakout | Available |
| Additional black and blue/yellow 24 AWG wire | Available |
| 2N2222 transistors | Available; BC547 units also received |
| 2.54 mm male header strip | Available; ADS1115 headers also pictured loose |
| Screw terminals or lever connectors | Available |
| Heat-shrink tubing, cable ties and labels | Available |
| Rigid non-conductive mounting plate or ABS enclosure | Available |
| Digital multimeter | Available |
| Wire tools, screwdrivers and soldering equipment | Available |
| Separate regulated 5 V, 1-2 A supply for relay and indicators | NOT EVIDENCED - confirm or obtain before output test |

## Amazon pending

| Item | Status | Decision |
|---|---|---|
| ELEGOO 17-value 1% resistor assortment | Pending Amazon | Useful for 1 kohm base resistors, 10 kohm pull-downs and indicator current limiting. Does not block Pi-only setup. |
| 10 uF, 16 V electrolytic capacitors, pack of 8 | Pending Amazon | Optional local bulk decoupling; the received 100 uF capacitor is sufficient for initial low-voltage bench checks. |
| 1000 uF, 25 V electrolytic capacitors, pack of 10 | Pending Amazon | Not required for Wave 1. Hold for later supply-transient experiments or Wave 2. |

## Immediate commissioning sequence

1. Quarantine outputs and label all components.
2. Perform passive continuity, resistance and transistor junction checks.
3. Provision the Raspberry Pi on its official supply and record boot, Wi-Fi, SSH and stability evidence.
4. Solder the ADS1115 headers, power one module at 3.3 V and verify its I2C address.
5. Integrate one potentiometer, then two; record raw ranges and three-point calibration.
6. Fix and test E-stop polarity, raw-range, stale-data and feedback guards in software before outputs.
7. Obtain or confirm the separate regulated 5 V supply, then test the fused relay branch with low-voltage indicators only.
8. Run the named fault tests and 60-minute soak; capture photos, CSV logs, screenshots and commit ID.

## Schedule

| Date | Milestone | Deliverable |
|---|---|---|
| 6 Sep | Receive and control | Freeze inventory, quarantine untested parts, inspect Pi and relay, identify pin labels, prepare microSD. |
| 7 Sep | Professor scope freeze | Confirm whether a hardware-in-loop dry bench is sufficient for Phase 3, and whether the water loop is explicitly required. |
| 8-9 Sep | Component acceptance | Continuity tests, potentiometer sweeps, transistor diode tests, solder ADS1115 headers, Pi boot and I2C detection. |
| 10 Sep | Software safety gate | Correct E-stop and feedback polarity configuration, add stale-sample and raw-range faults, and pass automated tests before outputs. |
| 11-12 Sep | Input integration | Wire two panel potentiometers to ADS1115 at 3.3 V, collect raw data, perform 3-point calibration and log evidence. |
| 13-14 Sep | Output and safety integration | Use a separate regulated 5 V supply, transistor interface and 1 A fused branch. Drive only low-voltage indicators. |
| 15 Sep | Integrated tests | Run normal, threshold, E-stop, broken-wire, stale-data, relay-feedback and restart tests; then perform a 60-minute soak. |
| 16 Sep | Evidence capture | Photograph wiring, export CSV logs, screenshots and test results; record exact software commit and configuration. |
| 17-18 Sep | Phase 3 report | Populate the template only with achieved evidence, limitations and measured results; advisor review on 18 Sep. |
| 19 Sep | Submission rehearsal | Fresh clone, clean installation, signed-out link check, PDF review and buffer for corrections. |
| 20 Sep | Submit | Submit the verified report, repository tag, evidence package and video/link set requested by the professor. |

## Change log

| Revision | Date | Change | Evidence / approver |
|---|---|---|---|
| 1.0 | 06 Sep 2026 | Initial inventory, photo mapping and commissioning baseline | Robu invoice and IMG_1835 to IMG_1850 |
| 1.1 | | | |

## Safety boundary

This is a low-voltage educational proof of concept. Do not connect the relay contacts to mains or a high-current load. Do not treat the emergency-stop switch as certified safety equipment. The AI layer is advisory; deterministic edge interlocks retain authority.
