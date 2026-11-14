"""Workbench evidence extension. Offline checks retain the legacy lifecycle verifier."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from typing import Any

from .contracts import encoded, fingerprint, verify_trace

EXTRA = {"workspace.json", "members.json", "analysis.json", "connectors.json", "replays.json"}


def context(platform: Any, actor: Any, deployment: dict[str, Any]) -> dict[str, Any]:
    s, d = platform.store, deployment
    version = platform.version(actor, d["version_id"])
    drafts = [v for v in s.listing("draft", actor.org_id) if v.get("version_id") == version["id"]]
    projects = [
        v for v in s.listing("project", actor.org_id) if v["id"] in {draft["project_id"] for draft in drafts}
    ]
    members = [
        {
            "version": platform.version(actor, identifier),
            "evaluation": s.get("evaluation", evaluation_id, actor.org_id),
        }
        for identifier, evaluation_id in zip(
            version.get("team_members", []), version.get("member_evaluations", []), strict=True
        )
    ]
    analysis = [v for v in s.listing("analysis", actor.org_id) if v.get("deployment_id") == d["id"]]
    selected_tools = {
        identifier
        for v in [version, *[m["version"] for m in members]]
        for identifier in v.get("analysis_tools", [])
    }
    tools = [s.get("analysis_tool", identifier, actor.org_id) for identifier in selected_tools]
    replays = [
        s.get("replay", identifier, actor.org_id)
        for identifier in {a["replay_id"] for a in analysis if a.get("replay_id")}
    ]
    connectors = [
        v
        for v in s.listing("connector_profile", actor.org_id)
        if v["asset_id"] == d["asset_id"] and v["base_profile_hash"] == d["binding"]["profile_hash"]
    ]
    return {
        "workspace.json": {"drafts": drafts, "projects": projects},
        "members.json": members,
        "analysis.json": {"runs": analysis, "tools": tools},
        "connectors.json": connectors,
        "replays.json": replays,
    }


def package(files: dict[str, bytes], extra: dict[str, Any]) -> bytes:
    files = {**files, **{name: encoded(value) for name, value in extra.items()}}
    files["manifest.json"] = encoded(
        {
            "format": "certarig-agent-evidence/2",
            "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()},
            "claim": "Recorded observation, team delegation and analysis; no physical commissioning or deterministic LLM replay",
        }
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def verify(data: bytes) -> dict[str, Any]:
    from . import evidence

    required = evidence.REQUIRED | EXTRA
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if (
            len(entries) != len(required) + 1
            or {i.filename for i in entries} != required | {"manifest.json"}
            or sum(i.file_size for i in entries) > 32 * 1024**2
            or any((i.external_attr >> 16) & 0o170000 == 0o120000 for i in entries)
        ):
            raise ValueError("Incomplete, unsafe or oversized workbench evidence")
        files = {i.filename: archive.read(i) for i in entries}
    manifest = json.loads(files.pop("manifest.json"))
    if (
        manifest["format"] != "certarig-agent-evidence/2"
        or set(manifest["files"]) != required
        or any(hashlib.sha256(value).hexdigest() != manifest["files"][name] for name, value in files.items())
    ):
        raise ValueError("Missing or corrupt workbench evidence")
    values = {n: json.loads(b) for n, b in files.items()}
    deployment, version = values["deployment.json"], values["version.json"]
    members = values["members.json"]
    if len(members) != len(version.get("team_members", [])):
        raise ValueError("Missing team member definitions")
    for i, record in enumerate(members):
        member, evaluation = record["version"], record["evaluation"]
        if (
            member["id"] != version["team_members"][i]
            or member["hash"] != fingerprint({k: v for k, v in member.items() if k != "hash"})
            or evaluation["version_id"] != member["id"]
            or evaluation["id"] != version["member_evaluations"][i]
            or evaluation["binding"] != deployment["binding"]["team_members"][i]
            or evaluation["binding"]["version_hash"] != member["hash"]
            or not evaluation["trusted"]
            or evaluation["status"] != "passed"
            or not verify_trace(evaluation["trace"])["passed"]
            or evaluation["trace"]["binding"] != evaluation["binding"]
        ):
            raise ValueError("Invalid team member qualification binding")
    for draft in values["workspace.json"]["drafts"]:
        if (
            draft["org_id"] != deployment["org_id"]
            or draft["asset_id"] != deployment["asset_id"]
            or draft["version_id"] != version["id"]
            or any(version[k] != val for k, val in draft["definition"].items())
        ):
            raise ValueError("Draft provenance differs from deployed version")
    tools = {t["id"]: t for t in values["analysis.json"]["tools"]}
    for run in values["analysis.json"]["runs"]:
        if (
            run["org_id"] != deployment["org_id"]
            or run["asset_id"] != deployment["asset_id"]
            or run["deployment_id"] != deployment["id"]
            or run["tool_hash"] != tools[run["tool_id"]]["hash"]
            or run["profile_hash"] != deployment["binding"]["profile_hash"]
            or run["status"] not in {"completed", "failed", "cancelled", "interrupted", "timed_out"}
        ):
            raise ValueError("Incomplete analysis provenance")
        if "bundle" not in run:
            raise ValueError("Missing raw analysis evidence")
        from certarig.sandbox.evidence import verify as verify_sandbox

        check = verify_sandbox(io.BytesIO(base64.b64decode(run["bundle"], validate=True)))
        if not check["ok"]:
            raise ValueError("Invalid nested Sandbox evidence")
    for replay in values["replays.json"]:
        if (
            replay["sha256"] != fingerprint(replay["csv"])
            or replay["org_id"] != deployment["org_id"]
            or replay["asset_id"] != deployment["asset_id"]
        ):
            raise ValueError("Replay provenance mismatch")
    verify_analysis(values, deployment, version)
    # Reuse every v1 invariant, including the fixed evaluation verifier.
    legacy = {n: files[n] for n in evidence.REQUIRED}
    legacy["manifest.json"] = encoded(
        {
            "format": "certarig-agent-evidence/1",
            "files": {n: hashlib.sha256(b).hexdigest() for n, b in legacy.items()},
        }
    )
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in legacy.items():
            archive.writestr(name, content)
    return {
        **evidence.verify(stream.getvalue()),
        "format": manifest["format"],
        "members": len(members),
        "analysis_runs": len(values["analysis.json"]["runs"]),
    }


def verify_analysis(values: dict[str, Any], deployment: dict[str, Any], version: dict[str, Any]) -> None:
    """Require every selected definition and submitted job, then cross-bind raw inputs."""
    import jsonschema

    versions = [version, *[m["version"] for m in values["members.json"]]]
    records = values["analysis.json"]
    runs, definitions = records["runs"], records["tools"]
    if len({r["id"] for r in runs}) != len(runs) or len({t["id"] for t in definitions}) != len(definitions):
        raise ValueError("Duplicate analysis evidence")
    run_ids = {r["id"] for r in runs}
    required_ids = set(deployment.get("analysis_ids", []))
    for observation in deployment["observations"]:
        transcripts = [
            observation["transcript"],
            *[d["transcript"] for d in observation.get("team", {}).get("delegations", [])],
        ]
        for transcript in transcripts:
            for row in transcript:
                if (
                    row["kind"] == "tool_result"
                    and row["name"].startswith("analysis_")
                    and isinstance(row.get("result"), dict)
                    and row["result"].get("analysis_id")
                ):
                    required_ids.add(row["result"]["analysis_id"])
    if run_ids != required_ids:
        raise ValueError("Missing or unexpected submitted analysis runs")
    required_tools = {identifier for v in versions for identifier in v.get("analysis_tools", [])}
    if {t["id"] for t in definitions} != required_tools:
        raise ValueError("Missing selected analysis definitions")
    tools = {t["id"]: t for t in definitions}
    bound_tools = {
        t["id"]: t
        for b in [deployment["binding"], *deployment["binding"].get("team_members", [])]
        for t in b.get("analysis_tools", [])
    }
    for identifier, tool in tools.items():
        stable = {
            k: v
            for k, v in tool.items()
            if k not in {"hash", "reviewer_id", "review_test_id", "reviewed_image"}
        }
        stable["status"] = "unreviewed"
        if (
            tool["hash"] != fingerprint(stable)
            or tool["org_id"] != deployment["org_id"]
            or tool["asset_id"] != deployment["asset_id"]
            or tool["status"] != "reviewed"
            or tool["owner_id"] == tool["reviewer_id"]
            or bound_tools.get(identifier)
            != {
                "id": identifier,
                "hash": tool["hash"],
                "runner_image": tool["reviewed_image"],
                "reviewer_id": tool["reviewer_id"],
            }
        ):
            raise ValueError("Analysis definition or review binding mismatch")
    for run in runs:
        tool = tools[run["tool_id"]]
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(run["bundle"], validate=True))) as archive:
            workspace = json.loads(archive.read("workspace.json"))
            jobs = workspace["jobs"]
            if len(jobs) != 1 or jobs[0]["job_id"] != run["job_id"]:
                raise ValueError("Unexpected nested analysis jobs")
            job = jobs[0]
            prefix = job["job_id"] + "/"
            source = archive.read(
                prefix + "inputs/" + ("main.py" if tool["kind"] == "python" else "circuit.cir")
            ).decode()
            parameters = json.loads(archive.read(prefix + "inputs/parameters.json"))
            snapshot = json.loads(archive.read(prefix + "inputs/snapshot.json"))
            provenance = snapshot["provenance"]
            if (
                source != tool["source"]
                or job["source"] != source
                or run["runner_image"] != job["runner_image"]
                or run["runner_image"] != tool["reviewed_image"]
                or run["input_hashes"] != job["input_hashes"]
                or run.get("artifacts") != job["artifacts"]
                or run["inputs"] != parameters["inputs"]
                or run["signals"] != parameters["signals"]
                or run.get("replay_id") != parameters.get("replay_id")
                or provenance.get("analysis_id") != run["id"]
                or provenance.get("tool_hash") != tool["hash"]
                or provenance.get("inputs_hash") != fingerprint(run["inputs"])
                or snapshot["base_config_hash"] != deployment["binding"]["profile_hash"]
            ):
                raise ValueError("Nested analysis source, inputs or image differs from deployment")
            if run["status"] == "completed":
                output = json.loads(archive.read(prefix + "artifacts/result.json"))
                jsonschema.validate(output, tool["output_schema"])
                if output != run["output"]:
                    raise ValueError("Displayed analysis differs from raw output")
