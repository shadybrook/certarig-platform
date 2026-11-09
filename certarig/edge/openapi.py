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
    if "/v1/commissioning/review" in paths:
        paths["/v1/commissioning/review"]["post"].update({
            "description": "Operator-only review bound to current config, adapter and approved procedure revisions. Simulator readiness does not accept physical commissioning.",
            "requestBody": {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "required": ["expected_config_hash", "procedure_ids"],
                "properties": {"expected_config_hash": {"type": "string"}, "procedure_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}}},
            }}}},
            "responses": {"201": {"description": "Reviewed simulator configuration"}, "403": {"description": "Operator required"}, "409": {"description": "Stale configuration, invalid observations or physical acceptance required"}},
        })
        paths["/v1/commissioning"]["get"]["description"] = "Read readiness, blockers, evidence kind and current versioned commissioning record; optional procedure_id query selects one procedure."
    if "/v1/procedure_runs" in paths:
        paths["/v1/procedure_runs"]["post"].update({
            "description": "Start a named approved procedure. commissioning_required profiles require a single-use approval for every principal. Approval binds requester role/name, exact args, contract, adapter and procedure hash.",
            "requestBody": {"content": {"application/json": {"schema": {"type": "object", "required": ["procedure_id"], "properties": {"procedure_id": {"type": "string"}, "label": {"type": "string"}, "approval_id": {"type": "string"}}}}}},
            "responses": {"201": {"description": "Run started"}, "403": {"description": "Invalid, expired, mismatched or reused approval"}, "409": {"description": "Readiness or contract prevents start"}, "428": {"description": "Request human approval, then retry with approval_id"}},
        })
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
