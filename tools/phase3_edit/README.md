# Phase 3 edit pipeline (cloud)

Everything here runs on the cloud machine — nothing is rendered on the
operator's laptop. Verified end-to-end by `selftest.py` (synthetic footage:
sync recovers a known 3.2 s offset within 50 ms; uncut stitch is a 1920x1080
1310|608 split with a full-height bench pane; EDL assembly builds a ~15 s
five-segment film including `layout=split` and `fit=pillarbox`).

## Inputs (uploaded once from the laptop)

| Canonical name | Source file on the laptop | Length |
| --- | --- | --- |
| `screen` | `~/Desktop/Screen Recording 2026-09-17 at 2.38.56 PM.mov` (2880x1800) | 29:34 |
| `topdown` | `~/Downloads/Dry test bench Top down recording.MOV` (HEVC 1080p) | 29:35 |
| `narr_1_5` | `~/Downloads/Section 1-5 Phase 3  Narration and Script.mov` | 5:47 |
| `narr_6` | `~/Downloads/Section 6 Phase 3 Narration Video In Script.mov` (audio only is used) | 3:38 |
| `narr_7_9` | `~/Downloads/Section 7-9 Phase 3 Narration from Script.mov` | 3:17 |

Canonical files live under `/tmp/certarig_footage/{screen,topdown,narr_1_5,narr_6,narr_7_9}.mov`.
Do not put `LOOKBOOK.mp4` in the film.

Upload path: share the Drive folder as **anyone with the link can view**, then:

```bash
gdown --folder 'https://drive.google.com/drive/folders/1mlegZnq_AQurnBIKY-Ckh1S6TyZ_Q8Bk' \
  -O /tmp/certarig_footage
# rename to the five canonical names above
```

Or, with a file-URL manifest:

```bash
python3 tools/phase3_edit/fetch_footage.py manifest.json --dest /tmp/certarig_footage
```

## Workflow

1. **Fetch** — as above. Probe every file after download.
2. **Sync** — `python3 tools/phase3_edit/sync_clap.py /tmp/certarig_footage/screen.mov
   /tmp/certarig_footage/topdown.mov`. Cross-correlates onset envelopes around
   the clap. Expected offset ≈ **+1.14 s** (`topdown_time = screen_time + 1.14`).
   Verify by extracting a frame from each aligned stream at the clap and at
   screen t=743 (pressure raise: hand on pot + trace climbing).
3. **Transcribe** — `python3 tools/phase3_edit/transcribe.py /tmp/certarig_footage/narr_*.mov
   --out-dir /tmp/certarig_out/transcripts/`. If sentence boundaries differ
   from the EDL audio in/out by more than ~0.4 s, snap the EDL. Do not
   reshuffle act order.
4. **Cut list** — `edl/phase3_film_v4.json`. Act A atelier + stills + early
   wiring/LED bench. Act B clap-synced **Studio | bench split** (left 1310,
   gutter 2, right 608). Trip crossings use `audio=video` (top-down mic).
   Act C gates / records / capstone. Target 14–16 min.
5. **Assemble** — v4 split compositor:

   ```bash
   python3 tools/phase3_edit/assemble.py \
     tools/phase3_edit/edl/phase3_film_v4.json /tmp/certarig_out/actA.mp4 --prefix a_
   python3 tools/phase3_edit/assemble.py \
     tools/phase3_edit/edl/phase3_film_v4.json /tmp/certarig_out/actB.mp4 --prefix b_
   python3 tools/phase3_edit/assemble.py \
     tools/phase3_edit/edl/phase3_film_v4.json /tmp/certarig_out/actC.mp4 --prefix c_
   ```

   Constants: 1920×1080, 30 fps, 48 kHz, `SPLIT_LEFT=1310`, `SPLIT_GUTTER=2`,
   `SPLIT_RIGHT=608`, charcoal `0x101216`. Screen crops are **not** rotated.
   Portrait bench uses `transpose=clock:passthrough=portrait`. Labels fade at
   4 s; captions are omitted on live traces. Loop defaults to false (never
   `-stream_loop`).
6. **Uncut deliverable** — 1310|608 split, not overlay PiP:

   ```bash
   python3 tools/phase3_edit/make_uncut.py \
     /tmp/certarig_footage/screen.mov /tmp/certarig_footage/topdown.mov \
     /tmp/certarig_out/CertaRig_Phase3_Uncut_Bench_Run.mp4 \
     --offset 1.14 --crf 21
   ```

   Screen crop `min(iw,2160):ih:max(0,iw-2160):0` drops the left 720 px
   sidebar on 2880×1800 sources. Top-down is cover-fit 608×1080 with a 2 px
   white rule, overlaid at x=1312. Top-down audio. ~29.6 min.
7. **Review** — 480p proxies and JPEG QC frames (Act A wiring/LED, Act B
   pressure-trip split at local t≈8 s, Act B flow-trip). Left pane must show
   the Studio graph, not the ChatGPT sidebar. Right pane must be a full-height
   bench, not a lower-right stamp.

## Honesty rails (from the film pack — enforced in every caption)

- Never label a simulator trace as hardware; never say an LLM tripped the relay.
- Live clips carry a surface label for their first four seconds:
  `Studio · Raspberry Pi sidecar :8081` or `Dry bench · Raspberry Pi`.
- Labels never sit on the Live trip trace. Fake ran the bench.
- The section 6 recording's video track is discarded; only its narration is
  used, per the operator's instruction.
