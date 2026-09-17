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
- Both deliverables and a 480p review proxy uploaded as run artifacts for the
  operator to download and place in Google Drive.

## Honesty rails carried into the edit

- Simulator footage is always labelled simulator; hardware is always labelled
  Raspberry Pi. No LLM is said to trip the relay — Fake ran the bench.
- Section 6 lives on the 8081 sidecar (Studio); sections 6A–6C observe the
  frozen Phase 3 dashboard on 8080 only.
- Numbers that must not drift: 4.2 bar / 15 L/min guardrails; 12 Sep peaks
  4.83 bar and 15.41 L/min; 1,291-sample passing sweep after one kept failure;
  six passing hardware runs, 3,422 samples, 34/34 checks; software transitions
  under 1 ms (not mechanical relay latency).
