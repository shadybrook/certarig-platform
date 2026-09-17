#!/usr/bin/env python3
"""Find the time offset between two recordings of the same event via their audio.

Both the screen recording and the top-down phone recording captured the same
room audio, including a deliberate clap. We cross-correlate onset envelopes
(rectified first difference of short-window RMS) rather than raw waveforms so
different microphones, gains, and codecs do not matter.

Usage:
    python3 sync_clap.py REF_VIDEO OTHER_VIDEO [--window-start S] [--window-dur S]

Prints JSON: {"offset_seconds": x, ...} where a positive offset means OTHER
starts x seconds *later* in real time than REF (i.e. to align, trim x seconds
from the head of REF, or delay OTHER by x).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

SR = 8000  # Hz, plenty for a clap transient
HOP = 80   # samples per envelope step -> 10 ms resolution


def extract_audio(video: Path, start: float | None, dur: float | None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(video)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-map", "0:a:0", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def onset_envelope(x: np.ndarray) -> np.ndarray:
    n = len(x) // HOP
    if n == 0:
        raise SystemExit("audio too short")
    rms = np.sqrt(np.mean(x[: n * HOP].reshape(n, HOP) ** 2, axis=1) + 1e-12)
    d = np.diff(rms, prepend=rms[0])
    d[d < 0] = 0.0
    d -= d.mean()
    norm = np.sqrt((d ** 2).sum())
    return d / (norm + 1e-12)


def best_offset(ref: np.ndarray, other: np.ndarray) -> tuple[float, float]:
    n = 1 << int(np.ceil(np.log2(len(ref) + len(other))))
    R = np.fft.rfft(ref, n)
    O = np.fft.rfft(other, n)
    corr = np.fft.irfft(R * np.conj(O), n)
    corr = np.concatenate([corr[-(len(other) - 1):], corr[: len(ref)]])
    lags = np.arange(-(len(other) - 1), len(ref))
    i = int(np.argmax(corr))
    peak = float(corr[i])
    second = float(np.partition(corr, -2)[-2])
    confidence = peak / (abs(second) + 1e-12)
    return float(lags[i]) * HOP / SR, confidence


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", type=Path)
    ap.add_argument("other", type=Path)
    ap.add_argument("--window-start", type=float, default=None,
                    help="only analyze from this time (s) in both files")
    ap.add_argument("--window-dur", type=float, default=None,
                    help="only analyze this many seconds")
    args = ap.parse_args()

    a = onset_envelope(extract_audio(args.ref, args.window_start, args.window_dur))
    b = onset_envelope(extract_audio(args.other, args.window_start, args.window_dur))
    offset, confidence = best_offset(a, b)

    print(json.dumps({
        "ref": str(args.ref),
        "other": str(args.other),
        "offset_seconds": round(offset, 3),
        "meaning": "positive => the shared event appears later on REF's clock "
                   "(REF started earlier); trim max(0, offset) from REF's head "
                   "and max(0, -offset) from OTHER's head to align",
        "confidence_peak_ratio": round(confidence, 2),
        "resolution_seconds": HOP / SR,
    }, indent=2))
    if confidence < 1.5:
        print("WARNING: weak correlation peak; verify with frames", file=sys.stderr)


if __name__ == "__main__":
    main()
