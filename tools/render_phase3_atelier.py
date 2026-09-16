#!/usr/bin/env python3
"""
CertaRig Phase 3 lookbook — atelier renderer.

One dark studio. Photographic plates. Motion that explains.
No grids, no chapter chrome, no presentation cards.

Rebuild:
    python3 tools/render_phase3_atelier.py --proof
    python3 tools/render_phase3_atelier.py
"""

from __future__ import annotations

import math
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATES = ROOT / "docs" / "explainer" / "phase3-film" / "plates"
OUT = ROOT / "docs" / "explainer" / "phase3-film" / "motion"
PROOF = ROOT / "docs" / "explainer" / "phase3-film" / "motion" / "proof"

FONT = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
FONT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"
FONT_SEMI = "/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf"
FONT_ITAL = "/usr/share/fonts/truetype/macos/Inter-Italic.ttf"

W, H, FPS = 1920, 1080, 30

# Quiet studio grade — warm, never neon.
BG = (7, 7, 8)
WARM = (236, 228, 214)
MUTED = (148, 140, 128)
DIM = (92, 86, 80)
TEAL = (86, 168, 154)
TEAL_GLOW = (120, 214, 196)
RED = (186, 70, 60)
AMBER = (196, 150, 88)
GLASS = (186, 198, 210)
PIN = (198, 196, 190)


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def smooth(t: float) -> float:
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def smoother(t: float) -> float:
    t = clamp(t)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def appear(t: float, start: float, dur: float = 1.1) -> float:
    return smoother((t - start) / dur)


def hold(t: float, start: float, fade: float = 1.1) -> float:
    return appear(t, start, fade)


def fade_out(t: float, end: float, dur: float = 0.8) -> float:
    return smoother((end - t) / dur)


@lru_cache(maxsize=32)
def face(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {
        "regular": FONT,
        "medium": FONT_MED,
        "semi": FONT_SEMI,
        "italic": FONT_ITAL,
    }[weight]
    return ImageFont.truetype(path, size=size)


@lru_cache(maxsize=8)
def plate(name: str, width: int = 2400, height: int = 1350) -> Image.Image:
    src = Image.open(PLATES / name).convert("RGB")
    return src.resize((width, height), Image.Resampling.LANCZOS)


def ken(
    src: Image.Image,
    t: float,
    dur: float,
    scale0: float,
    scale1: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> Image.Image:
    u = smoother(t / max(dur, 0.001))
    scale = lerp(scale0, scale1, u)
    px = lerp(x0, x1, u)
    py = lerp(y0, y1, u)
    cw = min(src.width, max(8, int(W / scale)))
    ch = min(src.height, max(8, int(H / scale)))
    max_x = max(0, src.width - cw)
    max_y = max(0, src.height - ch)
    x = int(max_x * clamp(px))
    y = int(max_y * clamp(py))
    crop = src.crop((x, y, x + cw, y + ch))
    if crop.size != (W, H):
        crop = crop.resize((W, H), Image.Resampling.BICUBIC)
    return crop


def black() -> Image.Image:
    return Image.new("RGB", (W, H), BG)


def mix_images(a: Image.Image, b: Image.Image, t: float) -> Image.Image:
    t = clamp(t)
    if t <= 0.004:
        return a
    if t >= 0.996:
        return b
    na = np.asarray(a, dtype=np.float32)
    nb = np.asarray(b, dtype=np.float32)
    out = na + (nb - na) * t
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def rgba(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int, int]:
    return (*color, int(255 * clamp(alpha)))


def tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, ...],
    tracking: float = 0.0,
    align: str = "left",
) -> None:
    if not text:
        return
    x, y = xy
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    if align == "center":
        x -= total / 2.0
    elif align == "right":
        x -= total
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def measure_tracked(text: str, font: ImageFont.FreeTypeFont, tracking: float = 0.0) -> float:
    probe = ImageDraw.Draw(Image.new("L", (8, 8)))
    if not text:
        return 0.0
    widths = [probe.textlength(ch, font=font) for ch in text]
    return sum(widths) + tracking * max(0, len(text) - 1)


