"""Temp-file then replace. Reviewers treat a partial zip as not a bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_bytes_atomic(path: str | Path, data: bytes) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return target


def write_text_atomic(path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    return write_bytes_atomic(path, text.encode(encoding))


def write_json_atomic(path: str | Path, document: Any, *, indent: int = 2) -> Path:
    return write_text_atomic(path, json.dumps(document, indent=indent, sort_keys=True))
