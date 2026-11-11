#!/usr/bin/env python3
"""Download the Phase 3 source footage onto the cloud machine.

Accepts a manifest JSON mapping canonical names to URLs. Google Drive share
links are handled via gdown (installed on demand); anything else is plain HTTP.

Canonical names expected by the EDLs:
    screen       Screen recording of the test bench run (Mac, 2880x1800)
    topdown      Dry test bench top-down recording (phone, HEVC)
    narr_1_5     Section 1-5 narration
    narr_6       Section 6 narration (audio is what matters)
    narr_7_9     Section 7-9 narration

Usage:
    python3 fetch_footage.py manifest.json --dest /workspace/footage
Example manifest:
    {"screen": "https://drive.google.com/file/d/FILE_ID/view?usp=sharing", ...}
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

EXPECTED = {"screen", "topdown", "narr_1_5", "narr_6", "narr_7_9"}


def is_drive(url: str) -> bool:
    return "drive.google.com" in url or "docs.google.com" in url


def drive_id(url: str) -> str | None:
    m = re.search(r"/d/([\w-]{20,})", url) or re.search(r"[?&]id=([\w-]{20,})", url)
    return m.group(1) if m else None


def fetch(name: str, url: str, dest: Path) -> Path:
    out = dest / f"{name}.mov"
    if out.exists() and out.stat().st_size > 0:
        print(f"{name}: already present ({out.stat().st_size / 1e6:.0f} MB)")
        return out
    if is_drive(url):
        try:
            import gdown  # noqa: F401
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gdown"],
                           check=True)
            import gdown  # noqa: F401
        import gdown
        fid = drive_id(url)
        target = f"https://drive.google.com/uc?id={fid}" if fid else url
        got = gdown.download(target, str(out), quiet=False, fuzzy=True)
        if not got:
            raise SystemExit(f"{name}: gdown failed for {url} — is the link "
                             "'anyone with the link can view'?")
    else:
        print(f"{name}: downloading {url}")
        urllib.request.urlretrieve(url, out)
    print(f"{name}: {out.stat().st_size / 1e6:.0f} MB")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--dest", type=Path, default=Path("/workspace/footage"))
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    missing = EXPECTED - set(manifest)
    if missing:
        print(f"note: manifest missing {sorted(missing)}", file=sys.stderr)
    args.dest.mkdir(parents=True, exist_ok=True)
    for name, url in manifest.items():
        fetch(name, url, args.dest)

    for f in sorted(args.dest.iterdir()):
        d = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout.strip()
        print(f"  {f.name}: {float(d or 0):.1f}s")


if __name__ == "__main__":
    main()
