"""Reviewed simulator profile revisions, with optimistic review and historical evidence."""

from __future__ import annotations

from typing import Any

from certarig.edge.configurator import _diff
from certarig.edge.revalidation import revalidation

from .contracts import fingerprint
from .store import Actor, uid


def baseline(platform: Any, asset: dict[str, Any], reviewer: str) -> dict[str, Any]:
    revision = asset.setdefault("profile_revision", 1)
    identifier = asset["id"] + "_profile_" + str(revision)
    try:
        return platform.store.get("asset_profile", identifier, asset["org_id"])
    except KeyError:
        value = {
            "id": identifier,
            "org_id": asset["org_id"],
            "asset_id": asset["id"],
            "revision": revision,
            "profile_hash": asset["profile_hash"],
            "profile": asset["profile"],
            "capabilities_hash": asset.get("capabilities_hash"),
            "reviewer_id": reviewer,
            "reviewed_at": platform.store.clock(),
        }
        value["record_hash"] = fingerprint(value)
        return platform.store.put("asset_profile", value)


def history(platform: Any, actor: Actor, asset_id: str) -> list[dict[str, Any]]:
    platform.asset(actor, asset_id)
    return [p for p in platform.store.listing("asset_profile", actor.org_id) if p["asset_id"] == asset_id]


def preview(platform: Any, actor: Actor, asset_id: str) -> dict[str, Any]:
    platform.reviewer(actor)
    asset = platform.asset(actor, asset_id)
    client = platform.client(asset)
    rig, caps = client.rig(), client.capabilities()
    if rig["rig"]["hardware"]["mode"] != "simulator":
        raise ValueError("Only simulator profiles may be reviewed here")
    if not isinstance(rig.get("config_hash"), str) or not rig["config_hash"]:
        raise ValueError("Connector did not supply an exact profile hash")
    with platform.store.atomic():
        asset = platform.asset(actor, asset_id)
        baseline(
            platform, asset, actor.user_id
        )  # Upgrade the original local-proof records without losing them.
        changed = rig != asset["profile"] or fingerprint(caps) != asset.get("capabilities_hash")
        value = {
            "id": uid("prv"),
            "org_id": actor.org_id,
            "asset_id": asset_id,
            "reviewer_id": actor.user_id,
            "base_revision": asset.get("profile_revision", 1),
            "base_hash": asset["profile_hash"],
            "profile": rig,
            "profile_hash": rig["config_hash"],
            "capabilities_hash": fingerprint(caps),
            "diff": _diff(asset["profile"], rig),
            "revalidation": revalidation(asset["profile"]["rig"], rig["rig"]),
            "required_agent_checks": ["all_five_evaluation_cases", "independent_deployment_review"],
            "changed": changed,
            "created_at": platform.store.clock(),
            "expires_at": platform.store.clock() + 300,
            "status": "pending" if changed else "unchanged",
        }
        if changed and not value["revalidation"]["required_checks"]:
            value["revalidation"].update(
                full_qualification=True,
                required_checks=["mapping_review", "all_supported_procedures", "safe_state_and_recovery"],
                reason="Profile identity or connector policy changed; full qualification required",
                execution_authority="new_review_and_approval_required",
            )
        if fingerprint(caps) != asset.get("capabilities_hash"):
            value["diff"].append("~ connector_capabilities")
        if changed:
            invalidate(
                platform,
                actor.org_id,
                asset_id,
                "Observed asset profile changed; reviewed baseline and new evaluation required",
            )
        return platform.store.put("profile_review", value)


def invalidate(platform: Any, org: str, asset_id: str, reason: str) -> None:
    for d in platform.store.listing("deployment", org):
        if d["asset_id"] == asset_id and d["status"] in {"approved", "running"}:
            platform.pause(d, reason)


def accept(platform: Any, actor: Actor, asset_id: str, review_id: str) -> dict[str, Any]:
    platform.reviewer(actor)
    asset = platform.asset(actor, asset_id)
    review = platform.store.get("profile_review", review_id, actor.org_id)
    if review["asset_id"] != asset_id or review["reviewer_id"] != actor.user_id:
        raise PermissionError("Profile review belongs to another asset or reviewer")
    client = platform.client(asset)
    rig, caps = client.rig(), client.capabilities()
    with platform.store.atomic():
        asset = platform.asset(actor, asset_id)
        current = platform.store.get("profile_review", review_id, actor.org_id)
        if (
            current["status"] != "pending"
            or not 0 <= platform.store.clock() - current["created_at"] < 300
            or current["base_revision"] != asset.get("profile_revision", 1)
            or current["base_hash"] != asset["profile_hash"]
            or rig != current["profile"]
            or fingerprint(caps) != current["capabilities_hash"]
            or rig["rig"]["hardware"]["mode"] != "simulator"
        ):
            raise ValueError("Profile review is stale, changed, expired or already consumed; preview again")
        baseline(platform, asset, actor.user_id)
        asset.update(
            profile=rig,
            profile_hash=rig["config_hash"],
            profile_revision=asset.get("profile_revision", 1) + 1,
            capabilities_hash=fingerprint(caps),
        )
        record = baseline(platform, asset, actor.user_id)
        platform.store.put("asset", asset)
        current.update(
            status="accepted", accepted_at=platform.store.clock(), profile_revision=record["revision"]
        )
        platform.store.put("profile_review", current)
        invalidate(
            platform,
            actor.org_id,
            asset_id,
            "Profile review invalidated prior evaluation and execution grants",
        )
        platform.store.audit(
            actor.org_id,
            "asset_profile_reviewed",
            actor.user_id,
            asset_id=asset_id,
            profile_revision=record["revision"],
            profile_hash=record["profile_hash"],
            review_id=review_id,
            authority="new_evaluation_and_independent_review_required",
        )
        return {
            "asset": asset,
            "review": current,
            "profile": record,
            "execution_authority": False,
            "next_step": "Collect a new evaluation, qualify it in Sandbox and obtain independent deployment review",
        }


def evidence_asset(platform: Any, actor: Actor, deployment: dict[str, Any]) -> dict[str, Any]:
    asset = dict(platform.asset(actor, deployment["asset_id"]))
    revision = deployment["binding"].get("profile_revision")
    if revision is None:  # Older bundles retain their format and original profile binding.
        if asset["profile_hash"] != deployment["binding"]["profile_hash"]:
            matches = [
                p
                for p in history(platform, actor, asset["id"])
                if p["profile_hash"] == deployment["binding"]["profile_hash"]
            ]
            if not matches:
                raise ValueError("Missing historical reviewed profile")
            asset.update(profile=matches[-1]["profile"], profile_hash=matches[-1]["profile_hash"])
        return asset
    record = platform.store.get("asset_profile", asset["id"] + "_profile_" + str(revision), actor.org_id)
    if record["profile_hash"] != deployment["binding"]["profile_hash"]:
        raise ValueError("Historical profile binding mismatch")
    asset.update(
        profile=record["profile"],
        profile_hash=record["profile_hash"],
        profile_revision=revision,
        reviewed_profile=record,
        capabilities_hash=record.get("capabilities_hash"),
    )
    return asset
