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
    interviews = "/v1/commissioning/interviews"
    if interviews in paths:
        paths[interviews]["post"]["responses"] = {"201": {"description": "Inert interview draft created"}}
        paths[interviews]["get"]["description"] = "List persisted drafts. Sources are operator-provided references; fixture interpretation is deterministic."
        update = {"description": "Save answers with optimistic revision matching. Unrecognized text remains unresolved. Does not change active configuration.", "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["expected_revision"], "properties": {"expected_revision": {"type": "integer"}, "answers": {"type": "object"}, "sources": {"type": "object", "additionalProperties": {"type": "string", "minLength": 1}}, "text": {"type": "string"}}}}}}, "responses": {"200": {"description": "Draft saved"}, "409": {"description": "Stale interview revision"}}}
        paths[interviews + "/{interview_id}"]["patch"].update(update)
        paths[interviews + "/{interview_id}/answers"]["post"].update(update)
        paths[interviews + "/{interview_id}/propose"]["post"]["description"] = "Validate sources, units, calibration and supported procedures. Returns needs_evidence with blockers or proposed with a configuration diff and revalidation checklist. Never applies configuration."
        paths["/v1/rig/apply"]["post"]["description"] = "Operator-only application with expected_current_hash. When supplying interview_id also supply interview_revision; the proposed document must match exactly. Material changes invalidate approvals/reviews and preserve configuration history."
        paths["/v1/rig/propose"]["post"]["description"] = "Validate proposed configuration and return semantic revalidation requirements. Rig-level/unclassified changes require full qualification."
        paths["/v1/commissioning/physical"]["post"].update({"description": "Operator-attested observation, attended trial or acceptance of a specific Pi configuration/wiring revision. Requires hashed physical qualification records and their raw artifacts. Trials expire after 30 minutes and on restart. Accepted procedures require passing physical trials. Not safety certification.", "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "required": ["stage", "expected_config_hash", "wiring_revision", "procedure_ids", "attest_reviewed", "checks"], "properties": {"stage": {"enum": ["observation", "trial", "accepted"]}, "expected_config_hash": {"type": "string"}, "wiring_revision": {"type": "string"}, "procedure_ids": {"type": "array", "items": {"type": "string"}}, "attest_reviewed": {"type": "boolean"}, "checks": {"type": "object", "description": "Named checks mapped to local path and SHA-256. JSON records must include exact config/wiring identity, passed=true, evidence_kind=physical and raw artifact references."}}}}}}, "responses": {"201": {"description": "Review retained with readiness"}, "403": {"description": "Human operator required"}, "409": {"description": "Missing, stale or incompatible qualification"}}})
    if "/v1/sandboxes" in paths:
        for path, operations in paths.items():
            if path.startswith("/v1/sandboxes"):
                for operation in operations.values():
                    operation.update(description="Authenticated local sandbox broker operation. No physical authority. Disabled/unavailable isolation returns503; invalid or stale experiment returns409. Generated code never runs on the host.", security=[{"operatorKey": []}, {"agentKey": []}, {"session": []}])
        requests = {"/v1/sandboxes": {"source": {"enum": ["active", "thermal", "pressure_flow", "interview"]}, "procedure_id": {"type": "string"}, "interview_id": {"type": "string"}, "recording_id": {"enum": ["latest"]}, "seed": {"type": "integer"}},
                    "/v1/sandboxes/{sandbox_id}/jobs": {"kind": {"enum": ["python", "spice", "rehearsal"]}, "source": {"type": "string", "maxLength": 256000}},
                    "/v1/sandboxes/{sandbox_id}/revisions": {"expected_revision": {"type": "integer"}, "document": {"type": "object"}, "procedure": {"type": "object"}},
                    "/v1/sandboxes/{sandbox_id}/proposals": {"job_id": {"type": "string"}, "kind": {"enum": ["configuration", "procedure"]}}}
        for path, properties in requests.items():
            paths[path]["post"]["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": properties, "additionalProperties": False}}}}
        paths["/v1/sandboxes/{sandbox_id}/export"]["get"]["responses"] = {"200": {"description": "Checksummed sandbox ZIP; numerical replay does not authenticate origin without local broker"}, "409": {"description": "Active job or missing/corrupt evidence"}}
    return {
        "components": {"securitySchemes": {"operatorKey": {"type": "apiKey", "in": "header", "name": "X-CertaRig-Operator-Key"}, "agentKey": {"type": "apiKey", "in": "header", "name": "X-CertaRig-Agent-Key"}, "session": {"type": "apiKey", "in": "header", "name": "X-CertaRig-Session"}}},
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
