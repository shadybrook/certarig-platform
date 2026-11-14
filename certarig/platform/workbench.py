"""Resumable, asset-scoped commissioning workspaces. Drafts confer no authority."""

from __future__ import annotations

import json
from typing import Any

from .contracts import READ_TOOLS, fingerprint
from .store import Actor, uid

TEMPLATES = {
    "commissioning": "Assess signal identity, calibration, units, freshness and readiness. Explain blockers. Observe only.",
    "analysis": "Inspect recorded signals and explain trends and uncertainty. Do not invent measurements.",
    "revalidation": "Compare reviewed profiles and identify evidence that needs repeating. Propose changes for review.",
    "evidence": "Inspect evidence completeness, provenance and consistency. Distinguish simulation from physical evidence.",
    "reporting": "Summarize recorded engineering results and unresolved questions with evidence references.",
}


def text(value: Any, maximum: int = 8000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Expected non-empty bounded text")
    return value.strip()


class Workbench:
    def __init__(self, platform: Any):
        self.p, self.s = platform, platform.store

    def get(self, actor: Actor, kind: str, identifier: str, *, edit: bool = False) -> dict[str, Any]:
        self.p.actor(actor)
        value = self.s.get(kind, identifier, actor.org_id)
        if value.get("asset_id"):
            self.p.asset(actor, value["asset_id"])
        if edit and value["owner_id"] != actor.user_id:
            raise PermissionError("Only the owner may edit this draft or conversation")
        return value

    def listing(self, actor: Actor, kind: str) -> list[dict[str, Any]]:
        self.p.actor(actor)
        result = []
        for row in self.s.listing(kind, actor.org_id):
            try:
                self.get(actor, kind, row["id"])
                if kind == "project":
                    row = {
                        **row,
                        "asset_ids": [
                            a for a in row["asset_ids"] if a in {v["id"] for v in self.p.assets(actor)}
                        ],
                    }
                result.append(row)
            except (KeyError, PermissionError):
                continue
        return result

    def project(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        self.p.actor(actor)
        if (
            set(body) != {"name", "asset_ids"}
            or not isinstance(body["asset_ids"], list)
            or not 1 <= len(body["asset_ids"]) <= 16
        ):
            raise ValueError("Project requires a name and one to sixteen permitted benches")
        for identifier in body["asset_ids"]:
            self.p.asset(actor, identifier)
        return self.s.put(
            "project",
            {
                "id": uid("prj"),
                "org_id": actor.org_id,
                "owner_id": actor.user_id,
                "name": text(body["name"], 120),
                "asset_ids": list(dict.fromkeys(body["asset_ids"])),
                "created_at": self.s.clock(),
            },
        )

    def draft(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) - {"asset_id", "project_id", "template", "goal", "base_version_id"}:
            raise ValueError("Unsupported draft fields")
        asset = self.p.asset(actor, body["asset_id"])
        project_id = body.get("project_id")
        if project_id and asset["id"] not in self.get(actor, "project", project_id)["asset_ids"]:
            raise ValueError("Bench is outside this project")
        template = body.get("template", "commissioning")
        if template not in TEMPLATES:
            raise ValueError("Unknown agent template")
        goal = text(body.get("goal", TEMPLATES[template]))
        supported = {t["name"] for t in self.p.observation_tools(actor, asset["id"])}
        value = {
            "id": uid("dft"),
            "org_id": actor.org_id,
            "asset_id": asset["id"],
            "owner_id": actor.user_id,
            "project_id": project_id,
            "revision": 1,
            "template": template,
            "created_at": self.s.clock(),
            "base_profile_hash": asset["profile_hash"],
            "status": "draft",
            "messages": [],
            "history": [],
            "definition": {
                "name": template.capitalize() + " agent",
                "instructions": TEMPLATES[template] + "\nGoal: " + goal,
                "asset_id": asset["id"],
                "connection_id": "",
                "tools": sorted(supported & READ_TOOLS),
            },
        }
        value["messages"] = [
            {"role": "user", "text": goal},
            {
                "role": "assistant",
                "text": "Deterministic drafting assistant: inspect the proposed instructions and tools, then select your model connection. This draft has no execution authority.",
            },
        ]
        if body.get("base_version_id"):
            base = self.p.version(actor, body["base_version_id"])
            if (
                base["author_id"] != actor.user_id
                or base["asset_id"] != asset["id"]
                or base.get("team_members")
            ):
                raise PermissionError("Revise your own individual version on its original bench")
            value["base_version_id"] = base["id"]
            value["definition"] = {
                k: base[k]
                for k in (
                    "name",
                    "instructions",
                    "asset_id",
                    "connection_id",
                    "tools",
                    "analysis_tools",
                    "limits",
                    "output_contract",
                )
                if k in base
            }
            value["base_definition"] = json.loads(json.dumps(value["definition"]))
        return self.s.put("draft", value)

    def update(self, actor: Actor, identifier: str, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) - {"expected_revision", "definition", "message"}:
            raise ValueError("Unsupported draft update")
        with self.s.atomic():
            value = self.get(actor, "draft", identifier, edit=True)
            if value["revision"] != body["expected_revision"] or value["status"] != "draft":
                raise ValueError("Draft changed or was committed; reload before editing")
            if value["revision"] >= 100 or len(value["messages"]) >= 200:
                raise ValueError("Draft history limit reached; create a new draft")
            old = value["definition"]
            definition = body.get("definition", old)
            if (
                not {"name", "instructions", "asset_id", "connection_id", "tools"} <= set(definition)
                or set(definition)
                - {
                    "name",
                    "instructions",
                    "asset_id",
                    "connection_id",
                    "tools",
                    "analysis_tools",
                    "limits",
                    "output_contract",
                }
                or definition["asset_id"] != value["asset_id"]
            ):
                raise ValueError("Draft requires a complete definition on its original bench")
            text(definition["name"], 120)
            text(definition["instructions"])
            if (
                not isinstance(definition["connection_id"], str)
                or not isinstance(definition["tools"], list)
                or not all(isinstance(t, str) and t in READ_TOOLS for t in definition["tools"])
            ):
                raise ValueError("Invalid draft connection or tools")
            value["history"].append(
                {"revision": value["revision"], "definition": old, "hash": fingerprint(old)}
            )
            # Copy to avoid aliased mutable caller data.
            value["definition"] = json.loads(json.dumps(definition))
            if "message" in body:
                message = text(body["message"], 2000)
                value["messages"].extend(
                    [
                        {"role": "user", "text": message},
                        {
                            "role": "assistant",
                            "text": "Deterministic drafting assistant: added your requirement to the proposal. Review it before saving a version.",
                        },
                    ]
                )
                value["definition"]["instructions"] = text(
                    definition["instructions"] + "\nRequirement: " + message
                )
            value.update(revision=value["revision"] + 1, updated_at=self.s.clock())
            return self.s.put("draft", value)

    def inspect(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.get(actor, "draft", identifier)
        d = value["definition"]
        blockers = []
        asset = self.p.asset(actor, value["asset_id"])
        if asset["profile_hash"] != value["base_profile_hash"]:
            blockers.append("Bench profile changed; create a draft against the reviewed baseline")
        try:
            c = self.p.owned_connection(actor, d["connection_id"])
            if not c["enabled"]:
                blockers.append("Model connection is disconnected")
        except (KeyError, PermissionError):
            blockers.append("Select an enabled model connection owned by the author")
        if not d["tools"]:
            blockers.append("Select at least one observation tool")
        before = value.get("base_definition", value["history"][-1]["definition"] if value["history"] else {})
        return {
            **value,
            "blockers": blockers,
            "diff": [
                {"field": key, "before": before.get(key), "after": val}
                for key, val in d.items()
                if before.get(key) != val
            ],
        }

    def commit(self, actor: Actor, identifier: str, revision: int) -> dict[str, Any]:
        with self.s.atomic():
            draft = self.get(actor, "draft", identifier, edit=True)
            if draft["status"] != "draft" or draft["revision"] != revision:
                raise ValueError("Draft changed or was already committed")
            if self.inspect(actor, identifier)["blockers"]:
                raise ValueError("Resolve draft blockers before saving a version")
            base = self.p.version(actor, draft["base_version_id"]) if draft.get("base_version_id") else None
            version = self.p.create_version(actor, draft["definition"], base["agent_id"] if base else None)
            draft.update(status="committed", version_id=version["id"])
            self.s.put("draft", draft)
            self.s.audit(
                actor.org_id,
                "draft_committed",
                actor.user_id,
                asset_id=draft["asset_id"],
                version_id=version["id"],
                draft_id=identifier,
            )
            return version
