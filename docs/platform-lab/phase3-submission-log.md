# Phase 3 submission log — 17 Sep 2026

Durable record of the submission-assembly instructions and state, kept in the
repo because the GBrain MCP server was unreachable from both the planning
session and this cloud run. Mirror this page into GBrain when it is back
(page suggestion: `certarig/phase3-submission`).

## Operator brief (17 Sep, condensed)

- Recordings delivered: script narration sections 1–5 (5:47), section 6
  narration with irrelevant video (3:38, audio only is used), sections 7–9
  (3:17); screen recording of the live test-bench run (29:34, 2880x1800);
  top-down dry-bench phone recording (29:35, HEVC). A clap is present in both
  long recordings for sync.
- Deliverable 1: the edited Phase 3 submission film. Narration sections over
  the lookbook animations; section 6 narration patched across the synced
  screen recording and top-down bench view; dead time trimmed; every dashboard
  view, agent interaction, and bench state change preserved. 12 min target may
  stretch to 15–18 if needed.
- Deliverable 2: a separate long, uncut video: screen recording and top-down
  view clap-synced and stitched, for its own Google Drive link.
- Deliverable 3: Phase 3 documentation filled from the professor's template
  with all evidence, cross-checked against the professor's meeting brief.
- All heavy work runs in the cloud (operator's laptop has ~6 GB free disk).

## Where everything lives

- Film pack (script, shot list, captions, stills, plates, motion clips):
  `docs/explainer/phase3-film/` on branch `cursor/phase3-submission-edit-c06e`
  (originally built on `cursor/phase3-submission-video-533a`).
- Animations: all 14 motion clips re-rendered on 17 Sep from
  `tools/render_phase3_atelier.py` at current code state; this added the
  previously missing `05b_latch.mp4` and brought stale durations up to date
  (e.g. `05_and_gate` 9.5 s → 18.5 s).
- Edit pipeline: `tools/phase3_edit/` — `fetch_footage.py`, `sync_clap.py`
  (onset-envelope cross-correlation; selftest recovers a known 3.2 s offset
  within 10 ms), `transcribe.py` (faster-whisper word timestamps),
  `assemble.py` (EDL-driven 1080p30 assembly with surface labels and
  captions), `make_uncut.py` (synced main-canvas + picture-in-picture stitch),
  `selftest.py`, and the draft cut list `edl/phase3_film.draft.json`.
- Phase 3 document: `deliverables/phase3-document/` (markdown source,
  `build_docx.py`, evidence index).

## Blocking handoff

The five source recordings exist only on the operator's laptop. The cloud
machine cannot reach them; the operator uploads them once (Google Drive links
with "anyone with link can view", or any direct-download URLs) and provides a
`manifest.json` per `tools/phase3_edit/README.md`. Everything downstream is
scripted and runs here.

## Outcome (17 Sep, cloud run)

- Footage received via Google Drive folder; all five files verified against
  laptop sizes byte-for-byte.
- Clap sync: topdown clock = screen clock + 1.14 s, confirmed on three
  matching transients and by frame inspection (hand mid-clap; Studio Live
  visible at the same instant).
- `out/CertaRig_Phase3_Film.mp4` — 12.7 min, 48 segments per
  `tools/phase3_edit/edl/phase3_film.json`. Sections 1–5 narration over the
  atelier animations, stills, and bench close-ups; section 6 narration
  patched across Studio screen crops (ChatGPT shoot-helper sidebar cropped
  out) and top-down bench zooms at the verified event times (permit ~8:20,
  pressure trip ~12:25, flow trip ~15:40, E-stop cycle ~20:40–21:11, agent
  pressure ~23:44, agent flow ~25:00 on the screen clock); sections 7–9 over
  the capstone clips. Video-model QC passed: continuous voiceover, correct
  visuals per narration, clean captions, no broken cuts, no doubled audio.
- `out/CertaRig_Phase3_Uncut_Bench_Run.mp4` — 29.6 min uncut synced stitch,
  screen recording main canvas + top-down picture-in-picture, top-down audio.
  Sync spot-verified at the pressure raise (hand on pot while the trace
  climbs).
- Both deliverables published as GitHub release
  `phase3-submission-videos-2026-09-17`:
  - Film: https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-2026-09-17/CertaRig_Phase3_Film.mp4
  - Uncut: https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-2026-09-17/CertaRig_Phase3_Uncut_Bench_Run.mp4
- Source footage remains in Drive folder
  https://drive.google.com/drive/folders/1mlegZnq_AQurnBIKY-Ckh1S6TyZ_Q8Bk
  The IDE browser was not signed into Google, so the finished videos were
  published on GitHub rather than uploaded into that folder. Copy the two
  mp4s into Drive if the course portal requires a Drive URL.

## Outcome (18 Sep, v4)

Cloud render of the designed Studio|bench split, then a rebuild of the motion pack after the operator rejected the dark atelier lookbook. Branch `cursor/phase3-film-v4-2e0e`. Selftest PASS (sync −3.21 s within 50 ms; uncut 1920×1080 split pixels; 15.1 s five-segment film including pillarbox and split).

- Footage from Drive folder
  https://drive.google.com/drive/folders/1mlegZnq_AQurnBIKY-Ckh1S6TyZ_Q8Bk
  renamed to `/tmp/certarig_footage/{screen,topdown,narr_1_5,narr_6,narr_7_9}.mov`
  (sizes match the laptop: screen 943 MB, topdown 1.8 GB, narr 223/140/127 MB).
- Clap offset **1.14 s**: `topdown_time = screen_time + 1.14`. Windowed
  `sync_clap.py` (REF=screen) returned −1.14 s (clap onsets screen 3.92 s /
  topdown 5.06 s; pressure-raise window −1.17 s at confidence 5.9). Spot-check
  at screen t=743: Studio Live 3.34 bar climbing, hand on the left pot on the
  aligned top-down frame at 744.14 s. `make_uncut.py --offset -1.14` (the
  signed `sync_clap` value) so the uncut timeline equals the screen clock.
- **Motion rebuild:** `tools/render_phase3_explainer.py` (not
  `render_phase3_atelier.py`). Cream/white paper, teal/gold/ink, Inter, 1920×1080
  30 fps libx264 crf 20, frames piped to ffmpeg stdin. Each clip duration equals
  the spoken beat; reveals use `u = t/dur` across the full length. No LOOKBOOK.
  No `-stream_loop`. Atelier files (dark studio, LOOKBOOK, old 7 s clips) live in
  `docs/explainer/phase3-film/motion/atelier_retired/`. Act A/C in
  `edl/phase3_film_v4.json` are one motion clip per beat; still-fillers removed.
  Live bench + Section 6 split stay as designed. Fake is the proven runtime;
  never imply Grok or Claude tripped the relay.
- Film **13.4 min** (`801 s`) from `tools/phase3_edit/edl/phase3_film_v4.json`
  (45 segments, `--prefix a_/b_/c_`). No LOOKBOOK.mp4. No overlay PiP.
- Uncut **29.6 min** 1310|608 split archive. Action windows **4.5 min**
  (permit 500–517, pressure 730–787, flow 940–975, E-stop 1238–1271,
  agent 1410–1515, evidence 1600–1620 on the screen clock).
- Picture bible: explainer clips play once at native spoken duration; proof
  beats `layout=split` (left Studio 1310×1080 decrease+pad, 2 px charcoal
  gutter, right portrait bench 608×1080 cover-fit); screen crops cards
  `2160:1215:720:66` / graph `2160:1215:720:585` (drops ChatGPT sidebar);
  bench punch-in `1080:1440:0:200` after `transpose=clock:passthrough=portrait`.
  Act A bench is early wiring (~61–111 s) and permit LEDs (~491–527 s), never
  pressure-trip hands (~730+). Trip crossings use live top-down audio. Labels
  fade at 4 s and stay off the Live trace. Honesty: Studio · Raspberry Pi
  sidecar :8081 / Dry bench · Raspberry Pi. Fake ran the bench.
- QC: Act A title frames are cream paper (not the dark atelier room). Act A
  wiring/LED frames show the idle dry bench, no 730 s pot-trip hand. Act B
  pressure-trip split at local t≈8 s is 1920×1080; left pane is the Studio
  graph (4.00 bar, trace at the 4.2 line, Output off, provider fake, no
  ChatGPT sidebar); right pane is a full-height portrait bench with the hand
  on the pressure pot (not a lower-right stamp, not squashed 16:9). Flow-trip
  split similarly shows the climbing flow trace and the hand on the right pot.
  Uncut at t=743 shows both panes alive and clap-synced.
- GitHub release `phase3-submission-videos-v4` (film asset replaced after the
  explainer rebuild):
  - Film: https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Film.mp4
  - Uncut: https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Bench_Run.mp4
  - Action: https://github.com/shadybrook/certarig-platform/releases/download/phase3-submission-videos-v4/CertaRig_Phase3_Uncut_Action.mp4
  - Release page: https://github.com/shadybrook/certarig-platform/releases/tag/phase3-submission-videos-v4
- Drive upload was not available from this VM (same as v1–v3); GitHub is
  the delivery. Source footage remains in the Drive folder above.

## Honesty rails carried into the edit

- Simulator footage is always labelled simulator; hardware is always labelled
  Raspberry Pi. No LLM is said to trip the relay — Fake ran the bench.
- Section 6 lives on the 8081 sidecar (Studio); sections 6A–6C observe the
  frozen Phase 3 dashboard on 8080 only.
- Numbers that must not drift: 4.2 bar / 15 L/min guardrails; 12 Sep peaks
  4.83 bar and 15.41 L/min; 1,291-sample passing sweep after one kept failure;
  six passing hardware runs, 3,422 samples, 34/34 checks; software transitions
  under 1 ms (not mechanical relay latency).
