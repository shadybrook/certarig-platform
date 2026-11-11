# CertaRig Phase 3 submission script

**Edit the spoken lines in [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md).** This file is the picture/timing companion. Visual grammar: Veritasium question + 3Blue1Brown one-idea diagrams, not a product ad.

**Working title:** What is CertaRig?
**Presenter card:** Chintan Dedhia
**Target duration:** 11:40 to 12:20
**Spoken rate:** about 140 words per minute
**Format:** Voiceover, diagrams that reveal one idea at a time, then a stitched product walkthrough. Optional face at open and close.

## Production grammar

- White title cards. Flat illustrated scenes for the problem. One architecture diagram, revealed in pieces. Then the real UI.
- Safety colours stay consistent: blue for observation, green for permitted, red for forced safe, gold for reset required.
- Define every abbreviation on first use: analog to digital converter, emergency stop, hardware in the loop, general-purpose input/output.
- Never call a simulated trace a hardware trace. Never call a GPIO command transition a measured relay response.
- Never say Grok, Claude, or GPT tripped the relay.
- On first use of a live clip, label the surface on screen: `Phase 3 dashboard · observe only` or `Studio · simulator` or `Studio · Raspberry Pi sidecar`.

Word count of the spoken track is about 1,650 words, which is just under twelve minutes at 140 words per minute. Hold on demo screens when the operator is clicking; do not rush the 7:45 to 11:00 block.

---

## 0:00 to 0:20 — Title

**Picture:** `stills/00_title.png`. Hold three silent seconds, then Ken-Burns a slow push-in.

**Narration:**

This is CertaRig. A test-operations platform where an AI can ask, and a deterministic kernel is the only thing allowed to say yes.

**On screen:** `What is CertaRig?`  
**Lower third from 0:08:** `Presented by Chintan Dedhia`

---

## 0:20 to 1:30 — The problem

**Picture:** `stills/01_problem_operator.png` for the operator and clipboard. Cut stock B-roll of a test cell, a pressure gauge, and a PLC cabinet from the search list in [capture-and-edit.md](capture-and-edit.md). Return to `stills/02_problem_relay.png` on the last two sentences.

**Narration:**

For most test benches, the work does not end when the sensors are wired. It actually begins there.

An operator has to run a procedure. Raise pressure. Watch flow. Hit an emergency stop. Write down what happened. The next person inherits a spreadsheet, a screenshot, and a story that is hard to audit.

People speak English. Rigs speak numbers. Four point two bar is not a vibe. Fifteen litres per minute is not “about that high.”

Now imagine putting a language model in the middle, and letting it decide whether a relay is allowed to energize.

That is the wrong product.

The useful question is not whether the AI is clever enough to operate the rig. The useful question is: who is allowed to say yes?

**On screen, last beat:** `Who is allowed to energize the output?`

---

## 1:30 to 2:20 — What CertaRig is

**Picture:** `../assets/07_product_architecture.png`. Reveal one block at a time: Operator and Studio, then Agent, then Kernel, then Rig.

**Narration:**

CertaRig splits those jobs.

The operator, or an agent, describes intent in ordinary language. Run the pressure test. Explain why it stopped. Shut the bench down.

The agent interprets that request, chooses an approved procedure, and guides the work.

A deterministic kernel measures, compares limits, latches trips, and owns the output. On this dry bench, that output is general-purpose input/output pin twenty-three, the pin that commands the relay.

Every run writes evidence: the procedure, the events, the checks, and a checksummed bundle.

The agent can ask. Only the kernel can say yes.

**On screen:** `Agent interprets. Kernel decides. Evidence explains.`

---

## 2:20 to 3:20 — Who is the end customer

**Picture:** `stills/03_customer.png`, then a slow pan across `stills/04_industries_hint.png`.

**Narration:**

Who is the end customer?

Not a chatbot user. The customer is the person who already owns a test bench, or is commissioning one. A lab engineer. A technician who has to repeat the same qualification. A team that needs a record that survives the shift change.

Today that customer is us, on a university dry bench. Two potentiometers pretending to be pressure and flow. An analog to digital converter. A physical emergency stop. A low-voltage relay.