def overlay(base: Image.Image, painter: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    painter(ImageDraw.Draw(layer))
    if base.mode != "RGBA":
        base = base.convert("RGBA")
    return Image.alpha_composite(base, layer).convert("RGB")


def glow_disk(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    alpha: float,
    rings: int = 8,
) -> None:
    if alpha <= 0.01:
        return
    x, y = xy
    for i in range(rings, 0, -1):
        u = i / rings
        r = radius * (0.35 + 1.8 * u)
        a = alpha * (0.035 / u)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=rgba(color, a))
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=rgba(mix_rgb(color, (255, 255, 255), 0.35), alpha),
    )


GRAIN = np.random.default_rng(12).integers(-7, 8, (H, W, 1), dtype=np.int16)


def grade(image: Image.Image, frame_index: int) -> Image.Image:
    arr = np.asarray(image, dtype=np.int16)
    shift = frame_index % 97
    grain = np.roll(GRAIN, shift, axis=1)
    arr = arr + grain
    # Soft vignette so type and objects sit in the same room.
    yy = np.linspace(-1.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(-1.12, 1.12, W, dtype=np.float32)[None, :]
    vig = np.clip(1.0 - 0.18 * (xx * xx + yy * yy), 0.72, 1.0)
    arr = (arr.astype(np.float32) * vig[..., None]).astype(np.int16)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def encode(path: Path, duration: float, painter: Callable[[float], Image.Image]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(round(duration * FPS)))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for index in range(frames):
        t = index / FPS
        image = grade(painter(t), index)
        proc.stdin.write(image.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")
    print(f"wrote {path.relative_to(ROOT)}  ({duration:.1f}s)", flush=True)


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def scene_object(t: float) -> Image.Image:
    img = ken(plate("plate_bench.png"), t, 8.0, 1.06, 1.20, 0.02, 0.42, 0.78, 0.38)

    def paint(draw: ImageDraw.ImageDraw) -> None:
        a0 = appear(t, 2.1, 1.4) * fade_out(t, 8.0, 0.9)
        tracked(
            draw, (160, 250), "CERTARIG", face(15, "medium"),
            rgba(MUTED, a0 * 0.9), tracking=14, align="left",
        )
        a1 = appear(t, 3.6, 1.6) * fade_out(t, 8.0, 0.9)
        draw.text(
            (160, 300),
            "What is this allowed to do?",
            font=face(44),
            fill=rgba(WARM, a1),
        )

    return overlay(img, paint)


def scene_question(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 7.5, 1.04, 1.12, 0.5, 0.55, 0.5, 0.42)

    def paint(draw: ImageDraw.ImageDraw) -> None:
        a = appear(t, 0.6, 1.6) * fade_out(t, 7.5, 1.0)
        draw.text(
            (W / 2, 400),
            "Who may turn this on?",
            font=face(56),
            fill=rgba(WARM, a),
            anchor="mm",
        )
        left = appear(t, 3.4, 1.2) * fade_out(t, 7.5, 0.8)
        right = appear(t, 4.4, 1.2) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (560, 560), "the agent can ask", face(20),
            rgba(MUTED, left * 0.85), tracking=3, align="center",
        )
        tracked(
            draw, (1360, 560), "the kernel can say yes", face(20),
            rgba(TEAL, right), tracking=3, align="center",
        )
        glow_disk(draw, (1360, 548), 4, TEAL, right * 0.9, rings=5)

    return overlay(img, paint)


def scene_glass(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 9.5, 1.02, 1.08, 0.48, 0.5, 0.52, 0.46)
    wall_x = 1128
    phrase = "run it, maybe five, looks fine."
    font = face(40, "italic")
    tracking = 1.0
    phrase_w = measure_tracked(phrase, font, tracking)
    travel = smoother(clamp((t - 0.5) / 3.2))
    hit_t = 3.7
    crossed = t >= hit_t
    rest = clamp((t - hit_t) / 2.8) if crossed else 0.0
    base_x = lerp(160, wall_x - phrase_w - 18, travel if not crossed else 1.0)
    y0 = 470

    def paint(draw: ImageDraw.ImageDraw) -> None:
        ga = appear(t, 0.15, 1.0)
        for i in range(36):
            x = wall_x - 18 + i
            a = ga * (0.018 + 0.10 * math.sin(i / 36 * math.pi))
            draw.line((x, 140, x, 920), fill=rgba(GLASS, a), width=1)
        draw.line((wall_x, 160, wall_x, 900), fill=rgba(WARM, ga * 0.5), width=2)
        draw.line((wall_x + 2, 240, wall_x + 2, 430), fill=rgba((255, 255, 255), ga * 0.28), width=1)
        tracked(
            draw, (wall_x, 112), "4.2 bar", face(16, "medium"),
            rgba(WARM, ga * 0.9), tracking=6, align="center",
        )

        if not crossed:
            a = appear(t, 0.35, 0.9)
            tracked(draw, (base_x, y0), phrase, font, rgba(WARM, a), tracking)
            tracked(
                draw, (wall_x + 16, y0), phrase, font,
                rgba(GLASS, a * 0.10), tracking,
            )
        else:
            x = base_x
            for i, ch in enumerate(phrase):
                rng = math.sin(i * 12.9898 + 78.233) * 43758.5453
                rng = rng - math.floor(rng)
                wch = draw.textlength(ch, font=font)
                dy = (24 + 210 * rng) * smoother(rest)
                # Letters die in place and fall. They do not cross.
                alpha = 0.92 * (1.0 - smoother(rest * 0.9))
                draw.text((x, y0 + dy), ch, font=font, fill=rgba(WARM, alpha))
                if x + wch > wall_x - 36:
                    smear = 0.35 * (1.0 - smoother(rest * 0.7))
                    draw.text(
                        (wall_x + 6, y0 + dy * 1.15),
                        ch, font=font, fill=rgba(GLASS, smear),
                    )
                x += wch + tracking

        late = appear(t, 6.2, 1.3) * fade_out(t, 9.5, 0.8)
        tracked(
            draw, (560, 900), "A sentence cannot cross a number.",
            face(22), rgba(WARM, late * 0.85), tracking=1.5, align="center",
        )

    return overlay(img, paint)


def _pressure_at(t: float) -> float:
    noise = 0.028 * math.sin(t * 17.1) + 0.016 * math.sin(t * 39.4 + 0.6)
    if t < 2.0:
        base = 1.12
    elif t < 7.4:
        u = smoother((t - 2.0) / 5.4)
        base = 1.12 + 3.96 * u
    elif t < 13.2:
        u = smoother((t - 7.4) / 5.8)
        base = 5.08 - 3.76 * u
    else:
        base = 1.32
    return max(0.35, base + noise)


def _trip_time() -> float:
    # First frame the analog value crosses the glass.
    t = 2.0
    while t < 8.0:
        if _pressure_at(t) >= 4.2:
            return t
        t += 1.0 / FPS
    return 6.7


TRIP_T = _trip_time()


def scene_pressure(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 18.5, 1.01, 1.06, 0.5, 0.5, 0.5, 0.48)
    p = _pressure_at(t)
    tripped = t >= TRIP_T
    lamp_on = appear(t, 1.3, 0.5) > 0.4 and not tripped

    plot = (200, 250, 1420, 780)
    pl, pt, pr, pb = plot
    pw, ph = pr - pl, pb - pt
    dur = 18.5

    def y_of(bar: float) -> float:
        return pb - (clamp(bar / 6.0) * ph)

    samples = max(2, int(t * 72))
    pts: list[tuple[float, float]] = []
    n = max(1, int(dur * 72))
    for i in range(samples + 1):
        ts = dur * (i / n)
        if ts > t:
            break
        x = pl + (ts / dur) * pw
        pts.append((x, y_of(_pressure_at(ts))))

    def paint(draw: ImageDraw.ImageDraw) -> None:
        bezel = appear(t, 0.15, 1.0)
        y42 = y_of(4.2)
        flash = 1.0
        if tripped and t < TRIP_T + 0.55:
            flash = 1.0 + 0.7 * (1.0 - (t - TRIP_T) / 0.55)
        draw.line((pl, y42, pr + 40, y42), fill=rgba(WARM, bezel * 0.38 * flash), width=2)
        tracked(
            draw, (pr + 56, y42 - 11), "4.2 bar", face(16, "medium"),
            rgba(WARM, bezel * 0.85), tracking=3, align="left",
        )
        draw.line((pl, pb, pr, pb), fill=rgba(DIM, bezel * 0.28), width=1)
        tracked(
            draw, (pl, 200), "PRESSURE", face(13, "medium"),
            rgba(MUTED, bezel * 0.75), tracking=6, align="left",
        )

        if len(pts) >= 2:
            ta = appear(t, 0.8, 0.6)
            draw.line(pts, fill=rgba(TEAL, ta * 0.16), width=10)
            draw.line(pts, fill=rgba(TEAL_GLOW, ta * 0.5), width=4)
            draw.line(pts, fill=rgba((232, 246, 240), ta), width=2)
            x, y = pts[-1]
            glow_disk(draw, (x, y), 5.0, TEAL_GLOW, ta * 0.85, rings=6)

        ra = appear(t, 0.9, 0.7)
        draw.text((pl, 860), f"{p:0.2f}  bar", font=face(32, "medium"), fill=rgba(WARM, ra))
        if tripped:
            la = appear(t, TRIP_T, 0.35)
            tracked(
                draw, (pl + 220, 872), "latched", face(16, "medium"),
                rgba(RED, la), tracking=4, align="left",
            )

        lx, ly = 1660, 400
        la = appear(t, 1.2, 0.7)
        if lamp_on:
            glow_disk(draw, (lx, ly), 26, TEAL_GLOW, la, rings=11)
        else:
            glow_disk(draw, (lx, ly), 9, RED if tripped else DIM, la * 0.6, rings=6)
            draw.ellipse((lx - 11, ly - 11, lx + 11, ly + 11), outline=rgba(DIM, la * 0.75), width=2)
        tracked(
            draw, (lx, 478), "output", face(14),
            rgba(MUTED, la * 0.9), tracking=4, align="center",
        )
        tracked(
            draw, (lx, 504), "on" if lamp_on else "safe", face(18, "medium"),
            rgba(TEAL if lamp_on else RED, la), tracking=2, align="center",
        )

        pin_a = appear(t, 1.4, 0.6)
        drop = 0.0 if not tripped else smoother(clamp((t - TRIP_T) / 0.32))
        well = (1646, 590, 1674, 730)
        draw.rounded_rectangle(well, radius=3, outline=rgba(DIM, pin_a * 0.8), width=1)
        pin_y = 598 + 78 * drop
        draw.rounded_rectangle((1650, pin_y, 1670, pin_y + 52), radius=2, fill=rgba(PIN, pin_a))
        tracked(
            draw, (lx, 760), "stays down", face(13),
            rgba(MUTED, appear(t, TRIP_T + 1.4, 1.1) * 0.9),
            tracking=3, align="center",
        )

        late = appear(t, 14.2, 1.5) * fade_out(t, 18.5, 0.9)
        tracked(
            draw, (W / 2, 980),
            "Returning to normal does not restart it.",
            face(22), rgba(WARM, late * 0.95), tracking=1.2, align="center",
        )

    return overlay(img, paint)


def scene_latch(t: float) -> Image.Image:
    img = ken(plate("plate_relay_macro.png"), t, 7.5, 1.08, 1.22, 0.28, 0.55, 0.18, 0.62)

    def paint(draw: ImageDraw.ImageDraw) -> None:
        a = appear(t, 2.2, 1.6) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (96, 880),
            "It stays down until a person resets it.",
            face(24), rgba(WARM, a), tracking=1.0, align="left",
        )

    return overlay(img, paint)


