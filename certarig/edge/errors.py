"""English catalog for Edge error codes. Studio and the SDK use this, not raw JSON."""

from __future__ import annotations

from typing import Any

CATALOG: dict[str, dict[str, str]] = {
    "stale_contract": {
        "title": "This page is out of date",
        "next": "Studio will re-read the rig contract and retry once. If it fails again, reload the page.",
    },
    "approval_required": {
        "title": "A human has to approve this",
        "next": "Open the Approvals inbox, grant or deny the request, then the agent can retry.",
    },
    "approval_invalid": {
        "title": "That approval cannot be used",
        "next": "Approvals are single-use and bound to the original tool arguments. Request a new one.",
    },
    "twin_gate": {
        "title": "This procedure has not passed on the twin",
        "next": "Run the same procedure on the simulator first. A pass is valid for 24 hours.",
    },
    "twin_gate_stale": {
        "title": "The twin pass is older than 24 hours",
        "next": "Re-run the procedure on the simulator, then try the bench again.",
    },
    "unclean_boot": {
        "title": "The last shutdown was not clean",
        "next": "Inspect the bench, then acknowledge the unclean boot before actuation can be armed.",
    },
    "observe_only": {
        "title": "This adapter is in observe mode",
        "next": "Evidence and telemetry are allowed. Flip command tools in capabilities only after review.",
    },
    "restart_required": {
        "title": "The new config needs a process restart",
        "next": "Hardware mode or ADC map changed. Restart the Edge node; limits-only edits apply live.",
    },
    "no_agent": {
        "title": "No agent key is configured on this node",
        "next": "Set CERTARIG_AGENT_KEY (different from the operator key) and restart.",
    },
    "tool_not_available": {
        "title": "That tool is not on this rig",
        "next": "The capability manifest does not expose it. Ask an engineer to change the manifest.",
    },
}


def describe(code: str | None, fallback: str = "") -> dict[str, str]:
    entry = CATALOG.get(str(code or ""), {})
    return {
        "code": str(code or ""),
        "title": entry.get("title") or fallback or "Request failed",
        "next": entry.get("next") or "See the error detail and retry if it is safe.",
    }


def enrich(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach title/next to an error payload that already has a code."""
    info = describe(payload.get("code"), str(payload.get("error") or ""))
    out = dict(payload)
    out.setdefault("title", info["title"])
    out.setdefault("next", info["next"])
    return out


def catalog() -> dict[str, Any]:
    return {"errors": {code: dict(row) for code, row in CATALOG.items()}}
