# EDIT THIS FILE

This is the voiceover you actually record. Change any line under **Say this**. Leave **Keep these facts** alone unless a number is wrong.

How to edit:
1. Open this file, or open `deliverables/CertaRig_Phase3_Submission_Film_Script.docx` in Word / Google Docs.
2. Rewrite **Say this** in your own voice. Shorter is fine.
3. Do not change the **Keep these facts** numbers (4.2 bar, 15 L/min, 12 Sep peaks, Fake on the bench).
4. Tell me what you changed if you want stills and captions regenerated.

Visual grammar (Veritasium + 3Blue1Brown):
- Watch [motion/LOOKBOOK.mp4](motion/LOOKBOOK.mp4) before editing.
- One idea on screen at a time.
- A question, then a demonstration, then what it means.
- Motion clips in `motion/` are the picture. You record only the two live gaps.

Capstone (this is the product, not a hydraulic plant):
CertaRig deploys as an agentic test-operations layer on *someone else’s* rig. A short commissioning interview maps protocols, connections, pins, and components. A human still applies that map. The kernel still owns the output. That interview is designed, not built yet. Say so.

---

## 0:00–0:20  Title
**Picture:** `stills/00_title.png`  
**Optional:** 8 seconds of you on camera instead of the title card.

**Say this:**

This is CertaRig. A test-operations platform where an AI can ask, and a deterministic kernel is the only thing allowed to say yes.

---

## 0:20–1:30  The question
**Picture:** `stills/01_problem_operator.png`, then `stills/02_problem_relay.png`  
**3B1B move:** language approaches a number line and stops.

**Say this:**

For most test benches, the work does not end when the sensors are wired. It actually begins there.

An operator has to run a procedure. Raise pressure. Watch flow. Hit an emergency stop. Write down what happened. The next person inherits a spreadsheet, a screenshot, and a story that is hard to audit.

People speak English. Rigs speak numbers. Four point two bar is not a vibe. Fifteen litres per minute is not “about that high.”

Now imagine putting a language model in the middle, and letting it decide whether a relay is allowed to energize.

That is the wrong product.

The useful question is not whether the AI is clever enough to operate the rig. The useful question is: who is allowed to say yes?

**Keep these facts:** 4.2 bar and 15 L/min are the dry-bench guardrails.

---

## 1:30–2:20  Split the jobs
**Picture:** `../assets/07_product_architecture.png` — reveal Operator, Agent, Kernel, Rig one block at a time.

**Say this:**

CertaRig splits those jobs.

The operator, or an agent, describes intent in ordinary language. Run the pressure test. Explain why it stopped. Shut the bench down.

The agent interprets that request, chooses an approved procedure, and guides the work.

A deterministic kernel measures, compares limits, latches trips, and owns the output. On this dry bench, that output is general-purpose input/output pin twenty-three, the pin that commands the relay.

Every run writes evidence: the procedure, the events, the checks, and a checksummed bundle.

The agent can ask. Only the kernel can say yes.

---

## 2:20–3:20  Who pays / who uses it
**Picture:** `stills/03_customer.png`, then `stills/04_industries_hint.png`

**Say this:**

Who is the end customer?

Not a chatbot user. The customer is the person who already owns a test bench, or is commissioning one. A lab engineer. A technician who has to repeat the same qualification. A team that needs a record that survives the shift change.

Today that customer is us, on a university dry bench. Two potentiometers pretending to be pressure and flow. An analog to digital converter. A physical emergency stop. A low-voltage relay.

Tomorrow that customer is anyone with a mapped rig. A hydraulic cart. A battery pack on controller area network. A Siemens or Allen-Bradley cell. A Modbus skid.

We are not claiming that an agent can look at a photograph of an unknown machine and take control. That is not proven.

The product is an agentic system you deploy onto a mapped rig, with inspectable evidence.

---

## 3:20–4:20  Same kernel, different buses
**Picture:** `stills/05_protocol_strip.png` — pan across the row.

**Say this:**

The same kernel can sit on more than one bus.

If the plant already publishes MQTT topics, we observe those tags. If it is a register map, Modbus TCP or RTU. If it is a modern programmable logic controller, OPC UA. Native Siemens S7 data blocks. Allen-Bradley EtherNet/IP tags. Vehicle and battery benches on CAN.

Every fieldbus example ships observe-only. A successful browse is not permission to write. A human still applies the map. Procedures that require an output still need a digital-twin pass, then an explicit arm.

That is how this grows. Not by giving the model more authority, but by letting more benches plug the same safety kernel into the buses they already have.

---

## 4:20–5:40  Why this AI
**Picture:** `stills/06_ai_stack.png`, then `stills/07_ai_benchmark.png`

**Say this:**

Why this AI?

There are two different AIs in this project, and they must not be confused.

While building CertaRig I used Cursor with Grok 4.6. That is a development assistant. It writes code, tests, and documentation. If that model is unavailable, the fallback is another Cursor model, or Claude, or GPT. None of those models are allowed to drive the relay.

Inside the product, the runtime agent is provider-neutral.

The default is Fake: a deterministic rule-based policy. It has no API key. It is what continuous integration uses, and it is what ran the twelfth of September hardware procedures. When you say “run the four point two bar test,” it selects the pressure guardrail skill. When you say “run fifteen litres per minute,” it selects flow. It never compares the number itself.

The intended live interpreter is Claude Sonnet 4.5, because tool use is first-class. The second choice is OpenAI GPT-4.1-mini, or any OpenAI-compatible endpoint, including a local server, through an OpenAI base URL. There is also a replay provider, so a transcript can be run again exactly.

We do not benchmark these models on trivia. We benchmark them on this use case. Pick the approved skill. Call only the tools the capability manifest allows. Never compare four point two bar. Stop if reset or shutdown needs a human. Swap providers without changing the Edge API.

