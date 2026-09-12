"""OpenAPI 3 document generated from the Edge route table."""

from __future__ import annotations

from typing import Any

from .server import EdgeNode


def routes_from(node: EdgeNode) -> list[tuple[str, str]]:
    return [(route.method, route.path) for route in node.router.routes]


def generate_openapi(node: EdgeNode) -> dict[str, Any]:
    paths: dict[str, Any] = {}
    for method, path in routes_from(node):
        item = paths.setdefault(path, {})
        item[method.lower()] = {
            "summary": f"{method} {path}",
            "responses": {"200": {"description": "Success"}},
        }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "CertaRig Edge API",
            "version": "0.4.0",
            "description": "Deterministic kernel, procedures, approvals, evidence. Generated from the live route table.",
        },
        "paths": paths,
    }


def render_yaml(document: dict[str, Any]) -> str:
    import yaml

    return yaml.safe_dump(document, sort_keys=False)
