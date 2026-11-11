# Power-stage design review request — UNSENT

Please review a 12V educational pump/NC-valve stage with separate always-on Pi recording power and an independent upstream actuator cutoff. No component is ordered or assembly released.

Required duty and evidence:

- Two-wire brushless pump: document exact supplied TOPSFLO revision and its real startup/input-capacitance/reverse-voltage/commutation behavior. The simulation explores assumed 3A startup, 1.5A steady and 100–1000uF input capacitance; these are not manufacturer internals.
- Controlled output rise around 10ms; current limiting around 4A including actual resistor/IC tolerances; an independent fast current veto and bounded sustained-overload timeout; fault latching and deliberate reset. TI TPS25940L is a feature reference, not a qualified selection from this model.
- Supply source/wiring/contact/shunt impedance and supply foldback must support measured startup and the valve sequence. Initial tests assume an already settled input rail; adapter hot-plug must be checked separately.
- The valve is enabled after startup and shed during pump overcurrent. Retain an independently effective return/pressure-protection path; do not rely on software sequencing for pressure safety.
- Pump measurement uses a 50milliohm shunt sized for current, heat and pulse energy, with Kelvin wiring and recalibration; the original R100 board is not unchanged. The valve can retain its separately appropriate measurement range. ADC/sampling is not the fast cutoff.
- One-direction MOSFET/driver stage, properly enhanced gate voltage, undervoltage veto, suppression and layout. Thermal analogy uses Vishay IRL540 0.077ohm at 5V gate, a 2x hot factor and effective mounted thermal resistance <=20C/W. Confirm actual device provenance, thermal path and linear/switching SOA.
- Check the complete pass-element voltage/current/time waveform: modeled short energy is about 0.42J before latching and normal startup is about 0.16J. Device energy/SOA and transient thermal behavior are NOT accepted just because the generic model limits current. Change device, timing or fault-energy containment if necessary.
- Switched output discharge equivalent: 47ohm, up to 1000uF and 13.2V. Select an actual discharge transistor and resistor with adequate pulse/thermal ratings; review backfeed and shutdown paths. Discharge is required after a trip and ordinary disable.
- Verify independent cutoff when a switching device fails short, relay-contact ratings, E-stop release/held-reset behavior, fuses, wire heating, measured per-load voltage/current and continuity of local recording.

Return a construction-level schematic, pin/terminal/wire schedule, exact assembled BOM and datasheets, thermal/SOA analysis, quote and required physical acceptance measurements. No supplier message has been sent.
