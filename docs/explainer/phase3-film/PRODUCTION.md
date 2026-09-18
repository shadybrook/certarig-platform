# Production: what you do vs what is already made

Watch the explainer clips in `motion/` (cream paper, one idea at a time). See [ANIMATION.md](ANIMATION.md). The live Studio|bench pictures for this submission are already in `tools/phase3_edit/edl/phase3_film_v4.json`.

Do **not** use `LOOKBOOK.mp4` or the retired atelier room. Rebuild motion with `python3 tools/render_phase3_explainer.py`.

Voiceover, two live captures, and post remain as below. Post is explainer clips + live footage + voice. Never `-stream_loop`. Never imply Grok or Claude tripped the relay — Fake ran the bench.

---

## 1. Watch the explainer pack

Open [preview.html](preview.html) or the mp4s in `motion/`. Clip duration equals the spoken beat. Atelier files, if kept, are in `motion/atelier_retired/`.

If a beat feels wrong, change **Say this** in [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md) and tell me.

---

## 2. Read this (voiceover)

Clean copy: [voiceover.md](voiceover.md). Editable copy: [SCRIPT_EDIT_ME.md](SCRIPT_EDIT_ME.md).

Record in a quiet room, phone is fine. Pause one beat at each heading. Live Section 6 is the Studio|bench split in the v4 EDL, not a RECORD lamp card.

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

1. Import the explainer mp4s in `motion/` (not `LOOKBOOK.mp4`, not `atelier_retired/`).
2. Import your `P3_dashboard_8080.mp4` and `studio_*.mp4`.
3. Timeline order = the table above. Replace R1 with Clip A. Replace R2 with the Studio takes in the table order.
4. Hold the last frame of a motion clip if the voiceover needs more air. Crossfade the studio plates; hard-cut into screen recordings.
5. Import [captions.srt](captions.srt). White type, charcoal pill, lower centre.
6. Music under −20 dB, duck under voice.
7. Export H.264.

Rebuild motion later with:

```bash
python3 tools/render_phase3_explainer.py
```
