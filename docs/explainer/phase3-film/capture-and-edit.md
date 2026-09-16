# Capture and edit checklist

You record three kinds of picture: stills already in [`stills/`](stills/), a 45-second Phase 3 dashboard clip, and a Studio/agent demo. Optional: overhead bench B-roll and free stock. Then assemble in CapCut from [shot-list.md](shot-list.md).

## Before any recording

- Hide `.env`, operator keys, SSH passwords, and chat windows that contain secrets.
- Use the documented demo keys on the simulator only. Do not paste production keys on screen.
- Do not run `deploy/install_pi.sh`.
- Port **8080** stays observe-only. Do not arm it for this film.
- Do not energize GPIO23 solely to get a green LED for the edit. Reuse 12 September footage if you need a hardware cutaway, and label it.
- If the Pi is off, the Studio block is still valid on the simulator.

## Clip A — Phase 3 dashboard (about 45 seconds)

Surface: frozen `certarig_edge` live-dashboard on **http://certarig-pi.local:8080** (or the Mac tunnel you already use). Observe only.

1. Full-screen browser at 1920×1080. Hide bookmarks.
2. Put a tape overlay later: `Phase 3 dashboard · port 8080 · observe only`.
3. Record 45 to 55 seconds of live meters. Slowly pan the cursor. Do not click arm, permit, or reset.
4. Optional 3-second cutaway of the physical bench sitting idle, red indicator visible.
5. Save as `P3_dashboard_8080.mp4`.

If the Pi is off, skip Clip A and extend the title of that section with `stills/00_title.png` plus a labelled still of a previously captured dashboard screenshot. Say so in the VO by shortening “this is the frozen dashboard” to “this is the frozen Phase 3 dashboard we submitted from the Pi.” Prefer a real clip.

## Clip B — Studio product demo (about 4 minutes)

Preferred: simulator on this Mac.

```bash
make install
.venv/bin/python -m certarig sim serve --port 8080
```

Open http://127.0.0.1:8080/ and sign in with the documented demo operator key. Overlay for the whole block: `Studio · simulator`.

If the sidecar is already up on the Pi, you may instead record http://certarig-pi.local:8081 and overlay `Studio · Raspberry Pi sidecar :8081`. Do not start a second kernel. Do not record both worlds as if they were one run.

Record these takes as separate files so the edit can breathe:

| File | What to do | Notes |
| --- | --- | --- |
| `studio_live.mp4` | Live page. Show both channel meters and trip lines. Hover ready-to-arm. | 25–35s |
| `studio_onboard_author.mp4` | Click Onboard, then Author. Do not apply a surprise map. | 15–25s |
| `studio_agent_pressure_start.mp4` | Procedures list, then Agent. Confirm the pill says Fake. Type `run the 4.2 bar test`. | 30–40s |
| `studio_pressure_trip.mp4` | Raise the Live pressure slider (simulator) or P1 pot (sidecar). Wait for the trip. Show the latched safe state. | 30–40s |
| `studio_flow_trip.mp4` | After reset/approval if the procedure needs it, run `run the 15 liters per minute test`. Raise flow. | 25–35s |
| `studio_shutdown_approval.mp4` | Type a shutdown request. Show the Approvals page. Grant or show the pending grant. Kernel goes safe. | 15–25s |
| `studio_evidence.mp4` | Evidence page. Open one completed run. Show checksum / export. | 20–30s |

On the simulator, drive pots from the Live sliders. Never label those traces as Raspberry Pi hardware.

## Clip C — Optional bench B-roll

Reuse existing footage if you have it. New footage only with the bench powered in a state you already trust.

- Overhead of the complete unpowered or observe-only bench.
- Close shots: both potentiometers, ADS1115, emergency stop, relay, red and green indicators.
- No serial numbers of keys. No terminal that shows `ANTHROPIC_API_KEY`.

## CapCut assembly

1. New project, 1920×1080, 30 fps.
2. Import `docs/explainer/phase3-film/stills/`, the reused figures in `docs/explainer/assets/`, your raw clips, and [`captions.srt`](captions.srt).
3. Follow [shot-list.md](shot-list.md) top to bottom.
4. Ken-Burns stills: scale 100% → 108%, 4–8 seconds, ease in/out.
5. Hard-cut to screen recordings. Do not crossfade UI.
6. Captions: lower centre, Inter or similar, white on a charcoal rounded pill, ~54 pt on a 1080 timeline.
7. Music: light instrumental, −20 dB, duck 6 dB under VO.
8. Export H.264, 1920×1080, 10–16 Mbps, AAC 320 kbps.

## Voiceover

Read [voiceover.md](voiceover.md). One quiet pass is better than many punch-ins. If you split files, name them `VO_01_title.wav` through `VO_10_close.wav` to match the script headings.

## Free stock search list

Use Pexels, Unsplash, or Mixkit. Download the license page with the file. Do not pull frames from the Curastra YouTube video.

| Search | Use at | Avoid |
| --- | --- | --- |
| industrial test bench, laboratory pressure gauge | 00:48 problem | Surgical / hospital footage |
| hydraulic power unit, hose reel, pump skid | 00:48 and 02:50 | Mains switchgear close-ups that imply we certified it |
| PLC cabinet, control panel lights, factory HMI | 01:05 and 03:20 | Brand logos you cannot clear |
| engineer with clipboard on factory floor | 02:20 customer | Faces if you cannot get a model release; prefer over-shoulder |
| automotive battery pack, CAN diagnostics laptop | 03:20 CAN beat | Crash footage |
| water pump / hydrostatic test (wide) | 11:24 mission 4, as *future* | Do not imply the dry bench pumped water |

Illustrated stills already cover the Curastra-style cartoon beats. Stock is cutaway only, a few seconds each.

## Honesty labels (keep these on screen)

- Simulated traces: `simulator`
- 12 September hardware: `Raspberry Pi · 12 Sep 2026`
- Phase 3 UI: `observe only`
- Agent pill: leave it showing `Fake` unless you truly have a live key and say so. Do not fake a Claude or Grok bench run.

## Done when

- Runtime is at most 12 minutes.
- Both demos are in the cut, or the Phase 3 clip is explicitly replaced by a labelled screenshot.
- Grok 4.6, Fake, Claude, and OpenAI are each named once.
- Capstone is deploy-on-any-rig plus the commissioning interview, not a hydraulic plant.
- Final card is `The AI can ask. Only the kernel can say yes.`
