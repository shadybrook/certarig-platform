#!/usr/bin/env python3
"""Transcribe narration files with word-level timestamps (faster-whisper, CPU).

Used to map the recorded voiceover onto the script blocks in
docs/explainer/phase3-film/SCRIPT_EDIT_ME.md so EDL audio in/out points can be
chosen at sentence boundaries, and to locate dead air worth trimming.

Usage:
    python3 transcribe.py AUDIO_OR_VIDEO [...] --out-dir transcripts/
Writes NAME.words.json ([{word, start, end}]) and NAME.txt per input.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def ensure_model():
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "faster-whisper"], check=True)
    from faster_whisper import WhisperModel
    return WhisperModel("small", device="cpu", compute_type="int8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("transcripts"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    model = ensure_model()
    for src in args.inputs:
        segments, _info = model.transcribe(str(src), word_timestamps=True,
                                           vad_filter=True)
        words, lines = [], []
        for seg in segments:
            lines.append(f"[{seg.start:8.2f} – {seg.end:8.2f}] {seg.text.strip()}")
            for w in seg.words or []:
                words.append({"word": w.word, "start": round(w.start, 2),
                              "end": round(w.end, 2)})
        stem = src.stem.replace(" ", "_")
        (args.out_dir / f"{stem}.words.json").write_text(json.dumps(words, indent=1))
        (args.out_dir / f"{stem}.txt").write_text("\n".join(lines) + "\n")
        print(f"{src.name}: {len(words)} words -> {args.out_dir}/{stem}.txt")


if __name__ == "__main__":
    main()
