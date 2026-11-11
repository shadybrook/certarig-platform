# Original extended bench - hobby prototype revision

Current scope, confirmed by the user on11 November2026: retain the original recirculating pump/NC-valve/reservoir/permanent-bypass layout and hobby sensors. Reuse the Pi, accepted spare ADS1115, official Pi PSU, tools and suitable stock. The R3 header-tank/industrial-panel proposal is superseded and was not published or purchased.

## Budget

Target allocation: INR14,500, rounded to the original INR15,000 goal. This is a DIY parts allowance, not a supplier quote. The pressure-protection line is an unquoted INR1,500 reserve, not a verified compatible assembly. Other line allowances span INR11,750-20,300 before pressure protection; their high values should not be represented as a complete20,000 quote. Valve, isolation modules and pressure protection can move the final total.

Hobby pulse flow sensor, DS18B20 probes and INA219 modules replace industrial instruments. Use a small12V direct-acting NC zero-differential solenoid, not the expensive motorized actuator. Retain basic isolation, protected ADC input, fused low-voltage power, correctly suppressed drivers and a hardware manually reset cutoff. These circuits and reused contact ratings need a component/wiring review; no assembled safety certification is claimed. A single hobby cutoff can fail welded; it is not equivalent to the previous redundant industrial panel.

No paid panel fabrication, custom industrial S01/S02/S03 procurement, industrial safety relay, redundant contactor package, industrial spring-return actuator, SSD/UPS or paid reference calibrator is assumed. Budget is DIY assembly, excludes existing laptop/Pi and preserves the frozen university card/harness. Do not use the old5V indicator relay as an assumed motor power cutoff. Keep mains outside the wet apparatus, using enclosed supplies.

## Preserved layout and model

Reservoir -> small centrifugal pump -> pressure tee -> split: permanently open bypass to reservoir, or short metered branch -> pulse flow meter ->12V NC valve -> reservoir. Temperature probe measures reservoir water. The branch is deliberately shorter and flow-limited to reduce closure energy; no elevated header tank is introduced.

Six reduced RK4 hydraulic experiments use an upper source envelope0.30bar,0.5L/min valve branch,0.5m of12mm ID hose, assumed wave speeds200-1000m/s, and20/5/1ms effective valve closures. The stiff source is conservative for manifold pressure and does not credit bypass as a fast wave absorber. Every integration sample is retained. The5ms case at1000m/s peaks0.39137bar; half-step refinement agrees. A1ms case peaks0.90063bar and exceeds a0.5bar sensor measurement range. Therefore a fast unknown valve is not accepted merely because it is cheap. Exact pump curve, valve timing, port restrictions, compliance and sensor proof ratings remain unresolved. This does not validate the R1 high-flow/much-longer-hose arrangement or qualify a purchased bench.

Saved extrema and full horizons were checked from all six raw traces. This rebase validates only that modeled hydraulic envelope, not the hobby control hardware. R3 electrical/control simulations are not transferred as proof of this cheaper hardware. ADC input protection, power-off behavior, pump startup, hardware reset/no-auto-restart and watchdog operation still require a model based on the actual selected low-cost board circuits and then physical commissioning.

Run from the directory containing outputs/Original_Hobby_Bench using Python3 +NumPy:

    python3 outputs/Original_Hobby_Bench/hobby_rebase.py

The script writes its cost CSV, numerical results and raw traces beneath outputs/Original_Hobby_Bench. See source paths and price observations below. No parts ordered.

## Price evidence checked11 November2026

- Small12V240L/h pump: retailer Mechblock lists INR490 inclGST, currently out of stock. A price-scale anchor only, not an accepted head/startup datasheet: https://mechblock.in/p/dc-12v-240l-h-brushless-water-pump-waterproof-brushless-pump/
- Flow sensor: Tomson lists YF-S401 atINR299 incltax; flow range, bore and pulse curve vary across generic variants, so the basket uses a low-flow YF-S302-class allowance with exact variant to confirm: https://www.tomsonelectronics.com/collections/best-selling-products/products/water-flow-sensor-yf-s401
- Pressure: Robu lists PR19C-PA-050K atINR2539 and PR15C-PA-050K atINR3181: https://robu.in/product-category/pro-range-pressure-sensors/ . PR19C050K remains on hold because its PDF conflicts between50kPa label and20kPa output table. Reserve ~INR3000 for a suitable confirmed low-range wet sensor; do not buy a0-12bar sensor simply to hit a cheap price.
- Original direct-acting valve reference: https://www.fescolo.com/uploadfile/2017/0406/20170406035327750.pdf . A complete locally supplied12V zero-differential valve is not yet quoted. The INR1000 entry is a target, not a claim of an available matched item.
- Existing architecture and15k target: docs/capstone/HARDWARE_REVIEW.md in the capstone source branch, dated9 November2026.