Tomorrow that customer is anyone with a mapped rig. A hydraulic cart. A battery pack on controller area network. A Siemens or Allen-Bradley cell. A Modbus skid.

We are not claiming that an agent can look at a photograph of an unknown machine and take control. That is not proven, and it is not where the value is yet.

The product is agent-guided commissioning and test operations for a mapped rig, with inspectable evidence.

**On screen:** `Mapped rigs. Not unknown machines.`

---

## 3:20 to 4:20 — Growing into industries

**Picture:** `stills/05_protocol_strip.png`. Zoom along the row. Optional stock cutaways of a factory HMI, a motor-control cabinet, and an automotive bench.

**Narration:**

The same kernel can sit on more than one bus.

If the plant already publishes MQTT topics, we observe those tags. If it is a register map, Modbus TCP or RTU. If it is a modern programmable logic controller, OPC UA. Native Siemens S7 data blocks. Allen-Bradley EtherNet/IP tags. Vehicle and battery benches on CAN.

Every fieldbus example ships observe-only. A successful browse is not permission to write. A human still applies the map. Procedures that require an output still need a digital-twin pass, then an explicit arm.

That is how this grows. Not by giving the model more authority, but by letting more industries plug the same safety kernel into the buses they already have.

**On screen:** `Same kernel. Different rig.json. Observe first.`

---

## 4:20 to 5:40 — Why this AI, the benchmark, and the fallback

**Picture:** `stills/06_ai_stack.png`. Hold on each of the three columns as it is named. End on `stills/07_ai_benchmark.png`.

**Narration:**

Why this AI?

There are two different AIs in this project, and they must not be confused.

While building CertaRig I used Cursor with Grok 4.6. That is a development assistant. It writes code, tests, and documentation. If that model is unavailable, the fallback is another Cursor model, or Claude, or GPT. None of those models are allowed to drive the relay.

Inside the product, the runtime agent is provider-neutral.

The default is Fake: a deterministic rule-based policy. It has no API key. It is what continuous integration uses, and it is what ran the twelfth of September hardware procedures. When you say “run the four point two bar test,” it selects the pressure guardrail skill. When you say “run fifteen litres per minute,” it selects flow. It never compares the number itself.

The intended live interpreter is Claude Sonnet 4.5, because tool use is first-class. The second choice is OpenAI GPT-4.1-mini, or any OpenAI-compatible endpoint, including a local server, through an OpenAI base URL. There is also a replay provider, so a transcript can be run again exactly.

We do not benchmark these models on trivia. We benchmark them on this use case. Pick the approved skill. Call only the tools the capability manifest allows. Never compare four point two bar. Stop if reset or shutdown needs a human. Swap providers without changing the Edge API.

Live Anthropic and OpenAI adapters exist in the tree. They are not the proven bench path. The twelfth of September lab used Fake. We are not going to pretend otherwise.

**On screen:** `Build-time: Grok 4.6. Runtime default: Fake. Live fallbacks: Claude, then OpenAI.`  
**Second card:** `Benchmark: skill routing and tool discipline. Not chat quality.`

---

## 5:40 to 7:00 — How Phase 3 actually proved it

**Picture:** `../assets/01_gate_ladder.png`, then overhead bench B-roll if you have it, then `../assets/02_hardware_peaks.png`, then `stills/08_output_equation.png`. Optional insert: `../assets/05_kernel_event_timeline.png`.

**Narration:**

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

**On screen:** `Observe, simulate, arm, run, restore.`  
**Equation card:** `OUTPUT = enabled AND permit AND not tripped AND E-stop closed AND healthy`

---

## 7:00 to 7:45 — Phase 3 dashboard, observe only

**Picture:** Screen recording of the frozen Phase 3 live dashboard on port 8080. Label the whole clip. Do not click arm. Optional cutaway of the physical bench sitting idle.

**Narration:**

This is the frozen Phase 3 dashboard, on port eight zero eight zero. It is the course proof of concept. Live readings. The dry-bench map. Observe only.

This is not the capstone product. It is the evidence that the low-voltage bench already worked.

Watch the meters. Do not arm anything here.

**On screen, full clip:** `Phase 3 dashboard · port 8080 · observe only`

