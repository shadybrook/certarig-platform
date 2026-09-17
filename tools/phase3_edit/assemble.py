#!/usr/bin/env python3
"""EDL-driven assembler for the Phase 3 submission film.

Reads a JSON edit decision list, renders every segment to a uniform
intermediate (1920x1080, 30 fps, H.264 + 48 kHz stereo AAC in MPEG-TS), and
concatenates them into the final MP4.

EDL format (see edl/ for real examples):

{
  "sources": {"screen": "/abs/path.mov", "narr15": "..."},   # aliases
  "segments": [
    {
      "id": "title",
      "video": {"src": "docs/.../01_title.mp4"}                       # clip
             | {"src": "screen", "in": 63.0, "out": 81.5}             # sub-clip
             | {"still": "docs/.../00_title.png", "kenburns": true},  # still
      "audio": {"src": "narr15", "in": 0.0, "out": 20.0}   # narration slice
             | "video"                                     # keep video's audio
             | "silence",
      "duration": 20.0,      # optional; default = audio range, else video range
      "label": "Studio · Raspberry Pi sidecar :8081",   # top-left surface pill
      "caption": "The AI can ask."                      # lower-third caption
    }
  ]
}

Rules: if audio is a narration slice, the segment lasts exactly that slice
(video is trimmed or freeze-extended to fit). Stills get a slow Ken Burns
push-in. Screen-recording sources are scaled to fit and pillarboxed.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

W, H, FPS, SR = 1920, 1080, 30, 48000
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def drawtext(text: str, *, y: str, size: int, boxcolor: str) -> str:
    return (
        f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize={size}:"
        f"fontcolor=white:x=(w-text_w)/2:y={y}:box=1:boxcolor={boxcolor}:"
        "boxborderw=18"
    )


def label_filter(text: str) -> str:
    return (
        f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=30:"
        "fontcolor=white:x=36:y=32:box=1:boxcolor=0x16181cB8:boxborderw=14"
    )


class Assembler:
    def __init__(self, edl: dict, root: Path, tmp: Path):
        self.edl = edl
        self.root = root
        self.tmp = tmp
        self.sources = {k: Path(v) for k, v in edl.get("sources", {}).items()}

    def resolve(self, name: str) -> Path:
        if name in self.sources:
            return self.sources[name]
        p = Path(name)
        return p if p.is_absolute() else self.root / p

    def segment_duration(self, seg: dict) -> float:
        if "duration" in seg:
            return float(seg["duration"])
        audio = seg.get("audio", "silence")
        if isinstance(audio, dict) and "out" in audio:
            return float(audio["out"]) - float(audio.get("in", 0.0))
        video = seg["video"]
        if "src" in video:
            if "out" in video:
                return float(video["out"]) - float(video.get("in", 0.0))
            return ffprobe_duration(self.resolve(video["src"]))
        raise ValueError(f"segment {seg.get('id')}: cannot infer duration")

    def render_segment(self, seg: dict, index: int) -> Path:
        dur = self.segment_duration(seg)
        out = self.tmp / f"seg_{index:03d}_{seg.get('id', 'seg')}.ts"
        video = seg["video"]
        cmd: list[str] = ["ffmpeg", "-y", "-v", "error"]
        vin = 0

        if "still" in video:
            cmd += ["-loop", "1", "-t", f"{dur:.3f}", "-i",
                    str(self.resolve(video["still"]))]
            if video.get("kenburns", True):
                frames = int(dur * FPS) + 1
                vf = (
                    f"scale={W * 2}:-2,"
                    f"zoompan=z='1.02+0.0016*in/{FPS}':"
                    f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:"
                    f"s={W}x{H}:fps={FPS}"
                )
            else:
                vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease," \
                     f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x101216,fps={FPS}"
        else:
            src = self.resolve(video["src"])
            if "in" in video:
                cmd += ["-ss", f"{float(video['in']):.3f}"]
            cmd += ["-i", str(src)]
            crop = f"crop={video['crop']}," if video.get("crop") else ""
            vf = (
                f"{crop}"
                f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x101216,fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration=600"
            )

        vf += ",setsar=1"
        if seg.get("label"):
            vf += "," + label_filter(seg["label"])
        if seg.get("caption"):
            vf += "," + drawtext(seg["caption"], y="h-110", size=40,
                                 boxcolor="0x16181cCC")

        audio = seg.get("audio", "silence")
        if isinstance(audio, dict):
            a_src = self.resolve(audio["src"])
            a_in = float(audio.get("in", 0.0))
            cmd += ["-ss", f"{a_in:.3f}", "-i", str(a_src)]
            amap = f"{vin + 1}:a:0"
            af = f"aresample={SR},apad=whole_dur={dur:.3f}"
        elif audio == "video":
            amap = f"{vin}:a:0"
            af = f"aresample={SR},apad=whole_dur={dur:.3f}"
        else:
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}",
                    "-i", f"anullsrc=r={SR}:cl=stereo"]
            amap = f"{vin + 1}:a:0"
            af = f"aresample={SR}"

        fade = float(seg.get("audio_fade", 0.15))
        if fade > 0:
            af += f",afade=t=out:st={max(0.0, dur - fade):.3f}:d={fade:.3f}"

        cmd += [
            "-filter_complex", f"[{vin}:v]{vf}[v];[{amap}]{af}[a]",
            "-map", "[v]", "-map", "[a]",
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "faster", "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2",
            "-muxdelay", "0", "-muxpreload", "0",
            str(out),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"segment {seg.get('id')} failed:\n{e.stderr}", file=sys.stderr)
            print("cmd:", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
            raise
        print(f"  [{index:03d}] {seg.get('id', '?'):28s} {dur:7.2f}s", flush=True)
        return out

    def run(self, out_path: Path) -> None:
        parts = [self.render_segment(s, i)
                 for i, s in enumerate(self.edl["segments"])]
        concat = self.tmp / "concat.txt"
        concat.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(concat), "-c", "copy", "-movflags", "+faststart",
             str(out_path)],
            check=True)
        total = ffprobe_duration(out_path)
        print(f"wrote {out_path}  ({total / 60:.1f} min)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("edl", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--root", type=Path, default=Path("/workspace"),
                    help="base for relative asset paths")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    edl = json.loads(args.edl.read_text())
    tmp = Path(tempfile.mkdtemp(prefix="phase3_assemble_"))
    print(f"intermediates in {tmp}")
    Assembler(edl, args.root, tmp).run(args.out)
    if not args.keep_temp:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()


if __name__ == "__main__":
    main()