def scene_architecture(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 8.5, 1.03, 1.10, 0.5, 0.62, 0.5, 0.48)
    stations = [
        (400, 730, "Operator"),
        (760, 660, "Agent"),
        (1140, 590, "Kernel"),
        (1500, 530, "Rig"),
    ]
    # Light may reach the kernel. It is not allowed to reach the rig.
    u = smoother(clamp((t - 1.1) / 4.8)) * 0.68

    def pos(s: float) -> tuple[float, float]:
        s = clamp(s)
        n = len(stations) - 1
        f = s * n
        i = min(int(f), n - 1)
        k = f - i
        x = lerp(stations[i][0], stations[i + 1][0], k)
        y = lerp(stations[i][1], stations[i + 1][1], k)
        return x, y

    def paint(draw: ImageDraw.ImageDraw) -> None:
        rail = appear(t, 0.3, 1.0)
        pts = [(s[0], s[1]) for s in stations]
        draw.line(pts, fill=rgba(DIM, rail * 0.55), width=2)
        # Glass notch before Rig
        gx, gy = 1320, 560
        draw.line((gx, gy - 48, gx, gy + 48), fill=rgba(WARM, rail * 0.45), width=2)

        for i, (x, y, name) in enumerate(stations):
            reached = u * 3 >= i - 0.05
            a = appear(t, 0.8 + i * 0.55, 0.7)
            on = reached and i < 3
            glow_disk(draw, (x, y), 6 if on else 3.5, TEAL if on else DIM, a * (0.85 if on else 0.35), rings=6)
            tracked(
                draw, (x, y + 28), name, face(16, "medium"),
                rgba(WARM if on or i < 3 else DIM, a * (0.9 if i < 3 else 0.4)),
                tracking=3, align="center",
            )

        hx, hy = pos(u)
        glow_disk(draw, (hx, hy), 11, TEAL_GLOW, appear(t, 1.1, 0.6), rings=8)

        late = appear(t, 5.6, 1.3) * fade_out(t, 8.5, 0.8)
        tracked(
            draw, (W / 2, 200),
            "The agent can ask.  Only the kernel can say yes.",
            face(22), rgba(WARM, late * 0.9), tracking=1.2, align="center",
        )

    return overlay(img, paint)


