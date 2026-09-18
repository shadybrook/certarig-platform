#!/usr/bin/env python3
"""Stitch the full screen recording and top-down bench view into one long,
uncut, clap-synchronized 1920x1080 split for the archive upload.

Layout (picture bible v4): 1310 | 2 px charcoal gutter | 608.
- Screen (left): crop ``min(iw,2160):ih:max(0,iw-2160):0`` so a 2880x1800
  Studio capture drops the left 720 px ChatGPT sidebar, while a 640x360
  selftest source is left untouched. Then decrease+pad into 1310x1080.
- Top-down (right): ``transpose=clock:passthrough=portrait``, cover-fit
  608x1080, 2 px white rule, overlaid at x=1312.
- Audio defaults to the top-down mic.

Usage:
    python3 make_uncut.py SCREEN.mov TOPDOWN.mov out.mp4 --offset OFFSET
where OFFSET is sync_clap.py's offset_seconds computed with REF=screen,
OTHER=topdown.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

W, H = 1920, 1080
SPLIT_LEFT = 1310
SPLIT_GUTTER = 2
SPLIT_RIGHT = 608
CHARCOAL = "0x101216"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("screen", type=Path)
    ap.add_argument("topdown", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--offset", type=float, required=True,
                    help="offset_seconds from sync_clap.py (ref=screen, other=topdown)")
    ap.add_argument("--audio", choices=["topdown", "screen", "mix"], default="topdown")
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--preset", default="faster")
    args = ap.parse_args()

    # Align by trimming the head of whichever source started earlier.
    screen_ss = max(0.0, args.offset)
    topdown_ss = max(0.0, -args.offset)
    ox = SPLIT_LEFT + SPLIT_GUTTER

    fc = (
        f"[0:v]crop=min(iw\\,2160):ih:max(0\\,iw-2160):0,"
        f"scale={SPLIT_LEFT}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={SPLIT_LEFT}:{H}:(ow-iw)/2:(oh-ih)/2:color={CHARCOAL},"
        f"fps=30,setsar=1[left];"
        f"[1:v]transpose=clock:passthrough=portrait,"
        f"scale={SPLIT_RIGHT}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={SPLIT_RIGHT}:{H}:(iw-{SPLIT_RIGHT})/2:(ih-{H})/2,"
        f"fps=30,setsar=1,"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=white:t=2[right];"
        f"[left]pad={W}:{H}:0:0:color={CHARCOAL}[canvas];"
        f"[canvas][right]overlay={ox}:0[v]"
    )
    if args.audio == "mix":
        fc += ";[0:a][1:a]amix=inputs=2:duration=shortest,aresample=48000[a]"
    else:
        a_idx = 1 if args.audio == "topdown" else 0
        fc += f";[{a_idx}:a]aresample=48000,aformat=channel_layouts=stereo[a]"

    cmd = [
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-ss", f"{screen_ss:.3f}", "-i", str(args.screen),
        "-ss", f"{topdown_ss:.3f}", "-i", str(args.topdown),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", "-shortest",
        str(args.out),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
