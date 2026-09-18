#!/usr/bin/env python3
"""Build CertaRig_Phase3_Document.docx from CertaRig_Phase3_Document.md.

Renders headings, paragraphs, bullet lists, and pipe tables with python-docx,
and produces a real cover page from the Cover Page section of the markdown.

Usage:
    pip install python-docx
    python build_docx.py
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MD_PATH = HERE / "CertaRig_Phase3_Document.md"
DOCX_PATH = HERE / "CertaRig_Phase3_Document.docx"
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.+?)\)$")

BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def add_runs(paragraph, text: str) -> None:
    """Add runs to a paragraph, honouring **bold**, *italic*, and `code`."""
    token_re = re.compile(r"(\*\*.+?\*\*|`[^`]+`|(?<!\*)\*[^*]+\*(?!\*))")
    for part in token_re.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
        else:
            paragraph.add_run(part)


def split_table_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*", line))


def parse_blocks(lines: list[str]):
    """Yield (kind, payload) blocks: heading, bullet, table, hr, para, blank_sig."""
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "---":
            yield ("hr", None)
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            yield ("heading", (len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        img = IMAGE_RE.match(stripped)
        if img:
            yield ("figure", (img.group(1).strip(), img.group(2).strip()))
            i += 1
            continue
        if stripped.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                if not is_separator_row(lines[i]):
                    rows.append(split_table_row(lines[i]))
                i += 1
            yield ("table", rows)
            continue
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).rstrip())
                i += 1
            yield ("bullets", items)
            continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if m:
            items = []
            while i < n:
                m2 = re.match(r"^\s*\d+\.\s+(.*)$", lines[i])
                if not m2:
                    break
                items.append(m2.group(1).rstrip())
                i += 1
            yield ("numbered", items)
            continue
        # signature/blank lines rendered as-is
        if set(stripped) <= {"_"}:
            yield ("blank_line", None)
            i += 1
            continue
        # plain paragraph (join soft-wrapped lines until a blank or structural line)
        para_lines = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (not nxt or nxt == "---" or nxt.startswith("#") or nxt.startswith("|")
                    or nxt.startswith("![") or re.match(r"^\s*[-*]\s+", lines[i])
                    or re.match(r"^\s*\d+\.\s+", lines[i])
                    or set(nxt) <= {"_"}):
                break
            para_lines.append(nxt)
            i += 1
        yield ("para", " ".join(para_lines))


def style_base(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)


def build_cover_page(doc: Document, cover_rows: list[list[str]]) -> None:
    fields = {row[0]: row[1] for row in cover_rows[1:] if len(row) >= 2}

    for _ in range(5):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(fields.get("Course Title", "[Course Title]"))
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Phase 3 — Implementation Readiness & Validation")
    run.font.size = Pt(20)
    run.bold = True

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(fields.get("Project Title", "CertaRig"))
    run.font.size = Pt(26)
    run.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

    for _ in range(4):
        doc.add_paragraph()

    detail_order = [
        ("Student Name", fields.get("Student Name", "")),
        ("Student ID", fields.get("Student ID", "")),
        ("Project Advisor / Supervisor", fields.get("Project Advisor / Supervisor", "")),
        ("Date of Submission", fields.get("Date of Submission", "")),
    ]
    for label, value in detail_order:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"{label}: ")
        run.bold = True
        run.font.size = Pt(13)
        run = p.add_run(value)
        run.font.size = Pt(13)

    # page break after the cover
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def resolve_image(src: str) -> Path:
    raw = Path(src)
    candidates = [
        raw if raw.is_absolute() else None,
        HERE / src,
        REPO / src,
    ]
    for path in candidates:
        if path is not None and path.exists():
            return path
    raise FileNotFoundError(f"Figure not found: {src}")


def add_figure(doc: Document, src: str, caption: str) -> None:
    path = resolve_image(src)
    picture = doc.add_paragraph()
    picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = picture.add_run()
    run.add_picture(str(path), width=Inches(6.3))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = cap.add_run(caption)
    cap_run.italic = True
    cap_run.font.size = Pt(10)
    cap_run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    doc.add_paragraph()


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        for ci in range(ncols):
            text = row[ci] if ci < len(row) else ""
            cell = table.cell(ri, ci)
            cell.paragraphs[0].text = ""
            add_runs(cell.paragraphs[0], text)
            for para in cell.paragraphs:
                for run in para.runs:
                    if ri == 0:
                        run.bold = True
                    if run.font.size is None:
                        run.font.size = Pt(10)
    doc.add_paragraph()


def main() -> None:
    lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    blocks = list(parse_blocks(lines))

    doc = Document()
    style_base(doc)

    # Locate the cover-page table: first table after the "Cover Page" heading.
    cover_rows = None
    body_blocks = []
    seen_cover_heading = False
    cover_consumed = False
    skip_next_hr = False
    for kind, payload in blocks:
        if not cover_consumed:
            if kind == "heading" and payload[1].lower().startswith("cover page"):
                seen_cover_heading = True
                continue
            if kind == "heading" and payload[0] == 1 and not seen_cover_heading:
                continue  # markdown document title; the cover replaces it
            if seen_cover_heading and kind == "table":
                cover_rows = payload
                cover_consumed = True
                skip_next_hr = True
                continue
            if kind == "hr":
                continue
            body_blocks.append((kind, payload))
            continue
        if skip_next_hr and kind == "hr":
            skip_next_hr = False
            continue
        body_blocks.append((kind, payload))

    if cover_rows is None:
        raise SystemExit("Cover Page table not found in the markdown source.")

    build_cover_page(doc, cover_rows)

    for kind, payload in body_blocks:
        if kind == "heading":
            level, text = payload
            doc.add_heading(text, level=min(level, 4))
        elif kind == "para":
            p = doc.add_paragraph()
            add_runs(p, payload)
        elif kind == "bullets":
            for item in payload:
                p = doc.add_paragraph(style="List Bullet")
                add_runs(p, item)
        elif kind == "numbered":
            for item in payload:
                p = doc.add_paragraph(style="List Number")
                add_runs(p, item)
        elif kind == "table":
            add_table(doc, payload)
        elif kind == "figure":
            caption, src = payload
            add_figure(doc, src, caption)
        elif kind == "blank_line":
            p = doc.add_paragraph()
            p.add_run("_" * 65)
        elif kind == "hr":
            continue

    doc.save(DOCX_PATH)
    print(f"Wrote {DOCX_PATH}")


if __name__ == "__main__":
    main()