def scene_desks(t: float) -> Image.Image:
    img = ken(plate("plate_desks.png"), t, 8.5, 1.08, 1.13, 0.18, 0.42, 0.48, 0.36)
    labels = [
        (0.9, 330, 640, "a dry bench"),
        (2.4, 780, 360, "an industrial PC"),
        (3.9, 1600, 400, "a laptop on their bus"),
    ]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        for start, x, y, name in labels:
            a = appear(t, start, 1.1) * fade_out(t, 8.5, 0.8)
            glow_disk(draw, (x, y), 7, AMBER, a * 0.55, rings=6)
            tracked(
                draw, (x, y + 22), name, face(16),
                rgba(WARM, a * 0.9), tracking=1.5, align="center",
            )
        late = appear(t, 5.4, 1.4) * fade_out(t, 8.5, 0.8)
        tracked(
            draw, (W / 2, 960),
            "The same kernel.  Someone else's rig.",
            face(22), rgba(WARM, late), tracking=1.4, align="center",
        )

    return overlay(img, paint)


def scene_buses(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 7.5, 1.02, 1.08, 0.5, 0.58, 0.5, 0.5)
    names = ["MQTT", "Modbus", "OPC UA", "Siemens S7", "EtherNet/IP", "CAN"]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        draw.line((280, 560, 1640, 560), fill=rgba(DIM, appear(t, 0.4, 0.8) * 0.5), width=1)
        for i, name in enumerate(names):
            a = appear(t, 0.5 + i * 0.28, 0.8) * fade_out(t, 7.5, 0.7)
            x = 320 + i * 260
            tracked(
                draw, (x, 500), name, face(22, "medium"),
                rgba(WARM, a), tracking=2, align="center",
            )
        a = appear(t, 2.2, 1.0)
        tracked(
            draw, (W / 2, 600), "observe only", face(16),
            rgba(TEAL, a * 0.9), tracking=8, align="center",
        )
        late = appear(t, 4.4, 1.2) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (W / 2, 860),
            "A browse is not a write.",
            face(22), rgba(MUTED, late), tracking=1.6, align="center",
        )

    return overlay(img, paint)


