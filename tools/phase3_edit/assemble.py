#!/usr/bin/env python3
"""EDL-driven assembler for the Phase 3 v4 submission film.

Renders every segment to a uniform 1920x1080 30 fps intermediate (H.264 +
48 kHz stereo AAC in MPEG-TS) and concatenates. Picture bible:

- Stills: ``-loop 1`` on the image input. No Ken Burns unless requested.
- Explainer clips play once at native speed (never ``-stream_loop``). Freeze
  the last frame with tpad if the audio slice is longer than the clip.
- ``fit=pillarbox``: rotate portrait sources with
  ``transpose=clock:passthrough=portrait``, optional crop, then decrease+pad
  into 1920x1080. Do **not** rotate Studio / screen crops.
- ``layout=split``: left Studio 1310x1080 decrease+pad; 2 px charcoal gutter;
  right portrait bench 608x1080 cover-fit + 2 px white rule, overlaid at
  x=1312. Never stretch (no ``force_original_aspect_ratio=disable``).
- ``audio=video`` on a split uses the right pane (top-down mic). Labels
  fade at 4 s and are omitted on live (audio=video) traces. Captions only
  when the segment is not live.

Usage:
    python3 assemble.py edl/phase3_film_v4.json out/actA.mp4 --prefix a_
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
SPLIT_LEFT = 1310
SPLIT_GUTTER = 2
SPLIT_RIGHT = 608
CHARCOAL = "0x101216"
LABEL_FADE_S = 4.0
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
FONT = next((p for p in FONT_CANDIDATES if Path(p).exists()), "")


def _has_drawtext() -> bool:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        capture_output=True, text=True).stdout
    return "drawtext" in out


HAS_DRAWTEXT = _has_drawtext()


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def esc(text: str) -> str:
    return (text.replace("\\", "\\\\")
                .replace(":", "\\:")
                .replace("'", "\\'")
                .replace(",", "\\,"))


def drawtext(text: str, *, y: str, size: int, boxcolor: str,
             fade: bool = False) -> str:
    # Commas inside expressions must be escaped so they do not split the
    # filtergraph.
    extra = ""
    if fade:
        extra = (
            f":alpha='if(lt(t\\,{LABEL_FADE_S - 0.5})\\,1\\,"
            f"max(0\\,{LABEL_FADE_S}-t)/0.5)'"
        )
    return (
        f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize={size}:"
        f"fontcolor=white:x=(w-text_w)/2:y={y}:box=1:boxcolor={boxcolor}:"
        f"boxborderw=18{extra}"
    )


def label_filter(text: str) -> str:
    return (
        f"drawtext=fontfile={FONT}:text='{esc(text)}':fontsize=30:"
        "fontcolor=white:x=36:y=32:box=1:boxcolor=0x16181cB8:boxborderw=14:"
        f"alpha='if(lt(t\\,{LABEL_FADE_S - 0.5})\\,1\\,"
        f"max(0\\,{LABEL_FADE_S}-t)/0.5)'"
    )


def write_overlay_png(path: Path, label: str | None, caption: str | None) -> None:
    """Caption/label overlay for ffmpeg builds without libfreetype/drawtext."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font_label = ImageFont.truetype(FONT, 30) if FONT else ImageFont.load_default()
        font_cap = ImageFont.truetype(FONT, 40) if FONT else ImageFont.load_default()
    except OSError:
        font_label = font_cap = ImageFont.load_default()

    def pill(text: str, xy: tuple[int, int], font, *, center: bool) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 18, 14
        if center:
            x = (W - tw) // 2 - pad_x
            y = xy[1]
        else:
            x, y = xy
        draw.rounded_rectangle(
            (x, y, x + tw + 2 * pad_x, y + th + 2 * pad_y),
            radius=10, fill=(22, 24, 28, 196))
        draw.text((x + pad_x, y + pad_y), text, font=font, fill=(255, 255, 255, 255))

    if label:
        pill(label, (36, 32), font_label, center=False)
    if caption:
        pill(caption, (0, H - 110), font_cap, center=True)
    img.save(path)


