# Phase 3 edit pipeline (cloud)

Everything here runs on the cloud machine — nothing is rendered on the
operator's laptop. Verified end-to-end by `selftest.py` (synthetic footage:
sync recovered a known 3.2 s offset within 10 ms; uncut stitch and EDL
assembly both produce playable output).

## Inputs (uploaded once from the laptop)

| Canonical name | Source file on the laptop | Length |
| --- | --- | --- |
| `screen` | `~/Desktop/Screen Recording 2026-09-17 at 2.38.56 PM.mov` (2880x1800) | 29:34 |
| `topdown` | `~/Downloads/Dry test bench Top down recording.MOV` (HEVC 1080p) | 29:35 |
| `narr_1_5` | `~/Downloads/Section 1-5 Phase 3  Narration and Script.mov` | 5:47 |
| `narr_6` | `~/Downloads/Section 6 Phase 3 Narration Video In Script.mov` (audio only is used) | 3:38 |
| `narr_7_9` | `~/Downloads/Section 7-9 Phase 3 Narration from Script.mov` | 3:17 |

Upload path: share each file on Google Drive as **anyone with the link can
view**, write the five links into a `manifest.json`
(`{"screen": "https://drive.google.com/file/d/…/view", …}`), then:

```bash
python3 tools/phase3_edit/fetch_footage.py manifest.json --dest /workspace/footage
```

Note: the Desktop filename contains a narrow no-break space (U+202F) before
"PM" — tab-complete it rather than typing it.

## Workflow

1. **Fetch** — `fetch_footage.py` (above). Probes every file after download.
2. **Sync** — `python3 tools/phase3_edit/sync_clap.py footage/screen.mov
   footage/topdown.mov`. Cross-correlates onset envelopes around the clap.
   Positive offset ⇒ trim that much from the screen recording's head;
   negative ⇒ trim from the top-down's head. Verify by extracting a frame from
   each aligned stream at the clap moment.
3. **Transcribe** — `python3 tools/phase3_edit/transcribe.py footage/narr_*.mov
   --out-dir transcripts/`. Word timestamps map the voice onto
   `docs/explainer/phase3-film/SCRIPT_EDIT_ME.md` blocks and expose dead air.
4. **Cut decisions** — fill the `0.0` placeholders in
   `edl/phase3_film.draft.json`: narration in/out at sentence boundaries, live
   `screen`/`topdown` windows chosen after reviewing the synced footage
   (apply the sync offset to top-down timecodes so both use the screen clock).
   Trim waiting/scrolling; keep every trip crossing, kernel event, evidence
   view, and relay state change. Target 12–18 minutes.
5. **Assemble** — `python3 tools/phase3_edit/assemble.py
   edl/phase3_film.json out/CertaRig_Phase3_Film.mp4`. Renders each segment to
   a uniform 1080p30 intermediate and concatenates. Labels and captions are
   drawn per segment (surface pills top-left, captions lower third).
6. **Uncut deliverable** — `python3 tools/phase3_edit/make_uncut.py
   footage/screen.mov footage/topdown.mov out/CertaRig_Phase3_Uncut_Bench_Run.mp4
   --offset <from step 2>`. Full ~29.6 min, screen recording as the main
   canvas with the top-down bench as a picture-in-picture panel, top-down
   audio. CRF 21 keeps it under 2 GB.
7. **Review** — generate a 480p proxy (`ffmpeg -i out/… -vf scale=854:-2 -crf
   30 proxy.mp4`) and a cut-list summary for operator review before final
   delivery to Google Drive.

## Honesty rails (from the film pack — enforced in every caption)

- Never label a simulator trace as hardware; never say an LLM tripped the relay.
- Live clips carry a surface label for their first seconds:
  `Phase 3 dashboard · port 8080 · observe only` or `Studio · Raspberry Pi
  sidecar :8081`.
- The section 6 recording's video track is discarded; only its narration is
  used, per the operator's instruction.
