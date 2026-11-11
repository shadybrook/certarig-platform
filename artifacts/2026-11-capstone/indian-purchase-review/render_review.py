import argparse
import html
import json
from pathlib import Path

parser = argparse.ArgumentParser(description="Render CertaRig procurement data and saved experiment results")
parser.add_argument("root", type=Path)
root = parser.parse_args().root.resolve()
b = json.loads((root / "basket.json").read_text())
s = json.loads((root / "summary.json").read_text())
e = html.escape


def money(n):
    return f"₹{n:,.2f}"


positive = sum(x["expected"] == "within_envelope" for x in s["results"])
negative = len(s["results"]) - positive
assumptions = """The integrated circuit extends the earlier R1 behavioral cutoff/watchdog/reset network. It is NOT the DRV8871 module schematic. It uses generic 100V switch/diode models, a bounded BLDC input load, a 14.4ohm valve (inferred from Uflow-family 12V/10W), and assumed valve inductance 0.2H/0.5H. Exact valve, driver, watchdog, gate-drive and clamp assembly remain unselected. The valve suppression model uses a 28.5V avalanche knee plus diode, not a measured SMBJ18A curve. Nominal integrated pump input assumes 1uF and no excess startup demand; the deliberate failed-start comparison assumes 100uF and 3A. Neither is published TOPSFLO internal data. The -1V pump reverse criterion is an engineering assumption, not a manufacturer tolerance. No mechanical closure time, hydraulic transient, valve position, safety integrity level or selected physical assembly is qualified."""
nextsteps = [
    "Keep the pump, valve, pressure protection and actuator-stage orders on hold. The research does not support a complete matched purchase order at ₹15,000.",
    "Resolve the exact pump revision/inrush, a water-rated 12V NC zero-differential valve with coil/flow data, and an independently effective pressure-protection design. Use the unsent supplier questions in this pack; no vendor was contacted.",
    "Freeze a pin/terminal schematic and exact driver, fast protection, latch/watchdog/reset, feedback and power-sequencing parts. Apply the revised component values and repeat the complete matched model with those values.",
    "Obtain local quotes for 5m hose, all seal/port adapters, assembly, reference instruments, compliant supplies and shipping to 400053. Present the revised total before choosing a purchase order.",
    "The separate development microSD is independent of the water-loop design. The listed model can be compared with a local authorized seller; preserve the Phase 3 card.",
    "After procurement release and parts inspection, perform dry electrical checks, passive leak checks, read-only sensing, calibration, protected actuator trials and integrated attended tests in that order. Simulation does not replace those steps.",
]
md = f"""# CertaRig: Indian purchase and simulation review

Checked 9–10 November 2026 • delivery PIN 400053 • candidate basket, no purchase made.

**Purchase status: HOLD.** {len(b["items"])} product options researched across Indian retailers/manufacturers and Indian-facing import distributors. {len([x for x in b["items"] if x["kind"] == "candidate"])} primary candidate lines cover the major parts; {len(b["allowances"])} further cost groups still need exact part/quantity quotes. This is a review pack, not a purchase-ready matched assembly.

**Budget:** primary candidate planning subtotal {money(b["primary_subtotal_INR"])}; assembly/fittings/freight reserves {money(b["allowance_reserve_INR"])}; planning total **{money(b["planning_total_INR"])}**, plus unbounded import duty/clearance and any quote increases. The agreed ceiling is ₹15,000. Do not buy the full basket.

The 30m hose roll is counted because a 5m offcut sale is unconfirmed. Imported part lines carry an assumed 18% tax reserve, not a customs assessment. No unquoted line has been presented as a confirmed delivered price. SEN0262 is a comparison option and is excluded from the primary subtotal.

## Confirmed PIN checks

- Robu TOPSFLO pump: live page showed In Stock, ₹2,929 including GST; 400053 resolved to Mumbai, with estimated 13 November by air or 16 November by standard courier. These are estimates, not guaranteed delivery dates.
- Evelta SEN0262: live page showed 25 units, ₹546.34 including GST and expected delivery 12 November for 400053. Holiday notice warns of up to 72h dispatch delay. This module is not released as a complete protected ADC interface.
- Industrybuying Techno valve: 400053 returned prepaid/COD availability and a general five-day dispatch lead, without an observed dated arrival. It is not accepted for water because the exact listing specifies compressed air.
- Other rows distinguish published stock, orderable variants, global stock, lead times and unconfirmed stock. A .in domain does not imply Indian warehouse inventory.

## Candidate basket

| Role | Qty | Exact candidate | Seller | Planning line | Availability |
|---|---:|---|---|---:|---|
"""
for x in b["items"]:
    if x["kind"] == "candidate":
        md += f"| {x['role']} | {x['quantity']} | [{x['model']}]({x['url']}) | {x['supplier']} | {money(x['planning_line_INR'])} | {x['stock']} |\n"