def fit_filter(tw: int, th: int, *, crop: str | None = None,
               rotate: bool = False, cover: bool = False) -> str:
    """Build a scale/pad (or cover-crop) chain. Never stretch."""
    parts: list[str] = []
    if rotate:
        parts.append("transpose=clock:passthrough=portrait")
    if crop:
        parts.append(f"crop={crop}")
    if cover:
        parts.append(
            f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={tw}:{th}:(iw-{tw})/2:(ih-{th})/2"
        )
    else:
        parts.append(
            f"scale={tw}:{th}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color={CHARCOAL}"
        )
    parts.append(f"fps={FPS}")
    parts.append("setsar=1")
    parts.append("tpad=stop_mode=clone:stop_duration=600")
    return ",".join(parts)


def is_split(video: dict) -> bool:
    return video.get("layout") == "split" or "left" in video and "right" in video


def is_live(seg: dict) -> bool:
    return seg.get("audio") == "video"


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

    def _span(self, spec: dict) -> float | None:
        if "out" in spec:
            return float(spec["out"]) - float(spec.get("in", 0.0))
        return None

    def segment_duration(self, seg: dict) -> float:
        if "duration" in seg:
            return float(seg["duration"])
        audio = seg.get("audio", "silence")
        if isinstance(audio, dict) and "out" in audio:
            return float(audio["out"]) - float(audio.get("in", 0.0))
        video = seg["video"]
        if is_split(video):
            span = self._span(video.get("left", {}))
            if span is not None:
                return span
        if "still" in video:
            raise ValueError(f"segment {seg.get('id')}: still needs duration or audio out")
        if "src" in video:
            span = self._span(video)
            if span is not None:
                return span
            return ffprobe_duration(self.resolve(video["src"]))
        raise ValueError(f"segment {seg.get('id')}: cannot infer duration")

    def _add_video_input(self, cmd: list[str], spec: dict, dur: float) -> None:
        src = self.resolve(spec["src"])
        if "in" in spec:
            cmd += ["-ss", f"{float(spec['in']):.3f}"]
        # Never -stream_loop. A finite -t on the input keeps ffmpeg from
        # reading the rest of a 30-minute recording.
        cmd += ["-t", f"{dur + 1.0:.3f}", "-i", str(src)]

    def _text_filters(self, seg: dict) -> list[str]:
        live = is_live(seg)
        parts: list[str] = []
        label = None if live else seg.get("label")
        caption = None if live else seg.get("caption")
        if HAS_DRAWTEXT:
            if label:
                parts.append(label_filter(label))
            if caption:
                parts.append(drawtext(caption, y="h-110", size=40,
                                      boxcolor="0x16181cCC"))
        return parts

    def render_segment(self, seg: dict, index: int) -> Path:
        dur = self.segment_duration(seg)
        out = self.tmp / f"seg_{index:03d}_{seg.get('id', 'seg')}.ts"
        video = seg["video"]
        audio = seg.get("audio", "silence")
        cmd: list[str] = ["ffmpeg", "-y", "-v", "error"]
        chains: list[str] = []
        next_in = 0

        if "still" in video:
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}",
                    "-i", str(self.resolve(video["still"]))]
            still_i = next_in
            next_in += 1
            if video.get("kenburns"):
                frames = int(dur * FPS) + 1
                vf = (
                    f"scale={W * 2}:-2,"
                    f"zoompan=z='1.02+0.0016*in/{FPS}':"
                    f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:"
                    f"s={W}x{H}:fps={FPS},setsar=1"
                )
            else:
                vf = fit_filter(W, H, rotate=False, cover=False)
            chains.append(f"[{still_i}:v]{vf}[base]")
        elif is_split(video):
            left, right = video["left"], video["right"]
            self._add_video_input(cmd, left, dur)
            i_left = next_in
            next_in += 1
            self._add_video_input(cmd, right, dur)
            i_right = next_in
            next_in += 1
            left_vf = fit_filter(
                SPLIT_LEFT, H, crop=left.get("crop"), rotate=False, cover=False)
            right_vf = fit_filter(
                SPLIT_RIGHT, H, crop=right.get("crop"), rotate=True, cover=True)
            right_vf += ",drawbox=x=0:y=0:w=iw:h=ih:color=white:t=2"
            ox = SPLIT_LEFT + SPLIT_GUTTER
            chains.append(f"[{i_left}:v]{left_vf}[L]")
            chains.append(f"[{i_right}:v]{right_vf}[R]")
            chains.append(f"[L]pad={W}:{H}:0:0:color={CHARCOAL}[canvas]")
            chains.append(f"[canvas][R]overlay={ox}:0[base]")
        else:
            self._add_video_input(cmd, video, dur)
            i_v = next_in
            next_in += 1
            rotate = video.get("fit") == "pillarbox"
            vf = fit_filter(
                W, H, crop=video.get("crop"), rotate=rotate, cover=False)
            chains.append(f"[{i_v}:v]{vf}[base]")

        amap: str
        af: str
        if isinstance(audio, dict):
            a_src = self.resolve(audio["src"])
            a_in = float(audio.get("in", 0.0))
            cmd += ["-ss", f"{a_in:.3f}", "-t", f"{dur:.3f}", "-i", str(a_src)]
            amap = f"{next_in}:a:0"
            next_in += 1
            af = f"aresample={SR},aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}"
        elif audio == "video":
            # Split: right pane is top-down and carries the room mic.
            # Single-source live: the (only) video input is 0.
            a_idx = 1 if is_split(video) else 0
            amap = f"{a_idx}:a:0"
            af = f"aresample={SR},aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}"
        else:
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}",
                    "-i", f"anullsrc=r={SR}:cl=stereo"]
            amap = f"{next_in}:a:0"
            next_in += 1
            af = f"aresample={SR}"

        live = is_live(seg)
        label = None if live else seg.get("label")
        caption = None if live else seg.get("caption")
        overlay_idx = None
        if not HAS_DRAWTEXT and (label or caption):
            png = self.tmp / f"ov_{index:03d}.png"
            write_overlay_png(png, label, caption)
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}",
                    "-i", str(png)]
            overlay_idx = next_in
            next_in += 1

        fade = float(seg.get("audio_fade", 0.0 if live else 0.15))
        if fade > 0:
            af += f",afade=t=out:st={max(0.0, dur - fade):.3f}:d={fade:.3f}"

        text_bits = self._text_filters(seg)
        if overlay_idx is not None:
            # Fade the whole pill overlay off at 4 s when it is only a label.
            fade_ov = (
                f"format=rgba,fade=t=out:st={LABEL_FADE_S - 0.5:.2f}:"
                f"d=0.5:alpha=1"
                if label and not caption else "format=rgba"
            )
            chains.append(f"[{overlay_idx}:v]{fade_ov}[ov]")
            chains.append("[base][ov]overlay=0:0[v]")
        elif text_bits:
            chains.append("[base]" + ",".join(text_bits) + "[v]")
        else:
            chains.append("[base]copy[v]")
        chains.append(f"[{amap}]{af}[a]")
        fc = ";".join(chains)

        cmd += [
            "-filter_complex", fc,
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

    def run(self, out_path: Path, *, prefix: str = "") -> None:
        segs = self.edl["segments"]
        if prefix:
            segs = [s for s in segs if str(s.get("id", "")).startswith(prefix)]
            if not segs:
                raise SystemExit(f"no segments with prefix {prefix!r}")
            print(f"{len(segs)} segments with prefix {prefix!r}")
        parts = [self.render_segment(s, i) for i, s in enumerate(segs)]
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
    ap.add_argument("--prefix", default="",
                    help="only render segments whose id starts with this (a_ / b_ / c_)")
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    edl = json.loads(args.edl.read_text())
    tmp = Path(tempfile.mkdtemp(prefix="phase3_assemble_"))
    print(f"intermediates in {tmp}")
    Assembler(edl, args.root, tmp).run(args.out, prefix=args.prefix)
    if not args.keep_temp:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()


if __name__ == "__main__":
    main()
