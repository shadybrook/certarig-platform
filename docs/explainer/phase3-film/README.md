# Phase 3 submission film pack

Curastra-grammar product film for the 20 September Phase 3 submission.

**Working title:** What is CertaRig?
**Target duration:** 11:40 to 12:10
**Final line:** The AI can ask. Only the kernel can say yes.

This pack is the Phase 3 *submission* film. The 13 September curiosity-led script remains at [`../2026-09-13-video-script.md`](../2026-09-13-video-script.md) as a lab explainer. Do not mix the two spines in one cut.

## What is in this folder

| File | Use |
| --- | --- |
| [script.md](script.md) | Timed voiceover, picture, and on-screen text |
| [voiceover.md](voiceover.md) | Clean read-aloud, no picture notes |
| [shot-list.md](shot-list.md) | CapCut in/out labels |
| [captions.srt](captions.srt) / [captions.md](captions.md) | Burned-in captions, Curastra lower-third style |
| [capture-and-edit.md](capture-and-edit.md) | Demo capture, assembly order, stock search |
| [stills/](stills/) | 16:9 title, problem, customer, AI, protocol, mission, and close cards |

Spoken track is about 1,480 words (~10:35 at 140 wpm). Demo holds bring the cut to 11:40–12:10.

### Stills

| File | Beat |
| --- | --- |
| `stills/00_title.png` | Opening title |
| `stills/01_problem_operator.png` | Operator, clipboard, unlabeled bench |
| `stills/02_problem_relay.png` | Language stopped before the locked relay |
| `stills/03_customer.png` | Commissioning engineer at the dry bench |
| `stills/04_industries_hint.png` | Five domains, one kernel |
| `stills/05_protocol_strip.png` | MQTT through CAN, observe-only |
| `stills/06_ai_stack.png` | Grok / Fake / Claude then OpenAI |
| `stills/07_ai_benchmark.png` | Use-case benchmark, not trivia |
| `stills/08_output_equation.png` | Five-term output invariant |
| `stills/09_mission_1.png` … `12_mission_4.png` | Capstone missions |
| `stills/13_missions_summary.png` | Four-mission recap |
| `stills/14_close.png` | Final card |

Rebuild the typographic cards with `python3 tools/build_phase3_film_stills.py`. Rebuild the DOCX with `PYTHONPATH=tools python3 tools/build_phase3_film_docx.py`.

Reuse, do not redraw:

- [`../assets/07_product_architecture.png`](../assets/07_product_architecture.png)
- [`../assets/01_gate_ladder.png`](../assets/01_gate_ladder.png)
- [`../assets/02_hardware_peaks.png`](../assets/02_hardware_peaks.png)
- [`../assets/05_kernel_event_timeline.png`](../assets/05_kernel_event_timeline.png)

## Split of labour

You record voiceover, the 45-second Phase 3 dashboard clip, the Studio/agent demo, and optional bench B-roll. Stitch in CapCut using the shot list.

Do not energize GPIO23 only for the edit. Do not show keys, `.env`, or SSH passwords. Do not call a simulated trace a hardware trace. Do not say Grok or Claude tripped the relay.