md += "\n## Unquoted requirements and reserves\n\n"
for x in b["allowances"]:
    md += f"- **{x['role']} — {money(x['reserve_INR'])} reserve:** {x['quantity']}. {x['requirements']}.\n"
md += """
## What the new simulations establish

"""
md += f"""ngspice 47 ran **{len(s["results"])} new electrical experiments**: {positive} met their stated envelope criteria and {negative} deliberately unsuitable/fault cases were rejected. All transients completed and contain {sum(r["samples"] for r in s["results"]):,} finite saved samples. There are also **{len(s["analytical_checks"])} separate deterministic calculations**; those are not SPICE transients or measured hydraulic results. The earlier 54-case R1 evidence remains unchanged.

- A bounded 100ohm protected receiver reaches 4–20mA across 21.6–26.4V and passes modeled Pi-off cases. The modeled 10kohm series / 33kohm discharge network also attenuates the ADC signal by about 23%; scaling must use the full circuit and end-to-end calibration, not simply divide pin voltage by 100ohm. This relies on an ideal power-good/isolation timing assumption and an unselected reference/clamp realization; it is not a completed receiver PCB qualification.
- The 120ohm receiver burden is normal at 20mA (2.4V), but a 33mA fault gives 3.96V before loading. The deliberately unbuffered test is a burden/ADC hazard demonstration, **not a TP5551/SEN0262 full-board fault simulation**. Its actual protection behavior remains unqualified.
- Nishka's conservative 11V transmitter minimum makes a 12V loop supply inadequate at full-scale after burden/protector drops. A 24V instrument supply is retained.
- The listed INA219 module uses 0.1ohm: 4A produces 400mV, beyond its 320mV shunt range. 2.5A produces 250mV and is measurable, but startup compatibility and an independent fast cutoff remain unresolved. A saturated or unknown reading must not become safe by default.
- A DRV8871 conduction/thermal analogy rejects the retailer's 3.6A continuous claim. At 1.5A the nominal TI-test-PCB analogy is below the conservative 125C design limit; an assumed hot/poor-cooling bound fails. The unconstrained model's high temperatures indicate thermal incompatibility, not a prediction that a real chip reaches that temperature: TI specifies automatic shutdown/recovery, which this thermal analogy omits. Actual dual-board coupling/cooling and pump compatibility are unqualified.
- The revised integrated **behavioral** model passes nominal execution, E-stop, held-reset anti-restart, heartbeat loss and selected inductance/time-step comparisons. With an assumed 3A/100uF pump startup, the cutoff trips before a useful run. This is an unresolved procurement issue; nominal success does not establish real pump startup.
- Pump 5–6m shutoff head corresponds to about 0.49–0.59bar under static water assumptions. A 0–0.2bar transmitter would overrange without protection. A 0–1bar span avoids that static overrange but its conservative ±0.005bar error is already ±5% of a 0.1bar reading before other errors.
- The pipe calculation uses an explicitly assumed straight-line curve between uncertain pump endpoints, tube friction and K=6. It does not represent a selected valve, flow sensor pressure drop or accepted bypass. Water hammer, relief capacity, pump inlet flooding/cavitation, fittings and leaks remain unvalidated. No physical pressure setpoint is frozen.

{assumptions}

## Replacement choices

"""
for x in b["items"]:
    if x["kind"] != "candidate":
        md += f"- **{x['role']}: [{x['model']}]({x['url']}) — {money(x['unit_price_INR'])}, {x['kind']}.** {x['stock']}. {x['description']} {x['holds']}\n"
