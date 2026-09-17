#!/usr/bin/env python3
"""Stitch the full screen recording and top-down bench view into one long,
uncut, clap-synchronized video for the Google Drive upload.

Layout: the screen recording is the main 1920x1080 canvas (its 16:10 frame is
scaled to fit height and pillarboxed on charcoal); the top-down bench view is a
picture-in-picture panel in the lower-right corner, large enough to read the
relay indicators. Audio comes from the top-down camera by default (best room
sound), switchable with --audio.

Usage:
    python3 make_uncut.py SCREEN.mov TOPDOWN.mov out.mp4 --offset OFFSET
where OFFSET is sync_clap.py's offset_seconds computed with REF=screen,
OTHER=topdown.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("screen", type=Path)
    ap.add_argument("topdown", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--offset", type=float, required=True,
                    help="offset_seconds from sync_clap.py (ref=screen, other=topdown)")
    ap.add_argument("--audio", choices=["topdown", "screen", "mix"], default="topdown")
    ap.add_argument("--pip-width", type=int, default=640)
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--preset", default="faster")
    args = ap.parse_args()

    # Align by trimming the head of whichever source started earlier.
    screen_ss = max(0.0, args.offset)
    topdown_ss = max(0.0, -args.offset)

    pw = args.pip_width
    ph = int(pw * 9 / 16 / 2) * 2

    fc = (
        "[0:v]scale=-2:1080:flags=lanczos,crop='min(iw,1920)':1080,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x16181c,fps=30[main];"
        f"[1:v]scale={pw}:{ph}:flags=lanczos,fps=30,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.35:t=3[pip];"
        "[main][pip]overlay=W-w-24:H-h-24[v]"
    )
    if args.audio == "mix":
        fc += ";[0:a][1:a]amix=inputs=2:duration=shortest,aresample=48000[a]"
        amap = "[a]"
    else:
        amap = "1:a:0" if args.audio == "topdown" else "0:a:0"
        fc += f";[{1 if args.audio == 'topdown' else 0}:a]aresample=48000[a]"
        amap = "[a]"

    cmd = [
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-ss", f"{screen_ss:.3f}", "-i", str(args.screen),
        "-ss", f"{topdown_ss:.3f}", "-i", str(args.topdown),
        "-filter_complex", fc,
        "-map", "[v]", "-map", amap,
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", "-shortest",
        str(args.out),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
