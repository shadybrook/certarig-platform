#!/usr/bin/env python3
"""End-to-end smoke test of the Phase 3 edit pipeline with synthetic footage.

Creates two fake recordings of the same 'event track' (a clap transient plus
tones) whose files start at different real moments, then verifies:
  1. sync_clap.py recovers the known offset within 50 ms,
  2. make_uncut.py produces a playable synced side-by-side video,
  3. assemble.py builds a short film from an EDL that mixes a motion clip,
     a still with Ken Burns, and a live sub-clip with narration audio.

Run: python3 tools/phase3_edit/selftest.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUE_OFFSET = -3.2  # topdown started 3.2 s before the screen recording


def sh(*cmd: str) -> str:
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return r.stdout


def make_source(path: Path, clap_at: float, dur: float, color: str) -> None:
    # A sharp 4 kHz burst acts as the clap; low tone elsewhere.
    audio = (
        f"sine=frequency=200:duration={dur},volume=0.05,"
        f"volume=20:enable='between(t,{clap_at},{clap_at + 0.05})'"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"color=c={color}:s=640x360:r=30:d={dur}",
         "-f", "lavfi", "-i", audio,
         "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
         "-shortest", str(path)],
        check=True)


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="phase3_selftest_"))
    screen = tmp / "screen.mp4"
    topdown = tmp / "topdown.mp4"
    # Same real-world clap; the file that started earlier shows it later.
    make_source(screen, clap_at=5.0, dur=30, color="steelblue")
    make_source(topdown, clap_at=5.0 - TRUE_OFFSET, dur=33, color="darkgreen")

    out = json.loads(
        sh(sys.executable, str(HERE / "sync_clap.py"), str(screen), str(topdown)))
    got = out["offset_seconds"]
    assert abs(got - TRUE_OFFSET) < 0.05, f"sync offset {got} != {TRUE_OFFSET}"
    print(f"PASS sync_clap: offset {got}s (expected {TRUE_OFFSET})")

    uncut = tmp / "uncut.mp4"
    sh(sys.executable, str(HERE / "make_uncut.py"), str(screen), str(topdown),
       str(uncut), "--offset", str(got), "--audio", "topdown")
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(uncut)).strip())
    assert 25 < dur < 31, f"uncut duration {dur}"
    print(f"PASS make_uncut: {dur:.1f}s")

    narration = tmp / "narr.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=6",
                    str(narration)], check=True)
    motion = ROOT / "docs/explainer/phase3-film/motion/02_question.mp4"
    still = ROOT / "docs/explainer/phase3-film/stills/00_title.png"
    edl = {
        "sources": {"screen": str(screen), "narr": str(narration)},
        "segments": [
            {"id": "title", "video": {"still": str(still), "kenburns": True},
             "audio": {"src": "narr", "in": 0.0, "out": 3.0},
             "caption": "What is CertaRig?"},
            {"id": "motion", "video": {"src": str(motion)}, "audio": "silence",
             "duration": 3.0},
            {"id": "live", "video": {"src": "screen", "in": 2.0, "out": 6.0},
             "audio": {"src": "narr", "in": 3.0, "out": 6.0},
             "label": "Studio · simulator"},
        ],
    }
    edl_path = tmp / "edl.json"
    edl_path.write_text(json.dumps(edl))
    film = tmp / "film.mp4"
    sh(sys.executable, str(HERE / "assemble.py"), str(edl_path), str(film),
       "--root", str(ROOT))
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(film)).strip())
    assert 8.5 < dur < 10.0, f"film duration {dur}"
    print(f"PASS assemble: {dur:.1f}s film")
    print(f"all artifacts in {tmp}")


if __name__ == "__main__":
    main()
