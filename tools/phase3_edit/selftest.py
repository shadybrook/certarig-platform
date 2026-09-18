#!/usr/bin/env python3
"""End-to-end smoke test of the Phase 3 v4 edit pipeline with synthetic footage.

Creates two fake recordings of the same event (a clap transient plus tones)
whose files start at different real moments:

  * screen   640x360 steelblue
  * topdown  360x640 darkgreen (portrait)
  * known offset -3.2 s (topdown started first)

Then verifies:
  1. sync_clap.py recovers the known offset within 50 ms,
  2. make_uncut.py produces a 1920x1080 split: left pixel (~400,540) blue,
     right (~1600,540) green, and (1700,980) also green so the bench pane is
     full height rather than a lower-right stamp,
  3. assemble.py builds a ~15 s five-segment film (still, motion, screen,
     pillarbox, split) with the same pillarbox/split pixel checks.

Run: python3 tools/phase3_edit/selftest.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUE_OFFSET = -3.2  # topdown started 3.2 s before the screen recording


def sh(*cmd: str) -> str:
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return r.stdout


def make_source(path: Path, clap_at: float, dur: float, color: str,
                size: str) -> None:
    audio = (
        f"sine=frequency=200:duration={dur},volume=0.05,"
        f"volume=20:enable='between(t,{clap_at},{clap_at + 0.05})'"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"color=c={color}:s={size}:r=30:d={dur}",
         "-f", "lavfi", "-i", audio,
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True)


def grab_frame(video: Path, t: float, dest: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", str(dest)],
        check=True)


def rgb_at(path: Path, x: int, y: int) -> tuple[int, int, int]:
    im = Image.open(path).convert("RGB")
    return im.getpixel((x, y))


def is_blueish(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return b > 90 and b > r + 20 and b >= g


def is_greenish(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g > 50 and g > r + 25 and g > b + 25


def is_dark(rgb: tuple[int, int, int]) -> bool:
    return max(rgb) < 50


def probe_wh(path: Path) -> tuple[int, int]:
    w = int(sh("ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width", "-of", "csv=p=0", str(path)).strip())
    h = int(sh("ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=height", "-of", "csv=p=0", str(path)).strip())
    return w, h


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="phase3_selftest_"))
    screen = tmp / "screen.mp4"
    topdown = tmp / "topdown.mp4"
    make_source(screen, clap_at=5.0, dur=30, color="steelblue", size="640x360")
    make_source(topdown, clap_at=5.0 - TRUE_OFFSET, dur=33, color="darkgreen",
                size="360x640")

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
    uw, uh = probe_wh(uncut)
    assert (uw, uh) == (1920, 1080), f"uncut {uw}x{uh}"
    frame = tmp / "uncut.png"
    grab_frame(uncut, 5.0, frame)
    left = rgb_at(frame, 400, 540)
    right = rgb_at(frame, 1600, 540)
    right_foot = rgb_at(frame, 1700, 980)
    assert is_blueish(left), f"uncut left (400,540) {left} not blue"
    assert is_greenish(right), f"uncut right (1600,540) {right} not green"
    assert is_greenish(right_foot), (
        f"uncut (1700,980) {right_foot} not green — right pane is a stamp, "
        "not full height")
    print(f"PASS make_uncut: {dur:.1f}s 1920x1080 split "
          f"L{left} R{right} foot{right_foot}")

    narration = tmp / "narr.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=16",
                    str(narration)], check=True)
    motion = ROOT / "docs/explainer/phase3-film/motion/02_question.mp4"
    still = ROOT / "docs/explainer/phase3-film/stills/00_title.png"
    edl = {
        "sources": {"screen": str(screen), "topdown": str(topdown),
                    "narr": str(narration)},
        "segments": [
            {"id": "a_title",
             "video": {"still": str(still)},
             "audio": {"src": "narr", "in": 0.0, "out": 3.0},
             "caption": "What is CertaRig?"},
            {"id": "a_motion",
             "video": {"src": str(motion)},
             "audio": "silence", "duration": 3.0},
            {"id": "b_studio",
             "video": {"src": "screen", "in": 2.0, "out": 5.0},
             "audio": {"src": "narr", "in": 3.0, "out": 6.0},
             "label": "Studio · Raspberry Pi sidecar :8081"},
            {"id": "b_pillar",
             "video": {"src": "topdown", "in": 2.0, "out": 5.0,
                       "fit": "pillarbox"},
             "audio": {"src": "narr", "in": 6.0, "out": 9.0},
             "label": "Dry bench · Raspberry Pi"},
            {"id": "c_split",
             "video": {
                 "layout": "split",
                 "left": {"src": "screen", "in": 2.0, "out": 5.0},
                 "right": {"src": "topdown", "in": 5.2, "out": 8.2},
             },
             "audio": {"src": "narr", "in": 9.0, "out": 12.0}},
        ],
    }
    edl_path = tmp / "edl.json"
    edl_path.write_text(json.dumps(edl))
    film = tmp / "film.mp4"
    sh(sys.executable, str(HERE / "assemble.py"), str(edl_path), str(film),
       "--root", str(ROOT))
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "csv=p=0", str(film)).strip())
    assert 14.0 < dur < 16.5, f"film duration {dur} (want ~15 s)"
    fw, fh = probe_wh(film)
    assert (fw, fh) == (1920, 1080), f"film {fw}x{fh}"

    # Prefix filter: only a_ segments (3 s + 3 s).
    film_a = tmp / "film_a.mp4"
    sh(sys.executable, str(HERE / "assemble.py"), str(edl_path), str(film_a),
       "--root", str(ROOT), "--prefix", "a_")
    dur_a = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(film_a)).strip())
    assert 5.5 < dur_a < 6.5, f"prefix a_ duration {dur_a}"

    pillar = tmp / "pillar.png"
    grab_frame(film, 10.5, pillar)  # b_pillar at 9–12 s
    p_center = rgb_at(pillar, 960, 540)
    p_foot = rgb_at(pillar, 960, 980)
    p_side = rgb_at(pillar, 200, 540)
    assert is_greenish(p_center), f"pillarbox center {p_center} not green"
    assert is_greenish(p_foot), f"pillarbox foot {p_foot} not green (not full height)"
    assert is_dark(p_side), f"pillarbox side {p_side} not charcoal pad"

    split = tmp / "split.png"
    grab_frame(film, 13.5, split)  # c_split at 12–15 s
    s_left = rgb_at(split, 400, 540)
    s_right = rgb_at(split, 1600, 540)
    s_foot = rgb_at(split, 1700, 980)
    assert is_blueish(s_left), f"split left {s_left} not blue"
    assert is_greenish(s_right), f"split right {s_right} not green"
    assert is_greenish(s_foot), f"split foot {s_foot} not green — stamp/letterbox"
    print(f"PASS assemble: {dur:.1f}s film, prefix a_ {dur_a:.1f}s")
    print(f"  pillar L-pad{p_side} mid{p_center} foot{p_foot}")
    print(f"  split  L{s_left} R{s_right} foot{s_foot}")
    print(f"all artifacts in {tmp}")


if __name__ == "__main__":
    main()
