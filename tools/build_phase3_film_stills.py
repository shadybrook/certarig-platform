#!/usr/bin/env python3
"""Render 16:9 Phase 3 film title, AI, protocol, equation, mission, and close cards."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "explainer" / "phase3-film" / "stills"

INK = "#172523"
MUTED = "#66736f"
GREEN = "#1f7a61"
GREEN_LIGHT = "#d8eee5"
BLUE = "#33658a"
BLUE_LIGHT = "#d9e8f1"
GOLD = "#c58a26"
GOLD_LIGHT = "#f5e8c9"
RED = "#b44b42"
RED_LIGHT = "#f4dddd"
GRID = "#dfe5e2"
PAPER = "#fbfcfb"
WHITE = "#ffffff"

FONT = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"
FONT_MED = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/macos/Inter-Bold.ttf"

W, H = 1920, 1080


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    path = {"regular": FONT, "medium": FONT_MED, "bold": FONT_BOLD}[weight]
    return ImageFont.truetype(path, size=size)


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (W, H), PAPER)
    return image, ImageDraw.Draw(image)


def save(image: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / name
    image.save(dest, "PNG", optimize=True)
    print(dest)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, radius: int = 28) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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


def title_card() -> None:
    image, draw = canvas()
    draw.rectangle((0, 0, W, H), fill=WHITE)
    heading = font(92, "bold")
    sub = font(28, "medium")
    faint = font(22, "regular")
    text = "What is CertaRig?"
    tw = draw.textlength(text, font=heading)
    draw.text(((W - tw) / 2, 390), text, font=heading, fill=INK)
    presented = "Presented by Chintan Dedhia"
    pw = draw.textlength(presented, font=sub)
    draw.text(((W - pw) / 2, 530), presented, font=sub, fill=MUTED)
    line = "Phase 3 submission  ·  CertaRig"
    lw = draw.textlength(line, font=faint)
    draw.text(((W - lw) / 2, 920), line, font=faint, fill=MUTED)
    save(image, "00_title.png")


def protocol_strip() -> None:
    image, draw = canvas()
    draw.text((80, 70), "Same kernel. Different buses.", font=font(48, "bold"), fill=INK)
    draw.text(
        (80, 140),
        "Every fieldbus example ships observe-only. A browse is not a write.",
        font=font(24, "regular"),
        fill=MUTED,
    )
    draw.line((80, 200, W - 80, 200), fill=GRID, width=2)
    buses = [
        ("MQTT", "Topics on a broker"),
        ("Modbus", "TCP or RTU registers"),
        ("OPC UA", "Modern PLC / SCADA"),
        ("Siemens S7", "Native data blocks"),
        ("EtherNet/IP", "Allen-Bradley tags"),
        ("CAN", "Vehicle / battery"),
    ]
    gap = 28
    card_w = (W - 160 - gap * 5) // 6
    top = 280
    for i, (name, blurb) in enumerate(buses):
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, top, x + card_w, 820), WHITE, 24)
        draw.rounded_rectangle((x, top, x + card_w, 820), radius=24, outline=GRID, width=2)
        draw.ellipse((x + card_w / 2 - 18, top + 48, x + card_w / 2 + 18, top + 84), fill=GREEN_LIGHT)
        draw.ellipse((x + card_w / 2 - 8, top + 58, x + card_w / 2 + 8, top + 74), fill=GREEN)
        name_font = font(26, "bold")
        nw = draw.textlength(name, font=name_font)
        draw.text((x + (card_w - nw) / 2, top + 130), name, font=name_font, fill=INK)
        y = top + 200
        for line in wrap(draw, blurb, font(20), card_w - 40):
            lw = draw.textlength(line, font=font(20))
            draw.text((x + (card_w - lw) / 2, y), line, font=font(20), fill=MUTED)
            y += 32
        badge = "observe only"
        bw = draw.textlength(badge, font=font(16, "medium"))
        bx = x + (card_w - bw) / 2
        rounded(draw, (bx - 16, 730, bx + bw + 16, 778), BLUE_LIGHT, 14)
        draw.text((bx, 740), badge, font=font(16, "medium"), fill=BLUE)
    draw.text(
        (80, 940),
        "A human still applies the map. Twin-gate plus explicit arm before any output.",
        font=font(22),
        fill=MUTED,
    )
    save(image, "05_protocol_strip.png")


def ai_stack() -> None:
    image, draw = canvas()
    draw.text((80, 64), "Two AIs. They must not be confused.", font=font(46, "bold"), fill=INK)
    draw.text(
        (80, 132),
        "Grok builds the product. Fake runs the proven bench path. Claude and OpenAI are live interpreters only.",
        font=font(22),
        fill=MUTED,
    )
    draw.line((80, 190, W - 80, 190), fill=GRID, width=2)
    columns = [
        (BLUE_LIGHT, BLUE, "Build-time", "Grok 4.6", "Cursor assistant for code, tests, and this film pack. Fallback: another Cursor model, Claude, or GPT. Never owns GPIO23."),
        (GREEN_LIGHT, GREEN, "Runtime default", "Fake", "Deterministic rule policy. No API key. CI and the 12 Sep hardware procedures. Selects pressure_guardrail and flow_guardrail from operator English."),
        (GOLD_LIGHT, GOLD, "Live fallbacks", "Claude, then OpenAI", "Intended live interpreter: Claude Sonnet 4.5. Second choice: GPT-4.1-mini or any OpenAI-compatible base URL. ReplayProvider for exact transcripts."),
    ]
    gap = 36
    card_w = (W - 160 - gap * 2) // 3
    for i, (bg, accent, kicker, title, body) in enumerate(columns):
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 240, x + card_w, 900), WHITE, 28)
        draw.rounded_rectangle((x, 240, x + card_w, 900), radius=28, outline=GRID, width=2)
        rounded(draw, (x + 36, 280, x + 220, 332), bg, 12)
        draw.text((x + 52, 290), kicker.upper(), font=font(16, "bold"), fill=accent)
        draw.text((x + 36, 360), title, font=font(40, "bold"), fill=INK)
        y = 450
        for line in wrap(draw, body, font(22), card_w - 80):
            draw.text((x + 36, y), line, font=font(22), fill=MUTED)
            y += 34
    save(image, "06_ai_stack.png")


def ai_benchmark() -> None:
    image, draw = canvas()
    draw.text((80, 70), "Benchmark this use case, not trivia.", font=font(46, "bold"), fill=INK)
    draw.text(
        (80, 140),
        "Live Anthropic and OpenAI adapters exist. The 12 Sep lab used Fake. Do not pretend otherwise.",
        font=font(22),
        fill=MUTED,
    )
    draw.line((80, 200, W - 80, 200), fill=GRID, width=2)
    rows = [
        ("Skill routing", "“4.2 bar” selects pressure_guardrail. “15 L/min” selects flow_guardrail."),
        ("Tool discipline", "Only capability-manifest tools. No bypass_interlock. No override_limits."),
        ("Numeric boundary", "The model never compares 4.2 bar or 15 L/min. The kernel does."),
        ("Human gates", "reset_trip and shutdown stop until a person grants approval."),
        ("Provider swap", "Fake, Claude, OpenAI, or Replay share the same Edge API."),
    ]
    y = 240
    for title, body in rows:
        rounded(draw, (80, y, W - 80, y + 130), WHITE, 20)
        draw.rounded_rectangle((80, y, W - 80, y + 130), radius=20, outline=GRID, width=2)
        draw.ellipse((110, y + 48, 142, y + 80), fill=GREEN)
        draw.text((180, y + 28), title, font=font(28, "bold"), fill=INK)
        draw.text((180, y + 72), body, font=font(22), fill=MUTED)
        y += 150
    save(image, "07_ai_benchmark.png")


def output_equation() -> None:
    image, draw = canvas()
    draw.text((80, 80), "The output turns on only when every term is true.", font=font(42, "bold"), fill=INK)
    draw.text((80, 150), "Remove any one condition and the lamp stays dark.", font=font(24), fill=MUTED)
    draw.line((80, 210, W - 80, 210), fill=GRID, width=2)
    terms = [
        ("enabled", "Actuation is on"),
        ("permit", "Permit requested"),
        ("¬trip", "No trip latched"),
        ("E-stop closed", "Safety loop healthy"),
        ("process healthy", "Signals valid"),
    ]
    gap = 24
    card_w = (W - 160 - gap * 4) // 5
    for i, (name, blurb) in enumerate(terms):
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 280, x + card_w, 620), GREEN_LIGHT, 24)
        nf = font(26, "bold")
        nw = draw.textlength(name, font=nf)
        draw.text((x + (card_w - nw) / 2, 360), name, font=nf, fill=GREEN)
        y = 430
        for line in wrap(draw, blurb, font(20), card_w - 36):
            lw = draw.textlength(line, font=font(20))
            draw.text((x + (card_w - lw) / 2, y), line, font=font(20), fill=INK)
            y += 30
    rounded(draw, (80, 700, W - 80, 900), WHITE, 28)
    draw.rounded_rectangle((80, 700, W - 80, 900), radius=28, outline=GRID, width=2)
    eq = "OUTPUT = enabled  AND  permit  AND  ¬trip  AND  E-stop closed  AND  healthy"
    ef = font(30, "bold")
    ew = draw.textlength(eq, font=ef)
    draw.text(((W - ew) / 2, 760), eq, font=ef, fill=INK)
    note = "After a trip: healthy inputs, then explicit reset, then a new permit. Never auto-restart."
    nw = draw.textlength(note, font=font(22))
    draw.text(((W - nw) / 2, 820), note, font=font(22), fill=MUTED)
    save(image, "08_output_equation.png")


def interview_card() -> None:
    image, draw = canvas()
    draw.text((80, 64), "A short commissioning interview", font=font(46, "bold"), fill=INK)
    draw.text(
        (80, 132),
        "The agent asks. It does not energize. Design for capstone — not built yet.",
        font=font(22),
        fill=MUTED,
    )
    draw.line((80, 190, W - 80, 190), fill=GRID, width=2)
    questions = [
        ("1", "What modules are here?", "Pots, ADC, E-stop, relay, PLC, other"),
        ("2", "Which bus?", "GPIO/ADC, MQTT, Modbus, OPC UA, S7, EtherNet/IP, CAN"),
        ("3", "Which pin, register, or tag?", "Pressure, flow, temperature — mapped, not guessed"),
        ("4", "What are the trip numbers?", "Units and limits the kernel will compare"),
        ("5", "What must stay observe-only?", "A browse is never a write"),
    ]
    y = 230
    for num, title, body in questions:
        rounded(draw, (80, y, W - 80, y + 130), WHITE, 20)
        draw.rounded_rectangle((80, y, W - 80, y + 130), radius=20, outline=GRID, width=2)
        draw.ellipse((120, y + 36, 184, y + 100), fill=BLUE_LIGHT)
        nw = draw.textlength(num, font=font(28, "bold"))
        draw.text((152 - nw / 2, y + 50), num, font=font(28, "bold"), fill=BLUE)
        draw.text((220, y + 28), title, font=font(30, "bold"), fill=INK)
        draw.text((220, y + 76), body, font=font(22), fill=MUTED)
        y += 150
    save(image, "10_interview.png")


def map_locked() -> None:
    image, draw = canvas()
    draw.text((80, 70), "The map is a proposal, not permission.", font=font(44, "bold"), fill=INK)
    draw.text((80, 140), "A diagram or a chat answer cannot reach GPIO23.", font=font(24), fill=MUTED)
    draw.line((80, 200, W - 80, 200), fill=GRID, width=2)
    steps = [
        (BLUE_LIGHT, BLUE, "Agent", "Proposes rig.json from the interview"),
        (GOLD_LIGHT, GOLD, "Human", "Reviews and applies the map"),
        (GREEN_LIGHT, GREEN, "Twin", "Same procedure hash must pass in simulation"),
        (RED_LIGHT, RED, "Arm", "Explicit actuation. Kernel still compares."),
    ]
    gap = 32
    card_w = (W - 160 - gap * 3) // 4
    for i, (bg, accent, title, body) in enumerate(steps):
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 280, x + card_w, 780), WHITE, 28)
        draw.rounded_rectangle((x, 280, x + card_w, 780), radius=28, outline=GRID, width=2)
        rounded(draw, (x + 36, 320, x + 200, 376), bg, 12)
        draw.text((x + 52, 332), title.upper(), font=font(18, "bold"), fill=accent)
        y = 430
        for line in wrap(draw, body, font(26, "bold"), card_w - 72):
            draw.text((x + 36, y), line, font=font(26, "bold"), fill=INK)
            y += 40
        if i < 3:
            draw.polygon(
                [(x + card_w + 4, 520), (x + card_w + gap - 4, 540), (x + card_w + 4, 560)],
                fill=GRID,
            )
    note = "Never auto-energize from a guessed map."
    nw = draw.textlength(note, font=font(24, "medium"))
    draw.text(((W - nw) / 2, 880), note, font=font(24, "medium"), fill=RED)
    save(image, "11_map_locked.png")


def capstone_loop() -> None:
    image, draw = canvas()
    draw.text((80, 64), "Capstone is this loop, not a hydraulic plant.", font=font(42, "bold"), fill=INK)
    draw.text(
        (80, 128),
        "Phase 3 proved the kernel on one mapped dry bench. Capstone puts the same system on their bench.",
        font=font(22),
        fill=MUTED,
    )
    draw.line((80, 190, W - 80, 190), fill=GRID, width=2)
    items = [
        ("Deploy", "Install CertaRig on their Pi, IPC, or laptop."),
        ("Interview", "Modules, bus, pins or tags, trips, observe-only."),
        ("Human apply", "Proposed rig.json does nothing until a person applies it."),
        ("Twin, then arm", "Exact procedure hash in simulation, then explicit arm."),
        ("Kernel", "Still the only thing allowed to say yes."),
    ]
    y = 230
    for title, body in items:
        rounded(draw, (80, y, W - 80, y + 130), WHITE, 20)
        draw.rounded_rectangle((80, y, W - 80, y + 130), radius=20, outline=GRID, width=2)
        draw.ellipse((118, y + 46, 150, y + 78), fill=GREEN)
        draw.text((180, y + 24), title, font=font(28, "bold"), fill=INK)
        draw.text((180, y + 72), body, font=font(22), fill=MUTED)
        y += 148
    save(image, "13_capstone_loop.png")


def any_rig_card() -> None:
    image, draw = canvas()
    draw.text((80, 80), "The same agent, on their rig.", font=font(52, "bold"), fill=INK)
    draw.text(
        (80, 170),
        "A Pi. An industrial PC. A laptop talking to their controller.",
        font=font(26),
        fill=MUTED,
    )
    hosts = [
        ("Raspberry Pi", "GPIO + ADC dry bench, already proven"),
        ("Industrial PC", "Sits next to the existing PLC / HMI"),
        ("Laptop + bus", "MQTT, Modbus, OPC UA, S7, EIP, CAN"),
    ]
    gap = 36
    card_w = (W - 160 - gap * 2) // 3
    for i, (title, body) in enumerate(hosts):
        x = 80 + i * (card_w + gap)
        rounded(draw, (x, 300, x + card_w, 780), WHITE, 28)
        draw.rounded_rectangle((x, 300, x + card_w, 780), radius=28, outline=GRID, width=2)
        draw.ellipse((x + card_w / 2 - 36, 380, x + card_w / 2 + 36, 452), fill=GREEN_LIGHT)
        draw.ellipse((x + card_w / 2 - 16, 400, x + card_w / 2 + 16, 432), fill=GREEN)
        tf = font(30, "bold")
        tw = draw.textlength(title, font=tf)
        draw.text((x + (card_w - tw) / 2, 500), title, font=tf, fill=INK)
        y = 580
        for line in wrap(draw, body, font(22), card_w - 80):
            lw = draw.textlength(line, font=font(22))
            draw.text((x + (card_w - lw) / 2, y), line, font=font(22), fill=MUTED)
            y += 34
    draw.text((80, 900), "Not: an AI that discovers an unknown machine from a photograph and drives it.", font=font(22), fill=MUTED)
    save(image, "09_any_rig.png")


def close_card() -> None:
    image, draw = canvas()
    draw.rectangle((0, 0, W, H), fill=WHITE)
    kicker = "Phase 3 is complete. Capstone: any mapped bench, short interview."
    kw = draw.textlength(kicker, font=font(24, "medium"))
    draw.text(((W - kw) / 2, 280), kicker, font=font(24, "medium"), fill=MUTED)
    line1 = "The AI can ask."
    line2 = "Only the kernel can say yes."
    f1 = font(64, "bold")
    w1 = draw.textlength(line1, font=f1)
    draw.text(((W - w1) / 2, 400), line1, font=f1, fill=INK)
    w2 = draw.textlength(line2, font=f1)
    draw.text(((W - w2) / 2, 490), line2, font=f1, fill=GREEN)
    foot = "CertaRig  ·  Phase 3 submission"
    fw = draw.textlength(foot, font=font(22))
    draw.text(((W - fw) / 2, 900), foot, font=font(22), fill=MUTED)
    save(image, "14_close.png")


def main() -> None:
    title_card()
    protocol_strip()
    ai_stack()
    ai_benchmark()
    output_equation()
    any_rig_card()
    interview_card()
    map_locked()
    capstone_loop()
    close_card()


if __name__ == "__main__":
    main()