def scene_two_ais(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 7.5, 1.03, 1.09, 0.5, 0.5, 0.5, 0.46)
    cols = [
        (480, 0.6, "Grok 4.6", "wrote the system", MUTED),
        (960, 1.8, "Fake", "ran the bench", TEAL),
        (1440, 3.0, "Claude, then OpenAI", "may interpret", AMBER),
    ]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        for x, start, title, sub, col in cols:
            a = appear(t, start, 1.1) * fade_out(t, 7.5, 0.8)
            glow_disk(draw, (x, 430), 5, col, a * 0.5, rings=5)
            tracked(
                draw, (x, 470), title, face(26, "medium"),
                rgba(WARM, a), tracking=1.4, align="center",
            )
            tracked(
                draw, (x, 516), sub, face(16),
                rgba(MUTED, a * 0.9), tracking=1.8, align="center",
            )
        late = appear(t, 4.8, 1.3) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (W / 2, 780), "None of them own the pin.",
            face(22), rgba(WARM, late), tracking=1.5, align="center",
        )
        tracked(
            draw, (W / 2, 830), "GPIO23", face(14, "medium"),
            rgba(DIM, late * 0.8), tracking=6, align="center",
        )

    return overlay(img, paint)


def scene_gates(t: float) -> Image.Image:
    img = ken(plate("plate_void.png"), t, 7.5, 1.04, 1.12, 0.5, 0.7, 0.5, 0.45)
    # Six floor lamps receding into the room. The last one waits.
    lamps = [
        (960, 880),
        (960, 800),
        (960, 730),
        (960, 668),
        (960, 612),
        (960, 562),
    ]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        for i, (x, y) in enumerate(lamps):
            a = appear(t, 0.45 + i * 0.48, 0.55)
            last = i == 5
            lit = (not last) or (t >= 5.7)
            r = 11 - i * 1.15
            col = AMBER if last and lit else TEAL
            glow_disk(draw, (x, y), r, col if lit else DIM, a * (0.9 if lit else 0.22), rings=7)
        late = appear(t, 5.5, 1.2) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (W / 2, 200), "Arm is a separate act.",
            face(22), rgba(WARM, late * 0.9), tracking=1.6, align="center",
        )

    return overlay(img, paint)