Live Anthropic and OpenAI adapters exist in the tree. They are not the proven bench path. The twelfth of September lab used Fake. We are not going to pretend otherwise.

**Keep these facts:** Fake ran the 12 Sep hardware. Live Claude/OpenAI are adapters, not the proven bench path.

---

## 5:40–7:00  What Phase 3 actually proved
**Picture:** `../assets/01_gate_ladder.png`, then `../assets/02_hardware_peaks.png`, then `stills/08_output_equation.png` (reveal one term at a time).

**Say this:**

We did not jump from code to an energized relay. We crossed six gates.

Gate zero was read only. Inspect the frozen Phase 3 system, and confirm the new platform had not overwritten it.

Gate one created a sidecar. Separate folder, separate port, user-local configuration.

Gate two was observe only. Output authority stayed off while both analog channels were swept. The first attempt failed because the pressure movement was incomplete. We kept that failure. The next complete sweep passed with one thousand two hundred ninety-one samples.

Gate three was the digital twin. Six exact procedure hashes had to pass in simulation first.

Gate four allowed controlled actuation. The Fake agent ran five approved procedures. The kernel owned every comparison and trip.

Gate five restored the original Phase 3 dashboard, verified it was untouched, disabled actuation, and halted the Pi.

After that first failed observation, six hardware runs passed. Three thousand four hundred twenty-two samples. Thirty-four of thirty-four evaluated checks.

Pressure crossed four point two bar and peaked at four point eight three. Flow crossed fifteen litres per minute and peaked at fifteen point four one. The emergency stop forced safe. Releasing it did not restart the output. A new permit without reset was rejected.

The output is on only when five things are true at once. Actuation enabled. A permit requested. No trip latched. The emergency stop closed. And the process healthy.

**Keep these facts:** 3,422 samples, 34/34 checks, 4.83 bar, 15.41 L/min, first ADC sweep failed and was kept.

---

## 7:00–7:45  Phase 3 dashboard (course PoC)
**Picture:** your `P3_dashboard_8080.mp4`. Overlay: `Phase 3 dashboard · port 8080 · observe only`

**Say this:**

This is the frozen Phase 3 dashboard, on port eight zero eight zero. It is the course proof of concept. Live readings. The dry-bench map. Observe only.

This is not the capstone product. It is the evidence that the low-voltage bench already worked.

Watch the meters. Do not arm anything here.

---

## 7:45–11:00  Studio demo (stitch your recording)
**Picture:** your Studio clips. Overlay `Studio · simulator` or `Studio · Raspberry Pi sidecar :8081`. Hold on clicks. Do not talk over the trip.

**Say this:**

Now the product. This is Studio, talking to the Edge node.

Live shows both channels. Pressure in bar. Flow in litres per minute. Trip lines are drawn on the graph. The scorecard says whether the node is ready to arm.

Onboard is where a human reviews a proposed map. The agent may suggest. The human applies.

Author is for procedures. We are not inventing a skill on a live output.

Procedures lists the approved pack. Relay truth table. Pressure guardrail. Flow guardrail. Dual input. Emergency stop.

Agent. This pill says Fake, because that is the proven path. Type what an operator would actually say: run the four point two bar test.

The agent reads the skill, starts the named procedure, and waits. It does not watch the converter and decide that four point two has arrived.

Raise the pressure emulator. When the kernel sees the crossing, the commanded output goes safe and stays latched.

Reset is not automatic. Reset is an approval. Without that human grant, a new permit is rejected.

Same pattern for fifteen litres per minute. Independent trip. Same output.

If I ask it to shut the bench down, that is also an approval. The kernel forces safe first.

Evidence. Every completed run is a folder. Procedure, events, result, report, manifest, checksums. That bundle is the product, not the screenshot.

What you are watching on the simulator is labelled as a simulation. What you saw on the twelfth of September hardware is labelled as Raspberry Pi. We do not mix those claims.

---

## 11:00–11:50  Capstone: any rig, short interview
**Picture:** `stills/09_any_rig.png` → `stills/10_interview.png` → `stills/11_map_locked.png` → `stills/13_capstone_loop.png`

This is the capstone. Not a hydraulic machine. Not “AI discovers an unknown plant from a photo and drives it.”

**Say this:**

Phase 3 proved the kernel on one mapped dry bench. That is the foundation. It is not the capstone.

The capstone is an agentic system you can deploy onto someone else’s test rig.

They install it on their machine. A Pi. An industrial PC. A laptop talking to their controller.

Then the agent runs a short commissioning interview. What modules are here? Which bus? GPIO and an analog converter, or MQTT, Modbus, OPC UA, Siemens S7, EtherNet/IP, CAN? Which pin, register, or tag is pressure? Which is flow? What are the trip numbers and units? What must stay observe-only?

The agent proposes a map. A human still has to apply it. The digital twin rehearses the exact procedure. Only then can anyone arm an output.

We have not built that interview yet. Onboard today is a form, not discovery. Capstone is where the interview becomes the product, without ever giving the model the dangerous decision.

**Keep these facts:** interview is design, not proven. Twin-gate + human apply + explicit arm stay required.

---

## 11:50–12:20  Close
**Picture:** `stills/14_close.png`  
**Optional:** you on camera for the last two sentences.

**Say this:**

The most important Phase 3 result is not that an AI switched a relay.

It is that the AI never had to own the dangerous decision.

CertaRig let the agent ask, the operator approve, the kernel decide, and the evidence explain what happened afterward.

Phase 3 is complete. The capstone is to put this on any mapped bench, starting with a short commissioning interview.

The AI can ask. Only the kernel can say yes.