md += f"""
## Concrete budget revision

Using the provisional Robu Pro-Range supply instead of Mean Well saves ₹1,664. Obtaining 5m of the same hose instead of a 30m roll saves a conservatively taxed ₹1,770. Together those changes would reduce this planning estimate to **{money(b["revised_option"]["revised_planning_total_before_other_changes_INR"])}**, still above ₹15,000 and still subject to exact SKU/stock/quote review. This is not an approved substitution basket.

Retain all protection, feedback and calibration requirements. A staged purchase can fund the separate development card and later dry feedback electronics, but it does not constitute a complete fluid loop within budget. A smaller matched loop or institution-supplied reference equipment would require an explicit revised design and fresh evidence. No hardware budget increase is assumed.

## Exact next steps

"""
for i, x in enumerate(nextsteps, 1):
    md += f"{i}. {x}\n"
md += """
## Evidence and reproduction

Open `index.html` directly in a browser; no installation, login, external scripts or internet are needed for the review itself. Supplier links require internet. `basket.json` is editable structured procurement data. `summary.json` contains each experiment, criterion, measurement and assumption. `cases/` contains netlists, logs, per-case decisions and gzipped samples. `sources.json` records engineering parameter provenance. `SHA256SUMS` hashes the pack; consistency hashes do not establish third-party authenticity.

```sh
python3 run_review.py verify .
# To rerun with ngspice installed, choose a NEW evidence folder:
python3 run_review.py run /absolute/path/to/new-evidence
```

The script uses only the Python standard library and ngspice; bundled `run_spice.py` supplies the earlier behavioral control generator. Offline replay requires no ngspice or model API. Failure/corruption checks are recorded in `verification_checks.json`. No paid model calls or connections to physical equipment occur.

GBrain tools were unavailable, so the review uses local source/evidence and current public supplier pages. Restarting Codex may load the registered GBrain server. No university or website instructions were treated as authorization to purchase.
"""
(root / "README.md").write_text(md)
questions = """# Supplier/design questions — UNSENT

No vendor messages, accounts, carts or orders were created. These are reviewable request drafts for a later explicitly authorized enquiry.

## TOPSFLO / Robu — TL-B10-B12-0905, R256922

Please confirm current Indian stock and total delivered to PIN 400053; whether the supplied pump is 9 L/min/5m/16.6W or 9.5 L/min/6m/18W; actual B-housing G1/2 thread standard and seals; a matching revision pump curve; startup/stall/blocked-rotor current and protection; allowed supply tolerance, on/off switching, PWM and reverse/transient input ratings; flooded-suction/minimum inlet requirements and permitted continuous duty. We need exact supplied-unit documentation, not another A/C variant's sheet.

## Uflow / seller — small-port normally closed valve

Please quote ONE water-compatible direct-acting NC valve, 12VDC continuous duty, verified operation at zero pressure differential, approximately G1/4 ports and 0.3–3 L/min target branch flow. Confirm the complete part/coil/connector/seal code; the DAS-DA220E015 title/port ambiguity; water service and mounting, Kv/Cv, minimum/maximum pressure, coil power/resistance/inductance/tolerance and closing-time range; suppression requirements; stock, return rules and tax/freight to 400053. A compressed-air-only or minimum-0.2bar pilot valve is unsuitable.

## Nishka — pressure transmitter

Please quote ONE 0–1bar GAUGE, two-wire 4–20mA water transmitter with G1/4 BSP connection, complete connector/pinout and calibration evidence. Resolve 10–28V vs 11–30V supply and 0.5%FS vs 0.5%reading accuracy claims. Confirm wetted materials, sealing/overpressure/burst ratings, resolution/response, exact order code, stock and delivered cost. A lower range is acceptable only after the independent pressure protection is designed.

## Pressure protection / hydraulic reviewer

We need an independently effective return/protection path for a low-head water loop, including a worst-case 6m pump shutoff envelope. Please provide a matched device with known water capacity/pressure curve, adjustable low setpoint and tolerance, installation/back-pressure constraints and ports. RS PRO 275-5960 is documented as a differential bypass; is it suitable for this exact duty and available? Do not describe it as a certified safety relief valve without proof. Freeze operating limit, software trip, mechanical protection and weakest-component conditions together.

## Electrical assembly / suppliers

Please identify exact stock/price and schematics for the driver, protected 4–20mA receiver, independent watchdog/manual-reset anti-restart latch, power-good veto, fast current protection and separate measured load-voltage feedback. Verify MAX14626 exposed-pad and TMUX1511 package assembly; no TS5A3166 substitution on old powered-off claims. For MD-10116 confirm RILIM and thermal layout, continuous thermal limits and allowed BLDC on/off use. Quote PCB/assembly/enclosure, DC-rated fuses/holders and cables. Retain Pi power during actuator cutoff. Provide compliant enclosed adapters, polarity, connectors and pump-start current-limit behavior.

## Local references and plumbing

Quote 5m Phoenix PHWB12 offcut or a traceable equivalent with water working-pressure/temperature/vacuum information, all exact BSPP/BSPT seal-face transitions, 22mm bypass adapters if retained, clamps and containment. Confirm actual hose minimum order. Quote a 1L Class B cylinder with stated tolerance, a non-mercury thermometer with known uncertainty, and an appropriate pressure reference/column fixture. If the institution can lend calibrated references, record the actual loan before removing purchase costs.
"""
(root / "SUPPLIER_QUESTIONS_UNSENT.md").write_text(questions)
# Primary technical provenance; local PDF files stay in task scratch, not redistributed in pack.
sources = [
    (
        "pump",
        "https://robu-prod-media.s3.ap-south-1.amazonaws.com/products/attachments/OUBdxYrTqNAGFqLSPFl2NML0rXL4TCD8CWIFkZ2J.pdf",
        "12V 1.38A 5m 9L/min; actual attached sheet conflicts with product listing; do not merge variants",
    ),
    (
        "pump manufacturer",
        "https://www.topsflo.com/brushless-dc-pump/brushless-dc-pump.html",
        "B/C12-0905 family endpoints; no startup/current-controller model",
    ),
    (
        "pressure",
        "https://nishkainstruments.com/product/pressure-transmitter/",
        "0-1bar selected in live UI; 11-28V intersection and 0.5%FS conservative assumptions",
    ),
    (
        "receiver",
        "https://wiki.dfrobot.com/sen0262/",
        "120ohm 0-25mA published domain; no input-fault immunity proof",
    ),
    (
        "receiver schematic",
        "https://dfimg.dfrobot.com/wiki/17563/SEN0262_current-to-voltage_schematics_v1.pdf",
        "TP5551 buffer; separate burden-input experiment is not whole-board simulation",
    ),
    (
        "loop protector",
        "https://www.analog.com/media/en/technical-documentation/data-sheets/MAX14626.pdf",
        "45ohm max, 27-33mA DC bound, 36V input; dynamic fault overshoot/thermal cycling omitted",
    ),
    (
        "isolation",
        "https://www.ti.com/lit/ds/symlink/tmux1511.pdf",
        "3.6V powered-off signal domain; ideal PG switch timing is an explicit model gap",
    ),
    (
        "current",
        "https://www.ti.com/lit/ds/symlink/ina219.pdf",
        "+/-320mV shunt and 26V common mode; 0.1ohm from actual DNA module listing",
    ),
    (
        "driver",
        "https://www.ti.com/lit/ds/symlink/drv8871.pdf",
        "3.6A peak, 0.565ohm typical combined bridge resistance at specified conditions, TI test-PCB thetaJA41.1C/W; thermal shutdown/recovery not modeled",
    ),
    (
        "valve family",
        "https://www.uflowvalve.com/Assets/Product/Catalogue/solenoid-valve/uflow_das_series_2_way_direct_acting_valve.pdf",
        "12V10W family option; exact seller coil/part unresolved, L assumed",
    ),
    (
        "hydraulic bypass",
        "https://assets.rs-online.com/image/upload/v1720004472/Datasheets/ecdedbd5e5f64de5b3b30b97a04c022d.pdf",
        "Automatic/differential bypass, not demonstrated safety relief; missing capacity/tolerance",
    ),
    (
        "temperature",
        "https://www.analog.com/media/en/technical-documentation/data-sheets/DS18B20.pdf",
        "3.0-5.5V, 1-Wire, max 750ms 12bit conversion, chip accuracy not assembly calibration",
    ),
]
provenance = dict(
    checked=b["checked"],
    sources=[dict(component=x, url=y, interpretation=z) for x, y, z in sources],
    assumed=dict(
        pump_startup="1-3x current in standalone envelope; integrated 1uF/1.5A nominal versus 100uF/3A failed start, neither vendor internals",
        valve_L_H=[0.2, 0.5],
        cutoff="earlier R1 behavioral RC/manual reset/watchdog, not selected IC/PCB",
        thermal="Cth0.02J/K; theta41.1 TI PCB or assumed65C/W; Rds hot bound0.96ohm; no shutdown/dual-channel heating",
        hydraulic="straight-line endpoint envelope only; K6; 2m pipe; actual valve/meter/bypass curves missing",
    ),
    procurement_release=False,
)
(root / "sources.json").write_text(json.dumps(provenance, indent=2) + "\n")
# Full descriptions and quote holds stay inspectable; no copied full vendor descriptions.
cards = []
for x in b["items"]:
    cards.append(
        f'''<article class="item" data-kind="{e(x["kind"])}"><div class="eyebrow">{e(x["role"])} · {e(x["kind"])}</div><h3>{e(x["model"])}</h3><div class="price">{money(x["planning_line_INR"])} <small>for {x["quantity"]}</small></div><p class="stock">{e(x["stock"])}</p><p>{e(x["description"])}</p><details><summary>Specifications, delivery and purchase conditions</summary><p><b>Price basis:</b> {e(x["price_basis"])}; unit {money(x["unit_price_INR"])}.</p><p><b>Delivery:</b> {e(x["pin_delivery"])}</p><p><b>Open issues:</b> {e(x["holds"])}</p></details><a href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">View {e(x["supplier"])} listing ↗</a></article>'''
    )