def scene_record(t: float, title: str, detail: str) -> Image.Image:
    img = black()

    def paint(draw: ImageDraw.ImageDraw) -> None:
        a = appear(t, 0.4, 1.0) * fade_out(t, 4.6, 0.7)
        pulse = 0.6 + 0.4 * math.sin(t * 2.2)
        glow_disk(draw, (W / 2, 430), 16, RED, a * pulse, rings=8)
        draw.ellipse((W / 2 - 7, 423, W / 2 + 7, 437), fill=rgba((255, 80, 70), a * pulse))
        tracked(
            draw, (W / 2, 500), "RECORD", face(14, "medium"),
            rgba(MUTED, a * 0.8), tracking=12, align="center",
        )
        draw.text((W / 2, 560), title, font=face(36), fill=rgba(WARM, a), anchor="mm")
        tracked(
            draw, (W / 2, 630), detail, face(16),
            rgba(MUTED, a * 0.85), tracking=2, align="center",
        )

    return overlay(img, paint)


def scene_interview(t: float) -> Image.Image:
    img = ken(plate("plate_desks.png"), t, 10.5, 1.07, 1.12, 0.22, 0.42, 0.46, 0.36)
    qs = [
        (1.0, 300, 620, "What modules are here?"),
        (2.2, 760, 340, "Which bus?"),
        (3.4, 1080, 380, "Which tag is pressure?"),
        (4.6, 1280, 520, "Trip numbers and units?"),
        (5.8, 1600, 400, "What stays observe-only?"),
    ]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        for start, x, y, q in qs:
            a = appear(t, start, 0.9) * fade_out(t, 10.5, 0.8)
            glow_disk(draw, (x, y), 6, AMBER, a * 0.6, rings=6)
            tracked(
                draw, (x, y + 20), q, face(16),
                rgba(WARM, a), tracking=0.8, align="center",
            )
        late = appear(t, 7.4, 1.3) * fade_out(t, 10.5, 0.8)
        tracked(
            draw, (W / 2, 960),
            "The agent proposes.  A person applies.",
            face(22), rgba(WARM, late), tracking=1.3, align="center",
        )

    return overlay(img, paint)


