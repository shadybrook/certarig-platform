# Production: what you do vs what is already made

Watch `motion/LOOKBOOK.mp4` first (~122 seconds). It is one studio, not a stack of animated cards. The only things you still have to record sit behind two quiet RECORD lamps.

Then you only do three things:

1. Read the voiceover.
2. Record two live clips.
3. Drop those clips into the RECORD gaps.

I already made the motion. Post is: lookbook clips + your two recordings + your voice.

---

## 1. Watch the lookbook

Do **not** expect the `.mp4` to play when you click it in Cursor chat. Cursor does not open video files that way.

On your Mac, in this repo, after checking out `cursor/phase3-submission-video-533a`:

```bash
open docs/explainer/phase3-film/motion/LOOKBOOK.mp4
```

That launches QuickTime. Or double-click the file in Finder.

If the mp4 is stubborn, open the stills in `motion/proof/` — especially `05_pressure_trip.jpg` and `05_pressure_latched.jpg`. That pair is the whole argument: the number crosses 4.2, the lamp dies, the number comes home, the lamp stays dead.

A silent GIF of that test: [motion/LOOKBOOK_preview.gif](motion/LOOKBOOK_preview.gif)

| Clip | What you see |
| --- | --- |
| `01_title.mp4` | The object. What is this allowed to do? |
| `02_question.mp4` | Who may turn this on? |
| `03_language_stops.mp4` | A sentence hits 4.2 bar |
| `04_architecture.mp4` | Light stops at the kernel |
| `05_and_gate.mp4` | Live pressure test. Latch. No restart |
| `05b_latch.mp4` | The pin, after |
| `06_protocols.mp4` | MQTT through CAN, observe-only |
| `07_two_ais.mp4` | Grok / Fake / Claude then OpenAI |
| `08_six_gates.mp4` | Six lamps. The last waits |
| **`R1_record_dashboard.mp4`** | **YOU RECORD: Phase 3 dashboard, 45s** |
| **`R2_record_studio.mp4`** | **YOU RECORD: Studio demo** |
| `09_interview.mp4` | Questions as lights on the desks |
| `10_capstone_loop.mp4` | Deploy · Interview · Apply · Twin · Arm |
| `11_close.mp4` | The AI can ask. Only the kernel can say yes. |

If a beat feels wrong, change **Say this** in [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md) and tell me. Do not record the bench until the lookbook feels right.

---

## 2. Read this (voiceover)

Clean copy: [voiceover.md](voiceover.md). Editable copy: [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md).

Record in a quiet room, phone is fine. Pause one beat at each heading. When the lookbook shows a RECORD lamp, you will be talking over your own screen capture instead of a motion clip.

---

## 3. Record these two live clips

Hide keys, `.env`, chat, passwords. 1920×1080 if you can. Full-screen browser, bookmarks hidden.

### Clip A — Phase 3 dashboard (45–55 seconds)

- Open the frozen dashboard on **port 8080**.
- Overlay later: `Phase 3 dashboard · port 8080 · observe only`.
- Pan the meters. **Do not arm, permit, or reset.**
- Save `P3_dashboard_8080.mp4`.

If the Pi is off, skip this clip. We will hold the R1 card and a still.

### Clip B — Studio product demo (~4 minutes, simulator is enough)

```bash
make install
.venv/bin/python -m certarig sim serve --port 8080
```

Open http://127.0.0.1:8080/ with the documented demo operator key. Overlay the whole block: `Studio · simulator`.

Record **separate takes**:

| File | Do this | Length |
| --- | --- | --- |
| `studio_live.mp4` | Live page: both channels, trip lines, ready-to-arm | 25–35s |
| `studio_onboard_author.mp4` | Click Onboard, then Author. Do not apply a surprise map | 15–25s |
| `studio_agent_pressure_start.mp4` | Agent pill = Fake. Type `run the 4.2 bar test` | 30–40s |
| `studio_pressure_trip.mp4` | Raise the Live **pressure** slider. Wait for the trip. Show latched safe | 30–40s |
| `studio_flow_trip.mp4` | `run the 15 liters per minute test`. Raise flow. Independent trip | 25–35s |
| `studio_shutdown_approval.mp4` | Ask to shut down. Show Approvals. Kernel goes safe | 15–25s |
| `studio_evidence.mp4` | Evidence page, one run, checksum / export | 20–30s |

Never label simulator traces as Raspberry Pi.

---

## 4. Patch in post

CapCut, 1920×1080, 30 fps.

1. Import everything in `motion/` except `LOOKBOOK.mp4`, `LOOKBOOK_preview.gif`, `lookbook.txt`, and `proof/`.
2. Import your `P3_dashboard_8080.mp4` and `studio_*.mp4`.
3. Timeline order = the table above. Replace R1 with Clip A. Replace R2 with the Studio takes in the table order.
4. Hold the last frame of a motion clip if the voiceover needs more air. Crossfade the studio plates; hard-cut into screen recordings.
5. Import [captions.srt](captions.srt). White type, charcoal pill, lower centre.
6. Music under −20 dB, duck under voice.
7. Export H.264.

Rebuild motion later with:

```bash
python3 tools/render_phase3_atelier.py
```
