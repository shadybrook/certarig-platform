---
name: adc_validation
domain: electronics
procedure: procedure.yaml
intents:
  - validate the adc
  - sweep the sensors
  - check the potentiometer channels
  - calibrate pressure and flow emulators
---

# ADC channel validation sweep

Confirms the ADS1115 channels behave: good quality at rest, full-range response when the
operator sweeps each emulator, and a clean return to a mid value. The output is never armed;
`evaluate` asserts that `permit_accepted` was not observed.

Six operator moves, each confirmed by a measured trigger. If a trigger times out, the most likely
causes are a wrong potentiometer wired to that ADC input (swap suspected), a broken wiper, or
scaling that cannot reach the endpoint. Compare peaks in the run record with the channel's
`engineering_max` before touching hardware.

The whole-run CSV is the calibration artefact: keep it with the calibration id recorded in
the rig config.