def scene_capstone(t: float) -> Image.Image:
    img = ken(plate("plate_desks.png"), t, 7.5, 1.12, 1.06, 0.5, 0.4, 0.5, 0.5)
    steps = ["Deploy", "Interview", "Apply", "Twin", "Arm"]

    def paint(draw: ImageDraw.ImageDraw) -> None:
        for i, name in enumerate(steps):
            a = appear(t, 0.5 + i * 0.55, 0.7) * fade_out(t, 7.5, 0.8)
            x = 360 + i * 300
            glow_disk(draw, (x, 820), 5, TEAL if i < 4 else AMBER, a * 0.65, rings=5)
            tracked(
                draw, (x, 848), name, face(18, "medium"),
                rgba(WARM, a), tracking=2, align="center",
            )
        late = appear(t, 4.2, 1.2) * fade_out(t, 7.5, 0.8)
        tracked(
            draw, (W / 2, 960),
            "The interview is designed.  It is not built yet.",
            face(20), rgba(MUTED, late), tracking=1.2, align="center",
        )

    return overlay(img, paint)


def scene_close(t: float) -> Image.Image:
    img = ken(plate("plate_bench.png"), t, 9.5, 1.18, 1.05, 0.72, 0.4, 0.15, 0.45)

    def paint(draw: ImageDraw.ImageDraw) -> None:
        a1 = appear(t, 1.8, 1.5) * fade_out(t, 9.5, 1.2)
        a2 = appear(t, 3.6, 1.6) * fade_out(t, 9.5, 1.2)
        draw.text((160, 250), "The AI can ask.", font=face(42), fill=rgba(WARM, a1))
        draw.text((160, 318), "Only the kernel can say yes.", font=face(42), fill=rgba(WARM, a2))

    return overlay(img, paint)


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

Painter = Callable[[float], Image.Image]


@dataclass
class Beat:
    name: str
    duration: float
    painter: Painter
    overlap: float = 0.0  # xfade into next if >0, black gap if <0


BEATS: list[Beat] = [
    Beat("01_title", 8.0, scene_object, 1.0),
    Beat("02_question", 7.5, scene_question, -0.4),
    Beat("03_language_stops", 9.5, scene_glass, 0.8),
    Beat("05_and_gate", 18.5, scene_pressure, 0.9),
    Beat("05b_latch", 7.5, scene_latch, -0.4),
    Beat("04_architecture", 8.5, scene_architecture, -0.35),
    Beat("09_desks", 8.5, scene_desks, 0.8),
    Beat("06_protocols", 7.5, scene_buses, 0.7),
    Beat("07_two_ais", 7.5, scene_two_ais, 0.7),
    Beat("08_six_gates", 7.5, scene_gates, -0.45),
    Beat("R1_record_dashboard", 4.6, lambda t: scene_record(t, "Phase 3 dashboard", "port 8080  ·  observe only"), 0.5),
    Beat("R2_record_studio", 4.6, lambda t: scene_record(t, "Studio", "simulator is enough"), -0.45),
    Beat("09_interview", 10.5, scene_interview, 0.8),
    Beat("10_capstone_loop", 7.5, scene_capstone, 0.8),
    Beat("11_close", 9.5, scene_close, 0.0),
]


def starts_of(beats: list[Beat]) -> list[float]:
    t = 0.0
    out: list[float] = []
    for i, beat in enumerate(beats):
        out.append(t)
        nxt = beats[i].overlap
        t += beat.duration - max(0.0, nxt)
        if nxt < 0:
            t += -nxt
    return out


def lookbook_duration(beats: list[Beat]) -> float:
    s = starts_of(beats)
    last = beats[-1]
    return s[-1] + last.duration


def lookbook_frame(T: float) -> Image.Image:
    img = black()
    starts = starts_of(BEATS)
    for beat, start in zip(BEATS, starts):
        local = T - start
        if local < -0.05 or local > beat.duration + 0.05:
            continue
        fade_in = 0.8 if beat.name not in {"R1_record_dashboard", "R2_record_studio"} else 0.55
        fade_o = 0.8
        a = 1.0
        if local < fade_in:
            a *= smooth(local / fade_in)
        remain = beat.duration - local
        if remain < fade_o:
            a *= smooth(remain / fade_o)
        if a <= 0.01:
            continue
        layer = beat.painter(max(0.0, local))
        img = mix_images(img, layer, a)
    return img


