# Phase 3 submission film pack

A 3Blue1Brown / Veritasium explainer pack for the 20 September Phase 3 submission. Cream paper. One idea at a time. Reveals across the spoken beat.

**Working title:** What is CertaRig?
**Final line:** The AI can ask. Only the kernel can say yes.

**Start here:** [ANIMATION.md](ANIMATION.md) · [PRODUCTION.md](PRODUCTION.md)

Rebuild motion with `python3 tools/render_phase3_explainer.py`. Do not call `render_phase3_atelier.py`. Do not put `LOOKBOOK.mp4` in the film.

This pack is the Phase 3 *submission* film. Edit spoken lines in [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md). Motion is in [motion/](motion/). Visual grammar is paper stills plus timed explainer clips, then the designed Studio|bench split for Section 6. The 13 September lab explainer remains at [`../2026-09-13-video-script.md`](../2026-09-13-video-script.md).

## What is in this folder

| File | Use |
| --- | --- |
| [PRODUCTION.md](PRODUCTION.md) | **Do this.** Watch, read, record, patch |
| [preview.html](preview.html) | Click-through of every motion clip |
| [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md) | Spoken lines you can rewrite |
| [voiceover.md](voiceover.md) | Clean read-aloud |
| [ANIMATION.md](ANIMATION.md) | Clip list and rebuild command |
| [shot-list.md](shot-list.md) | CapCut in/out labels |
| [captions.srt](captions.srt) / [captions.md](captions.md) | Burned-in captions |
| [capture-and-edit.md](capture-and-edit.md) | Demo capture, assembly order, stock search |
| [stills/](stills/) | 16:9 diagrams and illustrations |
| [plates/](plates/) | Photographic studio world for the film |

Spoken track is about 1,500 words. Demo holds bring the cut to 11:40–12:20.

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
| `stills/09_any_rig.png` | Capstone: deploy on someone else's bench |
| `stills/09_any_rig_illustration.png` | Optional cutaway of Pi / IPC / laptop |
| `stills/10_interview.png` | Commissioning interview questions |
| `stills/10_interview_illustration.png` | Optional cutaway of chat vs locked schematic |
| `stills/11_map_locked.png` | Proposed map, locked until a human applies |
| `stills/13_capstone_loop.png` | Interview → apply → twin → arm |
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