---

## 7:45 to 11:00 — Stitch the product demo

**Picture:** Screen recording of Studio against the simulator, or against the sidecar on port 8081 if the Pi is already up. Follow the capture checklist. Overlay the surface label for the first five seconds of each scene.

Hold on the click. Do not talk over a trip crossing; let the graph and the kernel event speak, then resume.

### 7:45 — Live

**Narration:**

Now the product. This is Studio, talking to the Edge node.

Live shows both channels. Pressure in bar. Flow in litres per minute. Trip lines are drawn on the graph. The scorecard says whether the node is ready to arm.

**On screen:** `Studio · Live` and either `simulator` or `Raspberry Pi sidecar :8081`

### 8:15 — Onboard and Author, in passing

**Narration:**

Onboard is where a human reviews a proposed map. The agent may suggest. The human applies.

Author is for procedures. We are not inventing a skill on a live output.

### 8:35 — Procedures and Agent

**Narration:**

Procedures lists the approved pack. Relay truth table. Pressure guardrail. Flow guardrail. Dual input. Emergency stop.

Agent. This pill says Fake, because that is the proven path. Type what an operator would actually say: run the four point two bar test.

The agent reads the skill, starts the named procedure, and waits. It does not watch the converter and decide that four point two has arrived.

**On screen:** `Fake agent selects the skill. Kernel compares the number.`

### 9:10 — Pressure trip

**Narration:**

Raise the pressure emulator. When the kernel sees the crossing, the commanded output goes safe and stays latched.

Reset is not automatic. Reset is an approval. Without that human grant, a new permit is rejected.

**On screen at the crossing:** `4.2 bar · kernel trip · output latched safe`

### 9:45 — Flow trip

**Narration:**

Same pattern for fifteen litres per minute. Independent trip. Same output.

**On screen:** `15 L/min · independent trip · same output`

### 10:15 — Shutdown approval

**Narration:**

If I ask it to shut the bench down, that is also an approval. The kernel forces safe first.

**On screen:** `Shutdown needs a human. Kernel forces safe first.`

### 10:35 — Evidence

**Narration:**

Evidence. Every completed run is a folder. Procedure, events, result, report, manifest, checksums. That bundle is the product, not the screenshot.

What you are watching on the simulator is labelled as a simulation. What you saw on the twelfth of September hardware is labelled as Raspberry Pi. We do not mix those claims.

**On screen:** `Checksummed evidence is the output of the procedure.`

---

## 11:00 to 11:50 — Capstone: any rig, short interview

**Picture:** `stills/09_any_rig.png` → `stills/10_interview.png` → `stills/11_map_locked.png` → `stills/13_capstone_loop.png`

**Narration:**

Phase 3 proved the kernel on one mapped dry bench. That is the foundation. It is not the capstone.

The capstone is an agentic system you can deploy onto someone else’s test rig.

They install it on their machine. A Pi. An industrial PC. A laptop talking to their controller.

Then the agent runs a short commissioning interview. What modules are here? Which bus? GPIO and an analog converter, or MQTT, Modbus, OPC UA, Siemens S7, EtherNet/IP, CAN? Which pin, register, or tag is pressure? Which is flow? What are the trip numbers and units? What must stay observe-only?

The agent proposes a map. A human still has to apply it. The digital twin rehearses the exact procedure. Only then can anyone arm an output.

We have not built that interview yet. Onboard today is a form, not discovery. Capstone is where the interview becomes the product, without ever giving the model the dangerous decision.

**On screen:** `Deploy on their rig. Interview. Human applies. Twin. Then arm.`

---

## 11:50 to 12:20 — Close

**Picture:** `stills/14_close.png`. Optional face for the last two sentences. Do not recreate an energized sequence solely for this edit.

**Narration:**

The most important Phase 3 result is not that an AI switched a relay.

It is that the AI never had to own the dangerous decision.

CertaRig let the agent ask, the operator approve, the kernel decide, and the evidence explain what happened afterward.

Phase 3 is complete. The capstone is to put this on any mapped bench, starting with a short commissioning interview.

The AI can ask. Only the kernel can say yes.

**Final card:** `The AI can ask. Only the kernel can say yes.`
