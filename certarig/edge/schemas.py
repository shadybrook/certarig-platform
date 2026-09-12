"""Access to the JSON Schemas that define the CertaRig rig contract.

Schemas ship inside the package (``certarig/schemas``) so that a deployed Edge
node validates against exactly the contract it was built with.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


@cache
def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError(f"schema {name} must be a JSON object")
    Draft202012Validator.check_schema(schema)
    return schema


@cache
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name))


def schema_errors(instance: Any, name: str) -> list[str]:
    """Return human-readable schema violations, sorted by JSON path."""
    errors = sorted(_validator(name).iter_errors(instance), key=lambda error: list(error.absolute_path))
    messages: list[str] = []
    for error in errors:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    return messages


def validate_against_schema(instance: Any, name: str, error_type: type[Exception] = ValueError) -> None:
    errors = schema_errors(instance, name)
    if errors:
        raise error_type(f"{name} validation failed: " + "; ".join(errors))
