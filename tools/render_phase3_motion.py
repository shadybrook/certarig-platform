#!/usr/bin/env python3
"""Render 1920x1080 motion clips for the Phase 3 film (3Blue1Brown / Veritasium grammar)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "explainer" / "phase3-film" / "motion"
FONT = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
FONT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/macos/Inter-Bold.ttf"

W, H, FPS = 1920, 1080, 30

BG = (11, 14, 20)
CARD = (20, 25, 34)
STROKE = (42, 50, 64)
INK = (244, 241, 234)
MUTED = (142, 150, 162)
TEAL = (62, 207, 142)
GOLD = (232, 197, 71)
RED = (255, 92, 92)
BLUE = (110, 168, 254)
CREAM = (244, 241, 234)


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {"regular": FONT, "medium": FONT_MED, "bold": FONT_BOLD}[weight]
    return ImageFont.truetype(path, size=size)


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def smooth(t: float) -> float:
    t = clamp(t)
    return t * t * (3.0 - 2.0 * t)


def appear(t: float, start: float, dur: float = 0.55) -> float:
    return smooth((t - start) / dur)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def fade(color: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return mix(BG, color, alpha)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), BG)
    return image, ImageDraw.Draw(image)


def grid(draw: ImageDraw.ImageDraw, alpha: float = 0.22) -> None:
    color = fade(STROKE, alpha)
    for x in range(120, W, 80):
        draw.line((x, 0, x, H), fill=color, width=1)
    for y in range(80, H, 80):
        draw.line((0, y, W, y), fill=color, width=1)


def chapter(draw: ImageDraw.ImageDraw, number: str, title: str, alpha: float) -> None:
    if alpha <= 0:
        return
    draw.text((80, 48), number, font=font(18, "bold"), fill=fade(GOLD, alpha))
    draw.text((160, 48), title.upper(), font=font(18, "medium"), fill=fade(MUTED, alpha))


def rounded(draw: ImageDraw.ImageDraw, box: tuple[float, float, float, float], fill, radius: int = 28, outline=None) -> None:
    xy = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2 if outline else 0)


def center_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, face: ImageFont.FreeTypeFont, fill) -> None:
    x, y = xy
    w = draw.textlength(text, font=face)
    draw.text((x - w / 2, y), text, font=face, fill=fill)


def encode(path: Path, duration: float, painter) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration * FPS)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        "-crf", "20", "-movflags", "+faststart", str(path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for index in range(frames):
        image = painter(index / FPS)
        proc.stdin.write(image.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")
    print(f"wrote {path.relative_to(ROOT)}  ({duration:.1f}s)")


def scene_title(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.12)
    a = appear(t, 0.3, 0.8)
    line_w = 420 * a
    draw.line((W / 2 - line_w, 430, W / 2 + line_w, 430), fill=fade(GOLD, a), width=3)
    center_text(draw, (W / 2, 470), "What is CertaRig?", font(84, "bold"), fade(INK, appear(t, 0.7, 0.7)))
    center_text(draw, (W / 2, 590), "Presented by Chintan Dedhia", font(28, "medium"), fade(MUTED, appear(t, 1.6, 0.6)))
    center_text(
        draw,
        (W / 2, 860),
        "The AI can ask.  Only the kernel can say yes.",
        font(24, "medium"),
        fade(TEAL, appear(t, 2.6, 0.7)),
    )
    return image


def scene_question(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.14)
    chapter(draw, "01", "The question", appear(t, 0.1))
    a = appear(t, 0.4, 0.8)
    center_text(draw, (W / 2, 340), "Who is allowed to", font(54, "medium"), fade(INK, a))
    center_text(draw, (W / 2, 430), "energize the output?", font(72, "bold"), fade(GOLD, a))
    left = appear(t, 2.2)
    right = appear(t, 3.1)
    rounded(draw, (280, 640, 820, 860), fade(CARD, left), 32, fade(STROKE, left))
    center_text(draw, (550, 690), "AGENT", font(22, "bold"), fade(BLUE, left))
    center_text(draw, (550, 750), "can ask", font(36, "medium"), fade(INK, left))
    rounded(draw, (1100, 640, 1640, 860), fade(CARD, right), 32, fade(TEAL, right * 0.8))
    center_text(draw, (1370, 690), "KERNEL", font(22, "bold"), fade(TEAL, right))
    center_text(draw, (1370, 750), "can say yes", font(36, "medium"), fade(INK, right))
    return image


def scene_language(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.12)
    chapter(draw, "02", "Language is not a limit", appear(t, 0.05))
    wall_x = 1080
    draw.line((wall_x, 220, wall_x, 860), fill=GOLD, width=3)
    center_text(draw, (wall_x, 170), "4.2 bar", font(28, "bold"), GOLD)

    travel = smooth(clamp((t - 0.6) / 2.4))
    hit = t >= 3.0
    shake = 8 * (1 - appear(t, 3.0, 0.35)) * (1 if int(t * 40) % 2 == 0 else -1) if hit else 0
    bubble_w = 360
    stop_x = wall_x - bubble_w - 36
    bx = 180 + (stop_x - 180) * travel + (shake if hit else 0)
    by = 430
    rounded(draw, (bx, by, bx + bubble_w, by + 210), CARD, 28, STROKE)
    draw.text((bx + 36, by + 36), "run it,", font=font(32, "medium"), fill=INK)
    draw.text((bx + 36, by + 84), "maybe five,", font=font(32, "medium"), fill=INK)
    draw.text((bx + 36, by + 132), "looks fine.", font=font(32, "medium"), fill=MUTED)

    lock = appear(t, 3.3, 0.6)
    rounded(draw, (1180, 360, 1680, 760), fade(CARD, 0.9), 32, fade(mix(STROKE, RED, lock), 1))
    center_text(draw, (1430, 430), "RELAY", font(22, "bold"), fade(MUTED, 0.9))
    center_text(draw, (1430, 500), "GPIO23", font(40, "bold"), fade(INK, 0.9))
    center_text(draw, (1430, 600), "LOCKED", font(28, "bold"), fade(RED, lock))
    center_text(
        draw,
        (W / 2, 940),
        "A sentence cannot cross a number.",
        font(26, "medium"),
        fade(INK, appear(t, 4.0, 0.6)),
    )
    return image


def scene_architecture(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "03", "Split the jobs", appear(t, 0.05))
    blocks = [
        (BLUE, "Operator", "speaks intent"),
        (GOLD, "Agent", "interprets, never compares"),
        (TEAL, "Kernel", "measures, latches, owns GPIO"),
        (INK, "Rig", "pots, E-stop, relay"),
    ]
    gap = 36
    card_w = (W - 160 - gap * 3) // 4
    for i, (accent, title, body) in enumerate(blocks):
        a = appear(t, 0.4 + i * 0.85, 0.55)
        x = 80 + i * (card_w + gap)
        y = 340 + (1 - a) * 50
        rounded(draw, (x, y, x + card_w, y + 420), fade(CARD, a), 28, fade(accent, a * 0.7))
        draw.text((x + 36, y + 48), f"0{i + 1}", font=font(18, "bold"), fill=fade(accent, a))
        draw.text((x + 36, y + 120), title, font=font(34, "bold"), fill=fade(INK, a))
        draw.text((x + 36, y + 190), body, font=font(22), fill=fade(MUTED, a))
        if i < 3:
            ax = x + card_w + 6
            ay = y + 210
            arrow = appear(t, 0.9 + i * 0.85, 0.35)
            draw.polygon([(ax, ay - 12), (ax + gap - 12, ay), (ax, ay + 12)], fill=fade(STROKE, arrow))
    center_text(
        draw,
        (W / 2, 900),
        "The agent can ask.  Only the kernel can say yes.",
        font(28, "medium"),
        fade(TEAL, appear(t, 4.0, 0.7)),
    )
    return image


def scene_and_gate(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "04", "The surprising rule", appear(t, 0.05))
    terms = ["enabled", "permit", "no trip", "E-stop", "healthy"]
    trip = t >= 4.2
    recovered = t >= 6.4
    gap = 28
    card_w = (W - 160 - gap * 4) // 5
    for i, name in enumerate(terms):
        a = appear(t, 0.35 + i * 0.22, 0.4)
        x = 80 + i * (card_w + gap)
        healthy = not (i == 2 and trip and not recovered)
        latched = i == 2 and recovered
        fill = TEAL if healthy else (GOLD if latched else RED)
        rounded(draw, (x, 280, x + card_w, 520), fade(CARD, a), 24, fade(fill, a))
        center_text(draw, (x + card_w / 2, 360), name, font(28, "bold"), fade(INK, a))
    lamp_on = t >= 2.6 and not trip
    lamp_a = appear(t, 2.6, 0.35)
    rounded(draw, (710, 580, 1210, 760), fade(CARD, lamp_a), 28, fade(TEAL if lamp_on else RED, lamp_a))
    center_text(draw, (960, 615), "OUTPUT", font(18, "bold"), fade(MUTED, lamp_a))
    center_text(draw, (960, 665), "ON" if lamp_on else "SAFE", font(44, "bold"), fade(TEAL if lamp_on else RED, lamp_a))
    caption = "All five true."
    if trip and not recovered:
        caption = "A trip removes the output."
    if recovered:
        caption = "Returning to normal does not restart it. Reset is required."
    center_text(draw, (W / 2, 820), caption, font(26, "medium"), fade(INK, appear(t, 2.4, 0.4)))
    center_text(
        draw,
        (W / 2, 920),
        "OUTPUT = enabled AND permit AND not tripped AND E-stop closed AND healthy",
        font(20, "medium"),
        fade(MUTED, appear(t, 1.2, 0.5)),
    )
    return image


def scene_protocols(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "05", "Same kernel, different buses", appear(t, 0.05))
    buses = ["MQTT", "Modbus", "OPC UA", "Siemens S7", "EtherNet/IP", "CAN"]
    gap = 24
    card_w = (W - 160 - gap * 5) // 6
    for i, name in enumerate(buses):
        a = appear(t, 0.3 + i * 0.28, 0.4)
        x = 80 + i * (card_w + gap)
        y = 360 + (1 - a) * 40
        rounded(draw, (x, y, x + card_w, y + 360), fade(CARD, a), 24, fade(STROKE, a))
        center_text(draw, (x + card_w / 2, y + 80), name, font(24, "bold"), fade(INK, a))
        center_text(draw, (x + card_w / 2, y + 200), "observe", font(18, "medium"), fade(BLUE, a))
        center_text(draw, (x + card_w / 2, y + 240), "only", font(18, "medium"), fade(BLUE, a))
    center_text(
        draw,
        (W / 2, 860),
        "A browse is not a write.  A human still applies the map.",
        font(26, "medium"),
        fade(INK, appear(t, 2.4, 0.6)),
    )
    return image


def scene_two_ais(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "06", "Two AIs. Do not confuse them.", appear(t, 0.05))
    cols = [
        (BLUE, "BUILD", "Grok 4.6", "Writes code and tests.\nNever owns GPIO23."),
        (TEAL, "RUNTIME", "Fake", "Proven on CI and the\n12 Sep hardware."),
        (GOLD, "FALLBACK", "Claude, then OpenAI", "Live interpreters only.\nSame Edge API."),
    ]
    gap = 36
    card_w = (W - 160 - gap * 2) // 3
    for i, (accent, kicker, title, body) in enumerate(cols):
        a = appear(t, 0.35 + i * 1.1, 0.55)
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 280, x + card_w, 780), fade(CARD, a), 28, fade(accent, a * 0.75))
        draw.text((x + 40, 330), kicker, font=font(18, "bold"), fill=fade(accent, a))
        draw.text((x + 40, 400), title, font=font(40, "bold"), fill=fade(INK, a))
        y = 500
        for line in body.split("\n"):
            draw.text((x + 40, y), line, font=font(24), fill=fade(MUTED, a))
            y += 40
    center_text(
        draw,
        (W / 2, 900),
        "Benchmark: skill routing and tool discipline.  Not chat quality.",
        font(24, "medium"),
        fade(INK, appear(t, 3.6, 0.6)),
    )
    return image


def scene_gates(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "07", "Six gates, then a relay", appear(t, 0.05))
    labels = ["Read only", "Sidecar", "Observe", "Twin", "Actuate", "Restore"]
    gap = 28
    card_w = (W - 160 - gap * 5) // 6
    for i, name in enumerate(labels):
        a = appear(t, 0.3 + i * 0.35, 0.4)
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 360, x + card_w, 720), fade(CARD, a), 24, fade(TEAL, a * 0.6))
        center_text(draw, (x + card_w / 2, 420), str(i), font(40, "bold"), fade(TEAL, a))
        center_text(draw, (x + card_w / 2, 520), name, font(22, "medium"), fade(INK, a))
        center_text(draw, (x + card_w / 2, 620), "PASSED", font(16, "bold"), fade(TEAL, a))
    center_text(
        draw,
        (W / 2, 860),
        "Observe  →  simulate  →  arm  →  run  →  restore",
        font(26, "medium"),
        fade(INK, appear(t, 2.6, 0.6)),
    )
    return image


def scene_interview(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "08", "Capstone: a short interview", appear(t, 0.05))
    questions = [
        "What modules are here?",
        "Which bus? GPIO, MQTT, Modbus, OPC UA, S7, EIP, CAN",
        "Which pin, register, or tag is pressure? Flow?",
        "What are the trip numbers and units?",
        "What must stay observe-only?",
    ]
    for i, q in enumerate(questions):
        a = appear(t, 0.25 + i * 0.45, 0.4)
        y = 220 + i * 130 + (1 - a) * 24
        rounded(draw, (140, y, 1780, y + 108), fade(CARD, a), 22, fade(STROKE, a))
        draw.ellipse((180, y + 30, 236, y + 86), fill=fade(BLUE, a))
        center_text(draw, (208, y + 38), str(i + 1), font(22, "bold"), fade(BG, a))
        draw.text((280, y + 34), q, font=font(28, "medium"), fill=fade(INK, a))
    return image


def scene_loop(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.1)
    chapter(draw, "09", "Then a human. Then the twin. Then arm.", appear(t, 0.05))
    steps = [("Deploy", BLUE), ("Interview", GOLD), ("Human apply", TEAL), ("Twin", BLUE), ("Arm", RED)]
    gap = 28
    card_w = (W - 160 - gap * 4) // 5
    active = int(clamp((t - 0.4) / 1.1, 0, 4.99))
    for i, (name, accent) in enumerate(steps):
        a = appear(t, 0.25 + i * 0.35, 0.4)
        x = 80 + i * (card_w + gap)
        on = i <= active
        rounded(draw, (x, 400, x + card_w, 680), fade(CARD, a), 24, fade(accent if on else STROKE, a))
        center_text(draw, (x + card_w / 2, 500), name, font(26, "bold"), fade(INK, a))
        if i < 4:
            draw.polygon(
                [(x + card_w + 4, 530), (x + card_w + gap - 6, 540), (x + card_w + 4, 550)],
                fill=fade(STROKE, appear(t, 0.5 + i * 0.35, 0.3)),
            )
    center_text(
        draw,
        (W / 2, 840),
        "The interview is designed, not built.  The kernel still says yes.",
        font(26, "medium"),
        fade(INK, appear(t, 2.8, 0.6)),
    )
    return image


def scene_close(t: float) -> Image.Image:
    image, draw = canvas()
    grid(draw, 0.08)
    a = appear(t, 0.4, 0.8)
    center_text(draw, (W / 2, 360), "The AI can ask.", font(64, "bold"), fade(INK, a))
    center_text(draw, (W / 2, 470), "Only the kernel can say yes.", font(64, "bold"), fade(TEAL, appear(t, 1.3, 0.7)))
    center_text(
        draw,
        (W / 2, 680),
        "Phase 3 is complete.  Capstone: any mapped bench, short interview.",
        font(24, "medium"),
        fade(MUTED, appear(t, 2.4, 0.6)),
    )
    return image


def scene_record(label: str, detail: str):
    def painter(t: float) -> Image.Image:
        image, draw = canvas()
        a = appear(t, 0.15, 0.4)
        center_text(draw, (W / 2, 360), "YOU RECORD THIS", font(22, "bold"), fade(GOLD, a))
        center_text(draw, (W / 2, 460), label, font(54, "bold"), fade(INK, a))
        center_text(draw, (W / 2, 580), detail, font(26, "medium"), fade(MUTED, appear(t, 0.5, 0.5)))
        return image

    return painter


SCENES: list[tuple[str, float, object]] = [
    ("01_title", 6.0, scene_title),
    ("02_question", 8.0, scene_question),
    ("03_language_stops", 8.5, scene_language),
    ("04_architecture", 8.5, scene_architecture),
    ("05_and_gate", 9.5, scene_and_gate),
    ("06_protocols", 7.5, scene_protocols),
    ("07_two_ais", 8.5, scene_two_ais),
    ("08_six_gates", 7.5, scene_gates),
    ("R1_record_dashboard", 4.5, scene_record("Phase 3 dashboard", "45 seconds  ·  port 8080  ·  observe only  ·  do not arm")),
    ("R2_record_studio", 4.5, scene_record("Studio demo", "Live → Agent “4.2 bar” → trip → 15 L/min → shutdown → Evidence")),
    ("09_interview", 8.5, scene_interview),
    ("10_capstone_loop", 8.0, scene_loop),
    ("11_close", 7.0, scene_close),
]


def concat_lookbook(clips: list[Path]) -> None:
    listing = OUT / "lookbook.txt"
    listing.write_text("".join(f"file '{path.name}'\n" for path in clips))
    dest = OUT / "LOOKBOOK.mp4"
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", str(dest),
        ]
    )
    print(f"wrote {dest.relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    for name, duration, painter in SCENES:
        path = OUT / f"{name}.mp4"
        encode(path, duration, painter)
        clips.append(path)
    concat_lookbook(clips)


if __name__ == "__main__":
    main()