CLIP_EXPORTS: list[tuple[str, float, Painter]] = [
    ("01_title.mp4", 8.0, scene_object),
    ("02_question.mp4", 7.5, scene_question),
    ("03_language_stops.mp4", 9.5, scene_glass),
    ("04_architecture.mp4", 8.5, scene_architecture),
    ("05_and_gate.mp4", 18.5, scene_pressure),
    ("05b_latch.mp4", 7.5, scene_latch),
    ("06_protocols.mp4", 7.5, scene_buses),
    ("07_two_ais.mp4", 7.5, scene_two_ais),
    ("08_six_gates.mp4", 7.5, scene_gates),
    ("R1_record_dashboard.mp4", 4.6, lambda t: scene_record(t, "Phase 3 dashboard", "port 8080  ·  observe only")),
    ("R2_record_studio.mp4", 4.6, lambda t: scene_record(t, "Studio", "simulator is enough")),
    ("09_interview.mp4", 10.5, scene_interview),
    ("10_capstone_loop.mp4", 7.5, scene_capstone),
    ("11_close.mp4", 9.5, scene_close),
]


PROOFS: list[tuple[str, Painter, float]] = [
    ("01_object.jpg", scene_object, 5.2),
    ("02_question.jpg", scene_question, 5.0),
    ("03_glass_approach.jpg", scene_glass, 2.6),
    ("03_glass_hit.jpg", scene_glass, 3.85),
    ("03_glass_fall.jpg", scene_glass, 5.4),
    ("05_pressure_idle.jpg", scene_pressure, 2.4),
    ("05_pressure_trip.jpg", scene_pressure, TRIP_T + 0.35),
    ("05_pressure_latched.jpg", scene_pressure, 16.2),
    ("05b_latch.jpg", scene_latch, 4.0),
    ("04_architecture.jpg", scene_architecture, 6.2),
    ("09_desks.jpg", scene_desks, 6.0),
    ("06_buses.jpg", scene_buses, 5.0),
    ("08_gates.jpg", scene_gates, 6.2),
    ("R1_record.jpg", lambda t: scene_record(t, "Phase 3 dashboard", "port 8080  ·  observe only"), 2.0),
    ("09_interview.jpg", scene_interview, 8.0),
    ("11_close.jpg", scene_close, 6.4),
]


def write_proof() -> None:
    PROOF.mkdir(parents=True, exist_ok=True)
    for name, painter, t in PROOFS:
        image = grade(painter(t), int(t * FPS))
        path = PROOF / name
        image.save(path, quality=92)
        print(f"proof {path.relative_to(ROOT)}", flush=True)


def write_gif(src: Path, dest: Path, start: float, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.2f}", "-t", f"{duration:.2f}", "-i", str(src),
        "-vf", "fps=10,scale=720:-1:flags=lanczos",
        str(dest),
    ]
    subprocess.check_call(cmd)
    print(f"wrote {dest.relative_to(ROOT)}", flush=True)


def write_lookbook_txt() -> None:
    (OUT / "lookbook.txt").write_text(
        "atelier lookbook — one studio, not a slide deck\n"
        "rebuild: python3 tools/render_phase3_atelier.py\n",
        encoding="utf-8",
    )


def main() -> None:
    args = set(sys.argv[1:])
    write_proof()
    if "--proof" in args:
        return

    OUT.mkdir(parents=True, exist_ok=True)
    if "--lookbook-only" not in args:
        for name, dur, painter in CLIP_EXPORTS:
            encode(OUT / name, dur, painter)

    dur = lookbook_duration(BEATS)
    encode(OUT / "LOOKBOOK.mp4", dur, lookbook_frame)
    write_lookbook_txt()

    # The proof of the redesign: the pressure test writing itself.
    starts = dict(zip([b.name for b in BEATS], starts_of(BEATS)))
    write_gif(OUT / "LOOKBOOK.mp4", OUT / "LOOKBOOK_preview.gif", starts["05_and_gate"] + 1.5, 16.0)
    print(f"lookbook duration {dur:.1f}s  trip at {TRIP_T:.2f}s", flush=True)


if __name__ == "__main__":
    main()
