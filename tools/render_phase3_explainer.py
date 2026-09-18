#!/usr/bin/env python3
"""Phase 3 explainer motion — cream paper, teal/gold/ink, one idea at a time.

Visual grammar matches ``tools/render_phase3_motion.py`` (smooth / appear /
rounded cards / ffmpeg stdin) and the paper stills in
``docs/explainer/phase3-film/stills/`` plus ``docs/explainer/assets/``.
NOT the dark atelier room. Do not call ``render_phase3_atelier.py``.

Reveals are spaced across the full spoken duration via ``u = t / dur``.
Clips are 1920x1080 30 fps libx264 crf 20. Frames pipe to ffmpeg stdin.
No LOOKBOOK. No PNG frame folders. No ``-stream_loop``.

Honesty: Fake is the proven runtime. Never imply Grok or Claude tripped
the relay.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_phase3_motion import (  # noqa: E402
    FPS,
    H,
    ROOT,
    W,
    appear,
    center_text,
    clamp,
    encode,
    mix,
    rounded,
    smooth,
)

OUT = ROOT / "docs" / "explainer" / "phase3-film" / "motion"
STILLS = ROOT / "docs" / "explainer" / "phase3-film" / "stills"
ASSETS = ROOT / "docs" / "explainer" / "assets"

# Paper stills palette (not the atelier charcoal room).
PAPER = (251, 252, 251)
WHITE = (255, 255, 255)
INK = (23, 37, 35)
MUTED = (102, 115, 111)
TEAL = (31, 122, 97)
TEAL_LIGHT = (216, 238, 229)
BLUE = (51, 101, 138)
BLUE_LIGHT = (217, 232, 241)
GOLD = (197, 138, 38)
GOLD_LIGHT = (245, 232, 201)
RED = (180, 75, 66)
RED_LIGHT = (244, 221, 221)
GRID = (223, 229, 226)


def _first_font(*paths: str) -> str | None:
    for path in paths:
        if path and Path(path).exists():
            return path
    return None


FONT = _first_font(
    "/usr/share/fonts/truetype/macos/Inter-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
)
FONT_MED = _first_font(
    "/usr/share/fonts/truetype/macos/Inter-Medium.ttf",
    FONT,
)
FONT_BOLD = _first_font(
    "/usr/share/fonts/truetype/macos/Inter-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    FONT,
)


@lru_cache(maxsize=48)
def font(size: int, weight: str = "regular") -> ImageFont.ImageFont:
    path = {"regular": FONT, "medium": FONT_MED, "bold": FONT_BOLD}[weight]
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fade(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return mix(PAPER, color, alpha)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), PAPER)
    return image, ImageDraw.Draw(image)


def paper_grid(draw: ImageDraw.ImageDraw, alpha: float = 0.45) -> None:
    color = fade(GRID, alpha)
    for x in range(80, W, 80):
        draw.line((x, 0, x, H), fill=color, width=1)
    for y in range(40, H, 80):
        draw.line((0, y, W, y), fill=color, width=1)


def u_of(t: float, dur: float) -> float:
    return 0.0 if dur <= 0 else clamp(t / dur)


def reveal(u: float, start: float, length: float = 0.08) -> float:
    """Ease in across a fraction of the clip, not a wall-clock 0.55 s."""
    return appear(u, start, max(0.04, length))


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.ImageFont,
         max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=face) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def rule(draw: ImageDraw.ImageDraw, y: int, alpha: float) -> None:
    if alpha <= 0:
        return
    draw.line((80, y, W - 80, y), fill=fade(GRID, alpha), width=2)


def kicker_title(draw: ImageDraw.ImageDraw, kicker: str, title: str,
                 u: float) -> None:
    a = reveal(u, 0.0, 0.07)
    draw.text((80, 48), kicker.upper(), font=font(15, "bold"), fill=fade(TEAL, a))
    draw.text((80, 78), title, font=font(36, "bold"), fill=fade(INK, a))
    rule(draw, 140, a)


def card(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float],
         a: float, *, fill=WHITE, outline=GRID, radius: int = 24) -> None:
    if a <= 0.02:
        return
    rounded(draw, box, mix(PAPER, fill, a), radius, fade(outline, a))


def caption(draw: ImageDraw.ImageDraw, text: str, u: float, start: float,
            *, y: int = 980, color=INK, size: int = 24) -> None:
    a = reveal(u, start, 0.08)
    if a <= 0:
        return
    center_text(draw, (W / 2, y), text, font(size, "medium"), fade(color, a))


_KB: dict[str, Image.Image] = {}


def load_cover(path: Path, overscan: float = 1.14) -> Image.Image:
    key = f"{path}:{overscan}"
    cached = _KB.get(key)
    if cached is not None:
        return cached
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    scale = max(W / sw, H / sh) * overscan
    out = im.resize((max(W, int(sw * scale)), max(H, int(sh * scale))),
                    Image.Resampling.LANCZOS)
    _KB[key] = out
    return out


def kenburns(prepared: Image.Image, u: float, *, start: float = 0.0) -> Image.Image:
    p = smooth(clamp((u - start) / max(1e-6, 1.0 - start)))
    nw, nh = prepared.size
    max_x = max(0, nw - W)
    max_y = max(0, nh - H)
    x = int(max_x * (0.12 + 0.76 * p))
    y = int(max_y * (0.18 + 0.50 * (1.0 - p)))
    return prepared.crop((x, y, x + W, y + H))


def paste_reveal(dst: Image.Image, src: Image.Image,
                 box: tuple[int, int, int, int], a: float) -> None:
    if a <= 0.02:
        return
    x0, y0, x1, y1 = box
    crop = src.crop((x0, y0, x1, y1))
    if a < 0.999:
        paper = Image.new("RGB", crop.size, PAPER)
        crop = Image.blend(paper, crop, a)
    dst.paste(crop, (x0, y0))


def blend_over(base: Image.Image, overlay: Image.Image, a: float) -> Image.Image:
    a = clamp(a)
    if a <= 0:
        return base
    if a >= 1:
        return overlay
    return Image.blend(base, overlay, a)


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------

def scene_title(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    a1 = reveal(u, 0.04, 0.14)
    line_w = 380 * a1
    draw.line((W / 2 - line_w, 390, W / 2 + line_w, 390), fill=fade(GOLD, a1), width=3)
    center_text(draw, (W / 2, 420), "What is CertaRig?", font(84, "bold"),
                fade(INK, a1))
    center_text(draw, (W / 2, 560), "Presented by Chintan Dedhia",
                font(28, "medium"), fade(MUTED, reveal(u, 0.38, 0.12)))
    center_text(
        draw, (W / 2, 760),
        "The AI can ask. Only the kernel can say yes.",
        font(28, "medium"), fade(TEAL, reveal(u, 0.68, 0.14)),
    )
    return image


def scene_question(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    paper_grid(draw, 0.28)
    kicker_title(draw, "The question", "Who is allowed to energize the output?", u)
    a = reveal(u, 0.08, 0.12)
    center_text(draw, (W / 2, 280), "Who is allowed to", font(42, "medium"), fade(INK, a))
    center_text(draw, (W / 2, 350), "energize the output?", font(64, "bold"), fade(GOLD, a))
    left = reveal(u, 0.42, 0.12)
    right = reveal(u, 0.68, 0.12)
    card(draw, (260, 560, 860, 860), left, outline=BLUE)
    center_text(draw, (560, 620), "AGENT", font(18, "bold"), fade(BLUE, left))
    center_text(draw, (560, 700), "can ask", font(40, "medium"), fade(INK, left))
    card(draw, (1060, 560, 1660, 860), right, fill=TEAL_LIGHT, outline=TEAL)
    center_text(draw, (1360, 620), "KERNEL", font(18, "bold"), fade(TEAL, right))
    center_text(draw, (1360, 700), "can say yes", font(40, "medium"), fade(INK, right))
    return image


def scene_problem(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    prepared = load_cover(STILLS / "01_problem_operator.png", 1.16)
    image = kenburns(prepared, u, start=0.0)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    beats = [
        (0.08, "Operator"),
        (0.34, "Clipboard"),
        (0.58, "Spreadsheet / screenshot inheritance"),
        (0.80, "Work begins at the bench."),
    ]
    current: tuple[float, str] | None = None
    for start, text in beats:
        if u >= start:
            current = (start, text)
    if current is not None:
        start, text = current
        a = reveal(u, start, 0.10)
        fill = (*WHITE, int(230 * a))
        outline = (*GRID, int(255 * a))
        tw = draw.textlength(text, font=font(26, "medium"))
        x0 = (W - tw) / 2 - 28
        box = (x0, 820, x0 + tw + 56, 884)
        draw.rounded_rectangle(box, radius=18, fill=fill, outline=outline, width=2)
        draw.text((x0 + 28, 836), text, font=font(26, "medium"),
                  fill=(*INK, int(255 * a)))
    image = image.convert("RGBA")
    image = Image.alpha_composite(image, overlay).convert("RGB")
    return image


def scene_language(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    paper_grid(draw, 0.22)
    kicker_title(draw, "Language is not a limit", "A sentence cannot cross a number.", u)

    line_y = 560
    draw.line((120, line_y, 1180, line_y), fill=fade(GRID, reveal(u, 0.06, 0.08)), width=3)
    for tick, label in ((0.0, "0"), (0.5, "2.1"), (1.0, "4.2"), (1.4, "5+")):
        x = 140 + tick * 700
        draw.line((x, line_y - 10, x, line_y + 10), fill=fade(MUTED, reveal(u, 0.08, 0.08)), width=2)
        center_text(draw, (x, line_y + 24), label, font(16), fade(MUTED, reveal(u, 0.08, 0.08)))

    wall_x = 140 + 1.0 * 700
    wall_a = reveal(u, 0.12, 0.10)
    draw.line((wall_x, 220, wall_x, 820), fill=fade(GOLD, wall_a), width=5)
    center_text(draw, (wall_x, 188), "4.2 bar", font(26, "bold"), fade(GOLD, wall_a))

    walk = smooth(clamp((u - 0.10) / 0.42))
    hit = u >= 0.52
    die = reveal(u, 0.52, 0.10)
    bubble_w, bubble_h = 360, 200
    stop_x = wall_x - bubble_w - 28
    shake = 0
    if hit:
        shake = int(10 * (1 - die) * (1 if int(t * 36) % 2 == 0 else -1))
    bx = 140 + (stop_x - 140) * walk + shake
    by = 400
    bubble_a = max(0.0, 1.0 - die * 0.85) if hit else 1.0
    if u > 0.08:
        card(draw, (bx, by, bx + bubble_w, by + bubble_h), bubble_a, outline=INK)
        draw.text((bx + 28, by + 28), "run it,", font=font(28, "medium"),
                  fill=fade(INK, bubble_a))
        draw.text((bx + 28, by + 72), "maybe five", font=font(28, "medium"),
                  fill=fade(INK, bubble_a))
        if hit:
            center_text(draw, (bx + bubble_w / 2, by + 140), "DIES",
                        font(22, "bold"), fade(RED, die))

    lock = reveal(u, 0.62, 0.10)
    card(draw, (1280, 340, 1780, 780), lock, outline=mix(GRID, RED, lock))
    center_text(draw, (1530, 400), "RELAY", font(18, "bold"), fade(MUTED, lock))
    center_text(draw, (1530, 470), "GPIO23", font(40, "bold"), fade(INK, lock))
    center_text(draw, (1530, 580), "LOCKED", font(28, "bold"), fade(RED, lock))
    center_text(draw, (1530, 660), "stays locked", font(22, "medium"), fade(MUTED, lock))
    caption(draw, "A sentence cannot cross a number.", u, 0.78, color=INK, size=26)
    return image


def scene_relay(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    paper_grid(draw, 0.2)
    kicker_title(draw, "The wrong product", "Putting an LLM on the relay.", u)

    left = reveal(u, 0.10, 0.12)
    card(draw, (140, 220, 820, 720), left, fill=BLUE_LIGHT, outline=BLUE)
    center_text(draw, (480, 280), "LLM", font(20, "bold"), fade(BLUE, left))
    center_text(draw, (480, 360), "a sentence", font(36, "bold"), fade(INK, left))
    center_text(draw, (480, 430), "about the bench", font(28, "medium"), fade(MUTED, left))
    center_text(draw, (480, 560), "“run it, maybe five”", font(24, "medium"), fade(INK, left))

    arrow = reveal(u, 0.32, 0.10)
    draw.polygon([(850, 450), (1040, 470), (850, 490)], fill=fade(GRID, arrow))

    right = reveal(u, 0.28, 0.12)
    card(draw, (1080, 220, 1780, 720), right, outline=RED)
    center_text(draw, (1430, 280), "RELAY  ·  GPIO23", font(20, "bold"), fade(RED, right))
    center_text(draw, (1430, 400), "energize?", font(42, "bold"), fade(INK, right))

    wrong = reveal(u, 0.52, 0.12)
    if wrong > 0:
        cx, cy, r = 960, 470, int(70 + 20 * wrong)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=fade(RED, wrong), width=8)
        draw.line((cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18),
                  fill=fade(RED, wrong), width=8)
        center_text(draw, (W / 2, 780), "That is the wrong product.",
                    font(32, "bold"), fade(RED, wrong))

    caption(draw, "Who is allowed to say yes?", u, 0.78, color=TEAL, size=32)
    return image


def scene_protocols(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Same kernel, different buses", "Six buses. Observe only.", u)
    buses = [
        ("MQTT", "Topics on a broker"),
        ("Modbus", "TCP or RTU registers"),
        ("OPC UA", "Modern PLC / SCADA"),
        ("Siemens S7", "Native data blocks"),
        ("EtherNet/IP", "Allen-Bradley tags"),
        ("CAN", "Vehicle / battery"),
    ]
    gap = 24
    card_w = (W - 160 - gap * 5) // 6
    for i, (name, blurb) in enumerate(buses):
        a = reveal(u, 0.06 + i * (0.70 / 6), 0.08)
        x = 80 + i * (card_w + gap)
        y = 220 + int((1 - a) * 28)
        card(draw, (x, y, x + card_w, 820), a)
        if a <= 0:
            continue
        center_text(draw, (x + card_w / 2, y + 48), name, font(22, "bold"), fade(INK, a))
        by = y + 120
        for line in wrap(draw, blurb, font(18), card_w - 36):
            lw = draw.textlength(line, font=font(18))
            draw.text((x + (card_w - lw) / 2, by), line, font=font(18), fill=fade(MUTED, a))
            by += 28
        badge = "observe only"
        bw = draw.textlength(badge, font=font(15, "medium"))
        bx = x + (card_w - bw) / 2
        rounded(draw, (bx - 14, 720, bx + bw + 14, 768), fade(BLUE_LIGHT, a), 12, None)
        draw.text((bx, 730), badge, font=font(15, "medium"), fill=fade(BLUE, a))
    caption(draw, "A browse is not a write.", u, 0.72, color=INK, size=28)
    return image


def scene_architecture(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    paper_grid(draw, 0.18)
    kicker_title(draw, "Split the jobs", "Four blocks. One lock.", u)
    blocks = [
        (BLUE, BLUE_LIGHT, "Operator + Studio", "speaks intent · reviews the map"),
        (GOLD, GOLD_LIGHT, "Agent", "interprets, never compares"),
        (TEAL, TEAL_LIGHT, "Kernel", "measures, latches, owns GPIO23"),
        (INK, WHITE, "Rig", "pots, E-stop, relay"),
    ]
    gap = 28
    card_w = (W - 160 - gap * 3) // 4
    for i, (accent, fill, title, body) in enumerate(blocks):
        a = reveal(u, 0.06 + i * 0.12, 0.09)
        x = 80 + i * (card_w + gap)
        y = 200 + int((1 - a) * 36)
        card(draw, (x, y, x + card_w, y + 420), a, fill=fill, outline=accent)
        if a <= 0:
            continue
        draw.text((x + 28, y + 36), f"0{i + 1}", font=font(16, "bold"), fill=fade(accent, a))
        draw.text((x + 28, y + 90), title, font=font(26, "bold"), fill=fade(INK, a))
        ty = y + 170
        for line in wrap(draw, body, font(20), card_w - 56):
            draw.text((x + 28, ty), line, font=font(20), fill=fade(MUTED, a))
            ty += 32
        if i < 3:
            ax = x + card_w + 4
            ay = y + 200
            arr = reveal(u, 0.14 + i * 0.12, 0.06)
            draw.polygon([(ax, ay - 10), (ax + gap - 10, ay), (ax, ay + 10)],
                         fill=fade(GRID, arr))
    lock = reveal(u, 0.54, 0.10)
    center_text(
        draw, (W / 2, 720),
        "The agent can ask. Only the kernel can say yes.",
        font(28, "medium"), fade(TEAL, lock),
    )

    kb_a = reveal(u, 0.66, 0.12)
    if kb_a > 0:
        prepared = load_cover(ASSETS / "07_product_architecture.png", 1.10)
        kb = kenburns(prepared, u, start=0.66)
        image = blend_over(image, kb, kb_a)
    return image


def scene_and_gate(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "The surprising rule", "Five terms. Then a latch.", u)
    terms = ["enabled", "permit", "no trip", "E-stop", "healthy"]
    trip = u >= 0.48
    recovered = u >= 0.70
    gap = 24
    card_w = (W - 160 - gap * 4) // 5
    for i, name in enumerate(terms):
        a = reveal(u, 0.06 + i * 0.06, 0.07)
        x = 80 + i * (card_w + gap)
        failed = i == 2 and trip and not recovered
        latched = i == 2 and recovered
        fill = TEAL_LIGHT if not failed and not latched else (GOLD_LIGHT if latched else RED_LIGHT)
        outline = TEAL if not failed and not latched else (GOLD if latched else RED)
        card(draw, (x, 200, x + card_w, 480), a, fill=fill, outline=outline)
        center_text(draw, (x + card_w / 2, 300), name, font(26, "bold"), fade(INK, a))
        if latched:
            center_text(draw, (x + card_w / 2, 380), "LATCHED", font(16, "bold"), fade(GOLD, a))

    lamp_a = reveal(u, 0.36, 0.08)
    lamp_on = u >= 0.36 and not trip
    lamp_fill = TEAL_LIGHT if lamp_on else RED_LIGHT
    lamp_outline = TEAL if lamp_on else RED
    card(draw, (710, 540, 1210, 720), lamp_a, fill=lamp_fill, outline=lamp_outline)
    center_text(draw, (960, 570), "OUTPUT", font(16, "bold"), fade(MUTED, lamp_a))
    center_text(draw, (960, 620), "ON" if lamp_on else "SAFE",
                font(44, "bold"), fade(TEAL if lamp_on else RED, lamp_a))

    if u < 0.48:
        line = "All five true. Lamp ON."
    elif not recovered:
        line = "The trip term fails. Lamp SAFE."
    else:
        line = "Pressure comes home. Lamp STAYS safe. Reset required."
    cap_start = 0.38 if u < 0.48 else (0.50 if not recovered else 0.72)
    caption(draw, line, u, cap_start, y=780, size=24)

    eq_a = reveal(u, 0.18, 0.10)
    center_text(
        draw, (W / 2, 880),
        "OUTPUT = enabled AND permit AND not tripped AND E-stop closed AND healthy",
        font(18, "medium"), fade(MUTED, eq_a),
    )
    return image


def scene_latch(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    paper_grid(draw, 0.2)
    kicker_title(draw, "The pin that stayed down", "GPIO23 is latched.", u)
    a = reveal(u, 0.08, 0.12)
    # Macro of a pin / header.
    cx = 960
    draw.rectangle((cx - 28, 260, cx + 28, 720), fill=fade((180, 186, 190), a))
    draw.rectangle((cx - 70, 220, cx + 70, 280), fill=fade((90, 96, 100), a))
    pad_a = reveal(u, 0.22, 0.10)
    draw.ellipse((cx - 90, 680, cx + 90, 860), fill=fade(RED_LIGHT, pad_a), outline=fade(RED, pad_a), width=4)
    center_text(draw, (cx, 740), "GPIO23", font(36, "bold"), fade(INK, pad_a))
    flag = reveal(u, 0.40, 0.12)
    card(draw, (1180, 360, 1760, 620), flag, fill=RED_LIGHT, outline=RED)
    center_text(draw, (1470, 410), "LATCHED", font(22, "bold"), fade(RED, flag))
    center_text(draw, (1470, 480), "pin stays down", font(32, "bold"), fade(INK, flag))
    center_text(draw, (1470, 540), "No auto-restart", font(24, "medium"), fade(MUTED, flag))
    caption(draw, "Returning to normal does not clear the memory.", u, 0.72, size=24)
    return image


def scene_output_equation(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    still = Image.open(STILLS / "08_output_equation.png").convert("RGB")
    if still.size != (W, H):
        still = still.resize((W, H), Image.Resampling.LANCZOS)
    image, draw = canvas()
    # Title band of the still from the start; terms then the full equation.
    paste_reveal(image, still, (0, 0, W, 220), reveal(u, 0.02, 0.08))
    gap = 24
    card_w = (W - 160 - gap * 4) // 5
    for i in range(5):
        a = reveal(u, 0.10 + i * 0.12, 0.10)
        x = 80 + i * (card_w + gap)
        paste_reveal(image, still, (x, 250, x + card_w, 640), a)
    eq_a = reveal(u, 0.72, 0.12)
    paste_reveal(image, still, (40, 680, W - 40, 980), eq_a)
    caption(draw, "OUTPUT = enabled AND permit AND ¬trip AND E-stop AND healthy",
            u, 0.78, y=1010, size=20)
    return image


def scene_two_ais(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    a = reveal(u, 0.08, 0.14)
    center_text(draw, (W / 2, 380), "Two AIs must not be confused.",
                font(56, "bold"), fade(INK, a))
    rule(draw, 500, a)
    center_text(
        draw, (W / 2, 560),
        "Build-time is not runtime. Runtime is not the pin.",
        font(26, "medium"), fade(MUTED, reveal(u, 0.40, 0.14)),
    )
    caption(draw, "Grok writes. Fake ran the bench. Neither owns GPIO23.",
            u, 0.70, color=TEAL, size=24)
    return image


def scene_ai_stack(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Why this AI", "Three columns. One proven path.", u)
    cols = [
        (0.06, BLUE, BLUE_LIGHT, "BUILD", "Grok 4.6",
         "Writes code and tests. Never GPIO. Never the relay."),
        (0.30, TEAL, TEAL_LIGHT, "RUNTIME", "Fake",
         "12 Sep proven. CI and the hardware procedures. No API key."),
        (0.58, GOLD, GOLD_LIGHT, "FALLBACK", "Claude, then OpenAI",
         "Live interpreters only. Unproven live. Same Edge API."),
    ]
    gap = 36
    card_w = (W - 160 - gap * 2) // 3
    for i, (start, accent, fill, kicker, title, body) in enumerate(cols):
        a = reveal(u, start, 0.10)
        x = 80 + i * (card_w + gap)
        outline = TEAL if i == 1 and u >= 0.30 else accent
        card(draw, (x, 180, x + card_w, 780), a, fill=fill if i != 1 else WHITE,
             outline=outline)
        if a <= 0:
            continue
        rounded(draw, (x + 36, 220, x + 240, 272), fade(fill, a), 12, None)
        draw.text((x + 52, 232), kicker, font=font(16, "bold"), fill=fade(accent, a))
        draw.text((x + 36, 310), title, font=font(36, "bold"), fill=fade(INK, a))
        ty = 400
        for line in wrap(draw, body, font(22), card_w - 72):
            draw.text((x + 36, ty), line, font=font(22), fill=fade(MUTED, a))
            ty += 34
        if i == 1:
            badge = reveal(u, 0.38, 0.10)
            rounded(draw, (x + 36, 640, x + card_w - 36, 720), fade(TEAL_LIGHT, badge), 16, fade(TEAL, badge))
            center_text(draw, (x + card_w / 2, 662), "PROVEN PATH  ·  12 Sep",
                        font(18, "bold"), fade(TEAL, badge))
    caption(draw, "Fake ran the bench. Grok and Claude never tripped the relay.",
            u, 0.84, color=TEAL, size=22)
    return image


def scene_benchmark(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Benchmark this use case", "Not trivia.", u)
    rows = [
        ("Skill routing", "“4.2 bar” selects pressure_guardrail. “15 L/min” selects flow."),
        ("Tool discipline", "Only capability-manifest tools. No bypass. No override."),
        ("Never compare 4.2", "The model never compares the number. The kernel does."),
        ("Stop for human", "reset_trip and shutdown wait for a person."),
        ("Swap providers", "Fake, Claude, OpenAI, Replay — same Edge API."),
    ]
    y = 170
    for i, (title, body) in enumerate(rows):
        a = reveal(u, 0.08 + i * 0.14, 0.09)
        card(draw, (80, y, W - 80, y + 130), a)
        if a > 0:
            draw.ellipse((120, y + 48, 152, y + 80), fill=fade(TEAL, a))
            draw.text((190, y + 24), title, font=font(28, "bold"), fill=fade(INK, a))
            draw.text((190, y + 72), body, font=font(22), fill=fade(MUTED, a))
        y += 148
    return image


def scene_gates(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Six gates, then a relay", "Light them in order.", u)
    labels = ["Read only", "Sidecar", "Observe", "Twin", "Actuate", "Restore"]
    gap = 24
    card_w = (W - 160 - gap * 5) // 6
    for i, name in enumerate(labels):
        a = reveal(u, 0.06 + i * (0.58 / 6), 0.08)
        x = 80 + i * (card_w + gap)
        on = a > 0.6
        fill = TEAL_LIGHT if on else WHITE
        outline = TEAL if on else GRID
        card(draw, (x, 200, x + card_w, 720), a, fill=fill, outline=outline)
        center_text(draw, (x + card_w / 2, 280), str(i), font(44, "bold"), fade(TEAL, a))
        center_text(draw, (x + card_w / 2, 400), name, font(22, "medium"), fade(INK, a))
        if on:
            center_text(draw, (x + card_w / 2, 560), "ON", font(16, "bold"), fade(TEAL, a))
    kb_a = reveal(u, 0.72, 0.12)
    if kb_a > 0:
        prepared = load_cover(ASSETS / "01_gate_ladder.png", 1.10)
        kb = kenburns(prepared, u, start=0.72)
        image = blend_over(image, kb, kb_a)
    return image


def scene_interview(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Capstone interview", "Designed, not built.", u)
    questions = [
        ("1", "What modules are here?", "Pots, ADC, E-stop, relay, PLC, other"),
        ("2", "Which bus?", "GPIO, MQTT, Modbus, OPC UA, S7, EtherNet/IP, CAN"),
        ("3", "Which pin, register, or tag?", "Pressure, flow — mapped, not guessed"),
        ("4", "What are the trip numbers?", "Units and limits the kernel will compare"),
        ("5", "What must stay observe-only?", "A browse is never a write"),
    ]
    y = 168
    for i, (num, title, body) in enumerate(questions):
        a = reveal(u, 0.06 + i * 0.15, 0.09)
        card(draw, (80, y, W - 80, y + 128), a)
        if a > 0:
            draw.ellipse((120, y + 34, 184, y + 98), fill=fade(BLUE_LIGHT, a))
            center_text(draw, (152, y + 48), num, font(24, "bold"), fade(BLUE, a))
            draw.text((220, y + 24), title, font=font(28, "bold"), fill=fade(INK, a))
            draw.text((220, y + 72), body, font=font(20), fill=fade(MUTED, a))
        y += 140
    caption(draw, "Designed, not built.", u, 0.86, color=GOLD, size=24)
    return image


def scene_map(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "The map is a proposal", "Agent proposes. Human applies.", u)
    steps = [
        (BLUE, BLUE_LIGHT, "Agent", "Proposes the map"),
        (GOLD, GOLD_LIGHT, "Human", "Reviews and applies"),
        (TEAL, TEAL_LIGHT, "Twin", "Same procedure hash"),
        (RED, RED_LIGHT, "Arm", "Then — and only then"),
    ]
    gap = 28
    card_w = (W - 160 - gap * 3) // 4
    for i, (accent, fill, title, body) in enumerate(steps):
        a = reveal(u, 0.06 + i * 0.10, 0.08)
        x = 80 + i * (card_w + gap)
        card(draw, (x, 200, x + card_w, 620), a, fill=fill, outline=accent)
        center_text(draw, (x + card_w / 2, 280), title.upper(), font(18, "bold"), fade(accent, a))
        ty = 360
        for line in wrap(draw, body, font(26, "bold"), card_w - 48):
            lw = draw.textlength(line, font=font(26, "bold"))
            draw.text((x + (card_w - lw) / 2, ty), line, font=font(26, "bold"), fill=fade(INK, a))
            ty += 40
        if i < 3:
            draw.polygon(
                [(x + card_w + 4, 400), (x + card_w + gap - 8, 420), (x + card_w + 4, 440)],
                fill=fade(GRID, reveal(u, 0.12 + i * 0.10, 0.06)),
            )
    kb_a = reveal(u, 0.50, 0.12)
    if kb_a > 0:
        prepared = load_cover(STILLS / "11_map_locked.png", 1.08)
        kb = kenburns(prepared, u, start=0.50)
        image = blend_over(image, kb, kb_a)
    return image


def scene_loop(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    kicker_title(draw, "Capstone loop", "Walk it slowly.", u)
    steps = [
        ("Deploy", BLUE, "Install on their Pi, IPC, or laptop."),
        ("Interview", GOLD, "Modules, bus, pin/tag, trips, observe-only."),
        ("Human apply", TEAL, "Proposed rig.json does nothing until a person applies it."),
        ("Twin", BLUE, "Exact procedure hash must pass in simulation."),
        ("Arm", RED, "Explicit actuation. Kernel still says yes."),
    ]
    active = int(clamp((u - 0.06) / 0.16, 0.0, 4.99))
    y = 180
    for i, (name, accent, body) in enumerate(steps):
        a = reveal(u, 0.06 + i * 0.14, 0.08)
        on = i <= active
        fill = mix(WHITE, mix(WHITE, accent, 0.12), a) if on else mix(PAPER, WHITE, a)
        card(draw, (80, y, W - 80, y + 130), a, fill=fill, outline=accent if on else GRID)
        if a > 0:
            draw.ellipse((120, y + 48, 152, y + 80), fill=fade(accent if on else GRID, a))
            draw.text((190, y + 22), name, font=font(28, "bold"), fill=fade(INK, a))
            draw.text((190, y + 70), body, font=font(22), fill=fade(MUTED, a))
        y += 140
    caption(draw, "Interview is design, not proven.", u, 0.82, color=GOLD, size=26)
    return image


def scene_close(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    a1 = reveal(u, 0.08, 0.16)
    a2 = reveal(u, 0.42, 0.16)
    center_text(draw, (W / 2, 380), "The AI can ask.", font(64, "bold"), fade(INK, a1))
    center_text(draw, (W / 2, 490), "Only the kernel can say yes.",
                font(64, "bold"), fade(TEAL, a2))
    return image


def scene_thanks(t: float, dur: float) -> Image.Image:
    u = u_of(t, dur)
    image, draw = canvas()
    a1 = reveal(u, 0.04, 0.12)
    center_text(draw, (W / 2, 300), "The AI can ask.", font(48, "bold"), fade(INK, a1))
    center_text(draw, (W / 2, 380), "Only the kernel can say yes.",
                font(48, "bold"), fade(TEAL, reveal(u, 0.18, 0.12)))
    rule(draw, 500, reveal(u, 0.32, 0.08))
    center_text(draw, (W / 2, 560), "Phase 3 complete.",
                font(32, "medium"), fade(INK, reveal(u, 0.42, 0.12)))
    center_text(draw, (W / 2, 640), "Capstone is any mapped bench.",
                font(28, "medium"), fade(MUTED, reveal(u, 0.62, 0.12)))
    center_text(draw, (W / 2, 860), "CertaRig  ·  Phase 3 submission",
                font(20), fade(MUTED, reveal(u, 0.78, 0.10)))
    return image


SCENES: list[tuple[str, float, object]] = [
    ("01_title", 8.0, scene_title),
    ("02_question", 7.5, scene_question),
    ("03_problem", 12.5, scene_problem),
    ("03_language_stops", 9.5, scene_language),
    ("03b_relay", 10.5, scene_relay),
    ("06_protocols", 23.8, scene_protocols),
    ("04_architecture", 28.6, scene_architecture),
    ("05_and_gate", 18.5, scene_and_gate),
    ("05b_latch", 9.3, scene_latch),
    ("08_output_equation", 18.5, scene_output_equation),
    ("07_two_ais", 7.5, scene_two_ais),
    ("07b_ai_stack", 48.0, scene_ai_stack),
    ("07c_benchmark", 35.2, scene_benchmark),
    ("08_six_gates", 16.9, scene_gates),
    ("09_interview", 38.8, scene_interview),
    ("09b_map", 24.4, scene_map),
    ("10_capstone_loop", 45.25, scene_loop),
    ("11_close", 9.5, scene_close),
    ("11b_thanks", 14.8, scene_thanks),
]


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def render_one(name: str, duration: float, painter) -> Path:
    path = OUT / f"{name}.mp4"

    def bound(t: float, d: float = duration, fn=painter) -> Image.Image:
        return fn(t, d)

    encode(path, duration, bound)
    got = ffprobe_duration(path)
    if abs(got - duration) > 0.12:
        raise SystemExit(f"{name}: duration {got:.3f}s != {duration:.3f}s")
    print(f"  duration ok  {got:.2f}s")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None,
                    help="render only these clip stems (e.g. 01_title 05_and_gate)")
    args = ap.parse_args()
    if not FONT:
        print("warning: no Inter/DejaVu/Arial found; using PIL default", file=sys.stderr)
    else:
        print(f"font {FONT}")
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set(args.only) if args.only else None
    rendered = 0
    for name, duration, painter in SCENES:
        if wanted is not None and name not in wanted:
            continue
        render_one(name, duration, painter)
        rendered += 1
    if wanted is not None and rendered != len(wanted):
        known = {n for n, _, _ in SCENES}
        missing = sorted(wanted - known)
        raise SystemExit(f"unknown clip(s): {missing}")


if __name__ == "__main__":
    main()
