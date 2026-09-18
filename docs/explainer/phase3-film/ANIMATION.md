# Animations

The Phase 3 film pack is a 3Blue1Brown / Veritasium explainer: cream paper, teal / gold / ink, one idea at a time. Reveals are spaced across the full spoken duration (`u = t / dur`). It is not the retired dark atelier lookbook.

- **Rebuild:** `python3 tools/render_phase3_explainer.py`
- **Interactive preview:** [preview.html](preview.html)
- **What you still record:** [PRODUCTION.md](PRODUCTION.md)
- **Do not** call `tools/render_phase3_atelier.py`. Do not put `LOOKBOOK.mp4` in the film. Do not `-stream_loop`.

Atelier files (dark studio, `LOOKBOOK.mp4`, the old 7-second clips) live in `motion/atelier_retired/` if kept locally. The cut uses the explainer mp4s below.

## Design

Paper stills in `stills/` and `docs/explainer/assets/` are the picture bible. Type is Inter (else DejaVu, else Arial). 1920×1080 30 fps libx264 crf 20. Frames pipe to ffmpeg stdin — no PNG frame folders.

The picture should behave like the product:

- A speech bubble walks a number line and dies on a gold wall labelled **4.2 bar**. GPIO23 stays locked. A sentence cannot cross a number.
- Five AND-gate terms light. The lamp goes ON, a trip term fails, the lamp goes SAFE, pressure comes home, the lamp stays safe. Reset is required.
- Four blocks appear in spoken order: Operator+Studio, Agent (interprets, never compares), Kernel (measures, latches, owns GPIO23), Rig. Then — and only then — a Ken Burns of the architecture still.
- Six buses appear one by one as observe-only. A browse is not a write.
- Two AIs must not be confused. Fake is the proven runtime. Never imply Grok or Claude tripped the relay.

If a beat can be demonstrated, demonstrate it. Do not dump the whole slide in the first three seconds and freeze.

## Clips

| Clip | Duration | Picture while Chintan talks |
| --- | ---: | --- |
| `01_title.mp4` | 8.0 s | “What is CertaRig?” then “Presented by Chintan Dedhia” then “The AI can ask. Only the kernel can say yes.” |
| `02_question.mp4` | 7.5 s | “Who is allowed to energize the output?” Agent can ask \| Kernel can say yes. |
| `03_problem.mp4` | 12.5 s | Operator, clipboard, spreadsheet/screenshot inheritance. Work begins at the bench. |
| `03_language_stops.mp4` | 9.5 s | “run it, maybe five” walks a number line and dies on 4.2 bar. Relay GPIO23 locked. |
| `03b_relay.mp4` | 10.5 s | Putting an LLM on the relay is the wrong product. Ends on “who is allowed to say yes?” |
| `06_protocols.mp4` | 23.8 s | MQTT, Modbus, OPC UA, Siemens S7, EtherNet/IP, CAN appear as observe-only. A browse is not a write. |
| `04_architecture.mp4` | 28.6 s | Operator+Studio, Agent, Kernel, Rig in order, then Ken Burns of `assets/07_product_architecture.png`. |
| `05_and_gate.mp4` | 18.5 s | Five terms, lamp ON, trip fails, lamp SAFE, pressure home, lamp stays safe. Equation on screen. |
| `05b_latch.mp4` | 9.3 s | Macro of the latched pin / GPIO23. No auto-restart. |
| `08_output_equation.mp4` | 18.5 s | Reveal `stills/08_output_equation.png` one term at a time, then the full OUTPUT = … line. |
| `07_two_ais.mp4` | 7.5 s | Title: two AIs must not be confused. |
| `07b_ai_stack.mp4` | 48.0 s | BUILD Grok 4.6 (never GPIO), RUNTIME Fake (12 Sep proven), FALLBACK Claude then OpenAI (unproven live). Hold Fake. |
| `07c_benchmark.mp4` | 35.2 s | Skill routing, tool discipline, never compare 4.2, stop for human, swap providers. Not trivia. |
| `08_six_gates.mp4` | 16.9 s | Gates 0–5 light in order, then Ken Burns of `assets/01_gate_ladder.png`. |
| `09_interview.mp4` | 38.8 s | Commissioning questions one per beat. Designed, not built. |
| `09b_map.mp4` | 24.4 s | Agent proposes, human applies, twin, then arm. Second half Ken Burns `stills/11_map_locked.png`. |
| `10_capstone_loop.mp4` | 45.25 s | Deploy → Interview → Human apply → Twin → Arm, slowly. Interview is design, not proven. |
| `11_close.mp4` | 9.5 s | The AI can ask. Only the kernel can say yes. |
| `11b_thanks.mp4` | 14.8 s | Hold the close line + Phase 3 complete / capstone is any mapped bench. |

Live Studio\|bench split (Act B / Section 6) is assembled from footage, not from these clips. See `tools/phase3_edit/edl/phase3_film_v4.json`.

## What I did not make

- Your voice
- The live dashboard / Studio / bench recordings
- After Effects or Manim source
