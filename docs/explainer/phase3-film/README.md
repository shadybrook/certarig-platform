# Phase 3 submission film pack

Veritasium question + 3Blue1Brown diagrams for the 20 September Phase 3 submission.

**Working title:** What is CertaRig?
**Target duration:** 11:40 to 12:20
**Final line:** The AI can ask. Only the kernel can say yes.

**Start here:** [PRODUCTION.md](PRODUCTION.md)

Clicking `LOOKBOOK.mp4` in Cursor chat or the editor usually does **nothing** — Cursor does not play MP4s from a file citation. Open it on disk instead:

- Finder: `docs/explainer/phase3-film/motion/LOOKBOOK.mp4` (QuickTime)
- Or watch the GIF: [motion/LOOKBOOK_preview.gif](motion/LOOKBOOK_preview.gif)

If that folder is missing, you are not on branch `cursor/phase3-submission-video-533a`. Fetch/checkout that branch in the **certarig-platform** repo (GitHub: shadybrook/certarig-platform), not only the frozen Phase 3 PoC.

This pack is the Phase 3 *submission* film. Edit spoken lines in [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md). Motion graphics are in [motion/](motion/). Visual grammar is Veritasium question + 3Blue1Brown diagrams. The 13 September lab explainer remains at [`../2026-09-13-video-script.md`](../2026-09-13-video-script.md).

## What is in this folder

| File | Use |
| --- | --- |
| [PRODUCTION.md](PRODUCTION.md) | **Do this.** Watch, read, record, patch |
| [preview.html](preview.html) | Click-through of every motion clip |
| [motion/LOOKBOOK.mp4](motion/LOOKBOOK.mp4) | 96-second visual of the finished film |
| [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md) | Spoken lines you can rewrite |
| [voiceover.md](voiceover.md) | Clean read-aloud |
| [ANIMATION.md](ANIMATION.md) | Clip list and rebuild command |
| [shot-list.md](shot-list.md) | CapCut in/out labels |
| [captions.srt](captions.srt) / [captions.md](captions.md) | Burned-in captions |
| [capture-and-edit.md](capture-and-edit.md) | Demo capture, assembly order, stock search |
| [stills/](stills/) | 16:9 diagrams and illustrations |

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
