"""Reviewed analysis definitions and tenant-scoped bridge to the isolated broker."""

from __future__ import annotations

import base64
import csv
import io
import json
import time
from typing import Any

import jsonschema

from .contracts import encoded, fingerprint
from .store import Actor, uid
from .workbench import text


class Analysis:
    def __init__(self, platform: Any, broker: Any):
        self.p, self.s, self.broker = platform, platform.store, broker

    def get(self, actor: Actor, kind: str, identifier: str) -> dict[str, Any]:
        value = self.s.get(kind, identifier, actor.org_id)
        self.p.asset(actor, value["asset_id"])
        return value

    def listing(self, actor: Actor, kind: str) -> list[dict[str, Any]]:
        allowed = {v["id"] for v in self.p.assets(actor)}
        return [v for v in self.s.listing(kind, actor.org_id) if v["asset_id"] in allowed]

    def create(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {
            "name",
            "asset_id",
            "kind",
            "source",
            "input_schema",
            "output_schema",
            "dependencies",
            "tests",
        }:
            raise ValueError("Tool requires source, input/output schemas, dependencies and tests")
        self.p.asset(actor, body["asset_id"])
        if body["kind"] not in {"python", "spice"} or len(text(body["source"], 128000).encode()) > 256000:
            raise ValueError("Choose bounded Python or SPICE source")
        if not isinstance(body["dependencies"], list) or not set(body["dependencies"]) <= {
            "numpy",
            "matplotlib",
            "ngspice",
            "certarig",
        }:
            raise ValueError("Only preinstalled runner dependencies are available; no package installation")
        for key in ("input_schema", "output_schema"):
            if (
                not isinstance(body[key], dict)
                or len(encoded(body[key])) > 16000
                or "$ref" in json.dumps(body[key])
            ):
                raise ValueError("Bounded inline JSON schemas required; external references are unavailable")
            jsonschema.Draft202012Validator.check_schema(body[key])
        if not isinstance(body["tests"], list) or not 1 <= len(body["tests"]) <= 3:
            raise ValueError("Declare one to three analysis tests")
        for case in body["tests"]:
            if set(case) != {"inputs", "expected"}:
                raise ValueError("Each test needs inputs and exact expected result")
            jsonschema.validate(case["inputs"], body["input_schema"])
            jsonschema.validate(case["expected"], body["output_schema"])
        preflight = self.broker.call("preflight", actor.org_id + "/" + actor.user_id, "agent", {})
        value = {
            "id": uid("tool"),
            "org_id": actor.org_id,
            "owner_id": actor.user_id,
            "revision": 1,
            **body,
            "name": text(body["name"], 120),
            "runner_image": preflight.get("image", preflight.get("runner_image")),
            "status": "unreviewed",
            "created_at": self.s.clock(),
        }
        # A runtime may be unqualified at authoring time; review requires a real pinned image.
        value["hash"] = fingerprint(value)
        return self.s.put("analysis_tool", value)

    def check_definition(self, value: dict[str, Any]) -> None:
        stable = {
            k: v
            for k, v in value.items()
            if k not in {"hash", "reviewer_id", "review_test_id", "reviewed_image"}
        }
        stable["status"] = "unreviewed"
        if fingerprint(stable) != value["hash"]:
            raise ValueError("Analysis definition changed; create a new version")

    def _owner(self, value: dict[str, Any]) -> str:
        return value["org_id"] + "/analysis/" + value["owner_id"] + "/" + value["id"]

    def run(
        self,
        actor: Actor,
        identifier: str,
        inputs: Any,
        *,
        testing: bool = False,
        replay_id: str | None = None,
    ) -> dict[str, Any]:
        tool = self.get(actor, "analysis_tool", identifier)
        self.check_definition(tool)
        if tool["owner_id"] != actor.user_id:
            raise PermissionError("Only the tool author may start analysis")
        if not testing and tool["status"] != "reviewed":
            raise PermissionError("Independent tool review required")
        preflight = self.broker.call("preflight", actor.org_id + "/" + actor.user_id, "agent", {})
        expected_image = tool.get("reviewed_image", tool["runner_image"])
        if not preflight["ready"]:
            raise ValueError("Sandbox preflight failed; no host fallback")
        if (
            expected_image is not None
            and preflight.get("runner_image", preflight.get("image")) != expected_image
        ):
            raise ValueError("Runner image changed; create and test a new tool version")
        jsonschema.validate(inputs, tool["input_schema"])
        if len(encoded(inputs)) > 64000:
            raise ValueError("Analysis parameters exceed limit")
        asset = self.p.asset(actor, tool["asset_id"])
        rig = self.p.read_asset(actor, asset["id"], "rig")
        signals = self.p.read_asset(actor, asset["id"], "signals")
        document = rig["rig"]
        procedure = {"name": "analysis_only", "version": "1", "steps": []}
        value = {
            "id": uid("ana"),
            "org_id": actor.org_id,
            "asset_id": asset["id"],
            "owner_id": actor.user_id,
            "tool_id": identifier,
            "tool_hash": tool["hash"],
            "inputs": inputs,
            "signals": signals,
            "profile_hash": asset["profile_hash"],
            "profile_revision": asset.get("profile_revision", 1),
            "testing": testing,
            "status": "preparing",
            "created_at": self.s.clock(),
            "replay_id": replay_id,
        }
        recording = ""
        if replay_id:
            replay = self.get(actor, "replay", replay_id)
            if replay["asset_id"] != asset["id"]:
                raise PermissionError("Replay belongs to another bench")
            recording = base64.b64encode(replay["csv"].encode()).decode()
        owner = self._owner(value)
        workspace = self.broker.call(
            "create",
            owner,
            "agent",
            {
                "document": document,
                "procedure": procedure,
                "base_config_hash": asset["profile_hash"],
                "recording": recording,
                "provenance": {
                    "analysis_id": value["id"],
                    "tool_hash": tool["hash"],
                    "inputs_hash": fingerprint(inputs),
                    "replay_id": replay_id,
                },
            },
        )
        value["sandbox_id"] = workspace["sandbox_id"]
        self.s.put("analysis", value)
        try:
            parameters = {"inputs": inputs, "signals": signals, "replay_id": replay_id}
            job = self.broker.call(
                "run",
                owner,
                "agent",
                {
                    "sandbox_id": value["sandbox_id"],
                    "kind": tool["kind"],
                    "source": tool["source"],
                    "parameters": parameters,
                },
            )
            if expected_image is not None and expected_image != job["runner_image"]:
                raise ValueError("Runner image changed; create and test a new tool version")
            value.update(
                job_id=job["job_id"],
                status=job["status"],
                runner_image=job["runner_image"],
                input_hashes=job["input_hashes"],
            )
        except Exception:
            self.broker.call("close", owner, "agent", {"sandbox_id": value["sandbox_id"]})
            value.update(status="failed")
            self.s.put("analysis", value)
            raise
        return self.s.put("analysis", value)

    def inspect(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.get(actor, "analysis", identifier)
        if not value.get("job_id"):
            return value
        w = self.broker.call("read", self._owner(value), "agent", {"sandbox_id": value["sandbox_id"]})
        job = next(j for j in w["jobs"] if j["job_id"] == value["job_id"])
        value.update(status=job["status"], artifacts=job["artifacts"], resource=job.get("resource", {}))
        if job["status"] == "completed":
            try:
                result = self.artifact(actor, identifier, "result.json")
                output = json.loads(base64.b64decode(result["data"], validate=True))
                tool = self.get(actor, "analysis_tool", value["tool_id"])
                jsonschema.validate(output, tool["output_schema"])
                value["output"] = output
            except (KeyError, ValueError, jsonschema.ValidationError) as exc:
                value.update(status="failed", error="Missing or invalid result.json: " + str(exc)[:200])
            self.broker.call("close", self._owner(value), "agent", {"sandbox_id": value["sandbox_id"]})
        if job["status"] in {"completed", "failed", "cancelled", "interrupted", "timed_out"}:
            self.broker.call("close", self._owner(value), "agent", {"sandbox_id": value["sandbox_id"]})
            value["bundle"] = self.broker.call(
                "export", self._owner(value), "agent", {"sandbox_id": value["sandbox_id"]}
            )["data"]
        return self.s.put("analysis", value)

    def artifact(self, actor: Actor, identifier: str, name: str) -> dict[str, Any]:
        value = self.get(actor, "analysis", identifier)
        if (
            not isinstance(name, str)
            or "/" in name
            or not name.endswith((".json", ".txt", ".csv", ".png", ".log"))
        ):
            raise ValueError("Only inert text, data and PNG artifacts may be retrieved")
        return dict(
            self.broker.call(
                "artifact",
                self._owner(value),
                "agent",
                {"sandbox_id": value["sandbox_id"], "job_id": value["job_id"], "name": name},
            )
        )

    def cancel(self, actor: Actor, identifier: str) -> dict[str, Any]:
        value = self.get(actor, "analysis", identifier)
        if value["owner_id"] != actor.user_id:
            self.p.reviewer(actor)
        self.broker.call("close", self._owner(value), "agent", {"sandbox_id": value["sandbox_id"]})
        value.update(status="cancelled")
        return self.s.put("analysis", value)

    def test(self, actor: Actor, identifier: str) -> dict[str, Any]:
        tool = self.get(actor, "analysis_tool", identifier)
        jobs = [self.run(actor, identifier, case["inputs"], testing=True)["id"] for case in tool["tests"]]
        return self.s.put(
            "tool_test",
            {
                "id": uid("tst"),
                "org_id": actor.org_id,
                "asset_id": tool["asset_id"],
                "tool_id": identifier,
                "tool_hash": tool["hash"],
                "analyses": jobs,
                "created_at": self.s.clock(),
            },
        )

    def review(self, actor: Actor, identifier: str, test_id: str) -> dict[str, Any]:
        self.p.reviewer(actor)
        tool = self.get(actor, "analysis_tool", identifier)
        self.check_definition(tool)
        test = self.get(actor, "tool_test", test_id)
        if tool["owner_id"] == actor.user_id:
            raise PermissionError("Independent tool review required")
        if (
            test["tool_id"] != identifier
            or test["tool_hash"] != tool["hash"]
            or len(test["analyses"]) != len(tool["tests"])
        ):
            raise ValueError("Matching complete tool tests required")
        analyses = [self.inspect(actor, i) for i in test["analyses"]]
        images = {v.get("runner_image") for v in analyses}
        if len(images) != 1 or not next(iter(images), None):
            raise ValueError("Pinned tested runner image required")
        for result, case in zip(analyses, tool["tests"], strict=True):
            if (
                result["status"] != "completed"
                or result.get("output") != case["expected"]
                or result["tool_hash"] != tool["hash"]
            ):
                raise ValueError("All declared analysis tests must complete with expected results")
        preflight = self.broker.call("preflight", self._owner(analyses[0]), "agent", {})
        image = preflight.get("image", preflight.get("runner_image"))
        if not preflight["ready"] or image != analyses[0]["runner_image"]:
            raise ValueError("Qualified current runner image required")
        tool.update(
            status="reviewed", reviewer_id=actor.user_id, review_test_id=test_id, reviewed_image=image
        )
        # Definition hash excludes mutable review metadata; execution remains exactly source-bound.
        return self.s.put("analysis_tool", tool)

    def import_run(self, actor: Actor, body: dict[str, Any]) -> dict[str, Any]:
        if set(body) != {"asset_id", "name", "csv", "source"}:
            raise ValueError("Replay requires bench, name, bounded CSV and source description")
        self.p.asset(actor, body["asset_id"])
        raw = text(body["csv"], 512000)
        rows = list(csv.DictReader(io.StringIO(raw)))
        if not 1 <= len(rows) <= 10000 or not {
            "channel_id",
            "value",
            "unit",
            "captured_at",
            "quality",
        } <= set(rows[0]):
            raise ValueError("CSV needs 1-10000 timestamped, quality-labelled samples")
        from certarig.connectors.observation import checked_sample

        for row in rows:
            checked_sample(
                {**row, "value": float(row["value"])}, expected_unit=row["unit"], max_age_s=float("inf")
            )
        value = {
            "id": uid("rpl"),
            "org_id": actor.org_id,
            "asset_id": body["asset_id"],
            "owner_id": actor.user_id,
            "name": text(body["name"], 120),
            "csv": raw,
            "source": text(body["source"], 1000),
            "sha256": fingerprint(raw),
            "kind": "imported_recording_unverified_origin",
            "created_at": self.s.clock(),
            "samples": len(rows),
        }
        return self.s.put("replay", value)

    def wait(self, actor: Actor, identifier: str, guard: Any) -> dict[str, Any]:
        # Capture the already-authorized job identity before rechecking the live lease.
        # Cleanup must still close this exact owned job after grant/membership loss.
        owned = self.s.get("analysis", identifier, actor.org_id)
        if owned["owner_id"] != actor.user_id:
            raise PermissionError("Only the analysis owner may wait for this job")
        deadline = time.monotonic() + 125
        try:
            while time.monotonic() < deadline:
                guard()
                value = self.inspect(actor, identifier)
                if value["status"] in {"completed", "failed", "cancelled", "interrupted", "timed_out"}:
                    return value
                time.sleep(0.1)
            raise ValueError("Bounded analysis deadline reached")
        except Exception:
            try:
                self.broker.call("close", self._owner(owned), "agent", {"sandbox_id": owned["sandbox_id"]})
                status = "cancelled"
            except (OSError, ValueError, KeyError, PermissionError):
                status = "interrupted"
            with self.s.atomic():
                current = self.s.get("analysis", identifier, actor.org_id)
                current.update(
                    status=status, reason="Live authority unavailable; owned worker cleanup requested"
                )
                self.s.put("analysis", current)
            raise


class AnalysisRegistry:
    """Deployment-selected analysis tools receive snapshots, never connector credentials."""

    def __init__(
        self,
        base: Any,
        service: Analysis,
        actor: Actor,
        version: dict[str, Any],
        guard: Any,
        deployment_id: str,
    ):
        self.base, self.service, self.actor, self.version, self.guard, self.deployment_id = (
            base,
            service,
            actor,
            version,
            guard,
            deployment_id,
        )

    def specs(self) -> list[Any]:
        from certarig.agent.providers.base import ToolSpec

        tools = [
            self.service.get(self.actor, "analysis_tool", identifier)
            for identifier in self.version.get("analysis_tools", [])
        ]
        return [
            *self.base.specs(),
            *[
                ToolSpec(
                    "analysis_" + tool["id"], "Sandbox analysis only: " + tool["name"], tool["input_schema"]
                )
                for tool in tools
            ],
        ]

    def execute(self, name: str, args: dict[str, Any]) -> Any:
        from certarig.agent.tools import ToolResult

        if not name.startswith("analysis_"):
            return self.base.execute(name, args)
        try:
            self.guard()
            identifier = name.removeprefix("analysis_")
            if identifier not in self.version.get("analysis_tools", []):
                raise PermissionError("Analysis tool outside reviewed deployment")
            result = self.service.run(self.actor, identifier, args)
            with self.service.s.atomic():
                self.guard()
                result["deployment_id"] = self.deployment_id
                self.service.s.put("analysis", result)
                deployment = self.service.s.get("deployment", self.deployment_id, self.actor.org_id)
                deployment.setdefault("analysis_ids", []).append(result["id"])
                self.service.s.put("deployment", deployment)
            result = self.service.wait(self.actor, result["id"], self.guard)
            self.guard()
            return ToolResult(
                name,
                args,
                result["status"] == "completed",
                {
                    "analysis_id": result["id"],
                    "status": result["status"],
                    "output": result.get("output"),
                    "qualification": False,
                },
                0,
            )
        except (ValueError, KeyError, PermissionError, jsonschema.ValidationError) as exc:
            return ToolResult(name, args, False, {"error": str(exc)[:500]}, 0)