case_rows = "".join(
    f"<tr><td>{e(x['name'])}</td><td>{'Within stated envelope' if x['criteria_pass'] else 'Rejected as expected'}</td><td>{x['samples']:,}</td><td>{e(x['reason'])}</td></tr>"
    for x in s["results"]
)
allowance_rows = "".join(
    f"<tr><td>{e(x['role'])}</td><td>{e(x['quantity'])}</td><td>{money(x['reserve_INR'])}</td></tr>"
    for x in b["allowances"]
)
analysis = "".join(
    f"<tr><td>{e(x['name'])}</td><td>{x['value']:.5g} {e(x['unit'])}</td><td>{e(x['basis'])}</td></tr>"
    for x in s["analytical_checks"]
)
page = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CertaRig | Indian purchase review</title><style>
*:before,*:after,*{{box-sizing:border-box}}body{{margin:0;background:#f4f5f1;color:#182923;font:16px/1.55 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif}}header{{background:#17382f;color:white;padding:42px max(24px,calc((100vw - 1160px)/2))}}h1{{font-size:clamp(32px,4vw,52px);line-height:1.1;margin:12px 0}}h2{{font-size:28px;margin:38px 0 12px}}h3{{font-size:19px;margin:8px 0}}main{{max-width:1210px;margin:auto;padding:24px}}.eyebrow{{letter-spacing:1px;text-transform:uppercase;font-size:12px;font-weight:700;opacity:.85}}.badge{{display:inline-block;background:#ffe1ab;color:#4c330d;padding:6px 12px;border-radius:6px;font-weight:700}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:24px}}.metric{{border-top:1px solid #718a80;padding-top:14px}}.metric strong{{display:block;font-size:29px}}.note{{padding:20px;background:#fff4dc;border-left:4px solid #c78520;border-radius:4px}}.links{{display:flex;gap:20px;flex-wrap:wrap;margin:20px 0}}a{{color:#176c53}}header a{{color:white}}button{{border:1px solid #b9c7bd;border-radius:6px;padding:10px 16px;background:white;color:#18382e;font-weight:600;cursor:pointer}}button.active{{background:#17382f;color:white}}.filters{{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}.item{{background:white;border:1px solid #d9e0d9;border-radius:10px;padding:20px;display:flex;flex-direction:column}}.item p{{font-size:14px}}.item a{{margin-top:auto;padding-top:14px}}.price{{font-size:25px;font-weight:700}}small{{font-size:13px;font-weight:400}}.stock{{color:#6c4b12;background:#fff6df;padding:9px;border-radius:4px}}details{{font-size:14px;margin:10px 0}}summary{{cursor:pointer;font-weight:600}}table{{border-collapse:collapse;width:100%;background:white;font-size:14px}}td,th{{padding:11px;border-bottom:1px solid #e0e5de;text-align:left;vertical-align:top}}th{{background:#e4ebe3}}.scroll{{overflow:auto}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.panel{{padding:22px;background:white;border:1px solid #d9e0d9;border-radius:10px}}li{{margin:9px 0}}code{{background:#e7ece5;padding:2px 5px;overflow-wrap:anywhere}}footer{{border-top:1px solid #cbd6cb;margin-top:40px;padding:24px 0;color:#657268;font-size:13px}}img{{max-width:100%;height:auto}}[hidden]{{display:none!important}}@media(max-width:850px){{.grid{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}}}@media(max-width:560px){{.grid,.metrics{{grid-template-columns:1fr}}header{{padding:30px 24px}}}}@media print{{.filters,button{{display:none}}details{{display:block}}.grid{{grid-template-columns:1fr 1fr}}.item{{break-inside:avoid}}header{{color:#182923;background:white}}}}
</style><header><div class="eyebrow">CertaRig · Engineering procurement review · 9–10 November 2026</div><h1>Source the parts.<br>Keep the evidence attached.</h1><p>Mumbai PIN 400053 · No orders or vendor messages sent.</p><span class="badge">HOLD — assembly and budget unresolved</span><div class="metrics"><div class="metric"><strong>{money(b["planning_total_INR"])}</strong>planning estimate; import duty still open</div><div class="metric"><strong>₹15,000</strong>agreed ceiling</div><div class="metric"><strong>{len(s["results"])} experiments</strong>{positive} within envelope · {negative} expected rejections</div></div></header><main>
<div class="note"><b>Do not place the full order yet.</b> Major items are sourced, but the exact water valve, independent pressure protection, pump startup and physical cutoff implementation are unresolved. Published stock is not the same as verified delivery. The lower-cost substitution route still totals about {money(b["revised_option"]["revised_planning_total_before_other_changes_INR"])} and is not confirmed.</div>
<nav class="links"><a href="README.md">Full written review</a><a href="basket.json">Editable basket JSON</a><a href="SUPPLIER_QUESTIONS_UNSENT.md">Unsent supplier questions</a><a href="#evidence">Simulation evidence</a></nav>
<div class="two"><section class="panel"><h3>Delivery checks that actually completed</h3><p><b>Robu pump:</b> 400053 resolved to Mumbai; estimated 13 Nov air / 16 Nov standard. In Stock, ₹2,929 including GST.</p><p><b>Evelta receiver:</b> 25 units; expected 12 Nov for 400053. Holiday notice permits up to 72h dispatch delay.</p><p><b>Industrybuying valve:</b> PIN returned prepaid/COD service, no dated arrival observed. The air-medium listing is not accepted for water.</p><small>Dates are website estimates from the review, not guarantees. Most remaining lines need exact delivery checks.</small></section><section class="panel"><h3>How the estimate was built</h3><p>Candidate lines: <b>{money(b["primary_subtotal_INR"])}</b><br>Assembly, fittings and freight reserves: <b>{money(b["allowance_reserve_INR"])}</b></p><p>Includes a 30m hose roll because 5m offcut sale is unconfirmed. Imported parts include a conservative 18% tax reserve, not a customs assessment. SEN0262 comparison purchase is excluded.</p><p>There are {len(b["allowances"])} cost groups with unresolved exact SKUs or quotes. They are not presented as a completed purchase basket.</p></section></div>
<h2>Product options and actual interfaces</h2><p>Descriptions are summarized from supplier/manufacturer pages. Open each card for variant conflicts, delivery status and conditions.</p><div class="filters"><button class="active" data-filter="candidate">Primary candidates</button><button data-filter="alternative">Alternatives</button><button data-filter="comparison">Comparison module</button><button data-filter="rejected">Rejected / unavailable</button><button data-filter="all">All options</button></div><div class="grid">{"".join(cards)}</div>
<h2>Unquoted requirements</h2><div class="scroll"><table><thead><tr><th>Requirement</th><th>Quantity / scope</th><th>Reserve, not quote</th></tr></thead><tbody>{allowance_rows}</tbody></table></div>
<section id="evidence"><h2>Simulation results and limits</h2><p>{sum(x["samples"] for x in s["results"]):,} finite recorded samples · ngspice 47 · full-horizon checks · offline replay. Expected rejections remain design findings, not proof that those parts are safe.</p><div class="note">{e(assumptions)}</div><div class="two" style="margin-top:20px"><section class="panel"><h3>Receiver and measurement changes</h3><p>100Ω protected-input envelope passes modeled 21.6–26.4V and Pi-off cases. 120Ω × 33mA = 3.96V at the burden; this does not simulate the full SEN0262 buffer. A 12V supply lacks full-scale Nishka-loop compliance.</p><p>INA219 with 0.1Ω shunt cannot measure the old 4A threshold. 2.5A is measurable but actual pump startup and independent fast protection still need design review.</p></section><section class="panel"><h3>Power and hydraulic limits</h3><p>DRV8871's 3.6A continuous retail claim fails the thermal analogy. Actual board cooling and auto-recovery behavior remain unqualified.</p><p>5–6m pump head means ~0.49–0.59bar static, not a physical operating target. The low-range sensor would overrange. A selected valve/bypass hydraulic transient model cannot be completed without their curves and closing behavior.</p></section></div><div id="plots"></div><details><summary>All circuit experiments</summary><div class="scroll"><table><thead><tr><th>Experiment</th><th>Result</th><th>Samples</th><th>Declared unsuitable comparison</th></tr></thead><tbody>{case_rows}</tbody></table></div></details><details><summary>Separate calculations and assumptions</summary><div class="scroll"><table><thead><tr><th>Calculation</th><th>Value</th><th>Basis</th></tr></thead><tbody>{analysis}</tbody></table></div></details><p><a href="summary.json">Raw results</a> · <a href="sources.json">Parameter provenance</a> · <a href="run_review.py">Reproduction / offline verifier</a> · <a href="SHA256SUMS">Checksums</a></p><code>python3 run_review.py verify .</code></section>
<h2>What happens next</h2><ol>{"".join("<li>" + e(x) + "</li>" for x in nextsteps)}</ol><footer>Preserved Phase 3 installation and historical evidence. All new work here is research and simulation; no physical rig connection, purchase, supplier enquiry or live-model call. GBrain was unavailable; restarting Codex may load its registered server.</footer></main><script>
const buttons=[...document.querySelectorAll('[data-filter]')];function filter(kind){{document.querySelectorAll('.item').forEach(x=>x.hidden=kind!=='all'&&x.dataset.kind!==kind);buttons.forEach(x=>x.classList.toggle('active',x.dataset.filter===kind));}}buttons.forEach(x=>x.addEventListener('click',()=>filter(x.dataset.filter)));filter('candidate');
</script></html>"""
(root / "index.html").write_text(page)
# A compact machine-readable capture of completed UI observations, no full address.
(root / "delivery_observations.json").write_text(
    json.dumps(
        dict(
            checked=b["checked"],
            PIN="400053",
            observations=[
                dict(
                    supplier="Robu",
                    product="R256922",
                    method="Live browser product/pincode UI",
                    stock="In Stock",
                    price_INR=2929,
                    arrival_estimate=["2026-11-13 air", "2026-11-16 standard"],
                ),
                dict(
                    supplier="Evelta",
                    product="147-SEN0262",
                    method="Live browser product/pincode UI",
                    stock=25,
                    price_INR=546.34,
                    arrival_estimate="2026-11-12; holiday dispatch warning",
                ),
                dict(
                    supplier="Industrybuying",
                    product="PNE.DIR.18723207",
                    method="Live browser pincode UI",
                    service="Prepaid/COD shown; no arrival date observed",
                ),
            ],
        ),
        indent=2,
    )
    + "\n"
)
print("Built HTML, written review, source provenance and supplier question drafts")
