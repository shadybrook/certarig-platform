"""Resumable commissioning drafts. Proposals are inert; only an operator applies them."""

from __future__ import annotations

import copy
import json
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .atomic import write_json_atomic
from .config import canonical_hash, load_config_dict
from .configurator import propose_rig
from .models import CONCEPT_BY_UNIT
from .server import EdgeNode, HttpError, RequestContext


class InterviewService:
    def __init__(self, node: EdgeNode) -> None:
        self.node = node
        self.root = node.runtime.evidence_dir / "interviews"
        self.lock = threading.RLock()

    def read(self, identifier: str) -> dict[str, Any]:
        if not re.fullmatch(r"iv_[a-f0-9]{16}", identifier):
            raise HttpError(404, "Interview not found")
        path = self.root / f"{identifier}.json"
        if not path.is_file():
            raise HttpError(404, "Interview not found")
        return dict(json.loads(path.read_text()))

    def listing(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, {"interviews": [json.loads(p.read_text()) for p in sorted(self.root.glob("iv_*.json"))]}

    def templates(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        root = Path(__file__).resolve().parents[2] / "config"
        result = {}
        for name, filename in {
            "thermal": "rig.thermal.capstone.json",
            "pressure_flow": "rig.sim.json",
        }.items():
            document = json.loads((root / filename).read_text())
            document["commissioning_required"] = True
            for channel in document["channels"]:
                channel.setdefault("concept", CONCEPT_BY_UNIT.get(channel["unit"].lower(), "signal"))
                channel.setdefault(
                    "source", {"kind": "virtual", "address": "fixture." + channel["channel_id"]}
                )
            result[name] = document
        return 200, {
            "evidence_kind": "simulated_fixture_templates_not_discovered_equipment",
            "templates": result,
        }

    def create(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        value = {
            "interview_id": "iv_" + uuid.uuid4().hex[:16],
            "revision": 0,
            "status": "draft",
            "answers": {},
            "sources": {},
            "unresolved": [],
            "created_by": ctx.principal_name,
            "created_at": datetime.now(UTC).isoformat(),
            "interpreter": "deterministic_bounded_fixture",
        }
        write_json_atomic(self.root / f"{value['interview_id']}.json", value)
        return 201, value

    def get(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, self.read(ctx.params["interview_id"])

    def update(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        with self.lock:
            value = self.read(ctx.params["interview_id"])
            if ctx.body.get("expected_revision") != value["revision"]:
                raise HttpError(409, "Re-read the interview before editing")
            answers, sources = ctx.body.get("answers", {}), ctx.body.get("sources", {})
            if (
                not isinstance(answers, dict)
                or not isinstance(sources, dict)
                or not all(isinstance(v, str) and v.strip() for v in sources.values())
            ):
                raise HttpError(400, "answers and nonempty source references must be objects")
            text = str(ctx.body.get("text", value.get("source_text", "")))
            unresolved = []
            for line in text.splitlines():
                key, sep, content = line.partition(":")
                key = key.strip().lower().replace(" ", "_")
                if sep and key in {"equipment", "safe_state", "procedures"} and content.strip():
                    answers[key] = (
                        [s.strip() for s in content.split(",")] if key == "procedures" else content.strip()
                    )
                    sources[key] = "operator interview text"
                elif line.strip():
                    unresolved.append(line.strip())
            write_json_atomic(self.root / "revisions" / f"{value['interview_id']}-{value['revision']}.json", value)
            value["answers"].update(copy.deepcopy(answers))
            for key in answers:
                value["sources"].pop(key, None)
            value["sources"].update(sources)
            value.update(revision=value["revision"] + 1, status="draft", unresolved=unresolved, source_text=text)
            value.pop("proposal", None)
            write_json_atomic(self.root / f"{value['interview_id']}.json", value)
            return 200, value

    def propose(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        with self.lock:
            value = self.read(ctx.params["interview_id"])
            answers = value["answers"]
            blockers = [
                f"Missing answer/source: {k}"
                for k in ("equipment", "safe_state", "procedures", "document", "calibration_records")
                if not answers.get(k) or not value["sources"].get(k)
            ]
            blockers += [f"Unresolved text: {line}" for line in value["unresolved"]]
            document = answers.get("document")
            preview = None
            if isinstance(document, dict):
                try:
                    config = load_config_dict(document)
                    if not config.commissioning_required:
                        blockers.append("Interview profiles must require commissioning")
                    records = answers.get("calibration_records", [])
                    if not isinstance(records, list):
                        raise ValueError("calibration_records must be a list")
                    refs = {
                        r.get("calibration_id") for r in records if isinstance(r, dict) and r.get("reference")
                    }
                    for channel in config.channels:
                        if channel.required and channel.calibration_id not in refs:
                            blockers.append(f"Missing calibration evidence: {channel.channel_id}")
                        if not channel.source or not (
                            channel.source.get("kind")
                            or channel.source.get("topic")
                            or channel.source.get("address")
                        ):
                            blockers.append(f"Missing source identity: {channel.channel_id}")
                        expected = {"pressure": "bar", "flow": "l/min", "temperature": "degc"}.get(
                            channel.concept
                        )
                        if (expected and channel.unit.lower() != expected) or CONCEPT_BY_UNIT.get(
                            channel.unit.lower(), channel.concept
                        ) != channel.concept:
                            blockers.append(f"Incompatible procedure units: {channel.channel_id}")
                    ids = answers.get("procedures")
                    if not isinstance(ids, list) or not ids:
                        blockers.append("Choose supported procedure IDs")
                    else:
                        from .runtime import ProcedureLibrary, validate_procedure

                        candidate_library = ProcedureLibrary(config)
                        if self.node.extensions["procedures"].skills_root:
                            candidate_library.load_directory(self.node.extensions["procedures"].skills_root)

                        for pid in ids:
                            proc = candidate_library.get(str(pid)) or self.node.extensions[
                                "procedures"
                            ].library.get(str(pid))
                            if not proc or validate_procedure(proc.raw, config):
                                blockers.append(f"Unsupported procedure: {pid}")
                    if str(answers.get("safe_state", "")).lower() not in {
                        "deenergized",
                        "de-energized",
                        "output off",
                    }:
                        blockers.append("Supported safe state is deenergized / output off")
                    preview = propose_rig(self.node._current_rig_raw(), document)
                except (ValueError, TypeError, KeyError) as exc:
                    blockers.append(str(exc))
            else:
                blockers.append("Provide a structured rig document; unknown values cannot be guessed")
            value.update(status="needs_evidence" if blockers else "proposed", blockers=blockers)
            if not blockers:
                value["proposal"] = preview
            else:
                value.pop("proposal", None)
            write_json_atomic(self.root / f"{value['interview_id']}.json", value)
            return 200, value

    def application(self, identifier: str, document: dict[str, Any], revision: Any) -> dict[str, Any]:
        value = self.read(identifier)
        if (
            value["revision"] != revision
            or value["status"] != "proposed"
            or canonical_hash(document) != value.get("proposal", {}).get("next_hash")
        ):
            raise HttpError(409, "Interview revision/proposal does not match this application")
        return value

    def bind(self, value: dict[str, Any], config_hash: str) -> None:
        value = copy.deepcopy(value)
        value.update(
            status="applied", applied_config_hash=config_hash, applied_at=datetime.now(UTC).isoformat()
        )
        write_json_atomic(
            self.node.runtime.evidence_dir / "configuration_history" / f"{config_hash}.interview.json", value
        )
        with self.lock:
            current = self.read(value["interview_id"])
            if current["revision"] == value["revision"]:
                write_json_atomic(self.root / f"{value['interview_id']}.json", value)

    def evidence(self) -> dict[str, Any]:
        config_hash = self.node.config.config_hash
        root = self.node.runtime.evidence_dir / "configuration_history"
        result: dict[str, Any] = {}
        history = root / f"{config_hash}.json"
        if history.is_file():
            value = json.loads(history.read_text())
            result.update(configuration_history=value, revalidation=value["revalidation"])
        interview = root / f"{config_hash}.interview.json"
        if interview.is_file():
            value = json.loads(interview.read_text())
            result.update(interview=value, calibration_records=value["answers"]["calibration_records"])
        from .revalidation import test_profile

        result["test_profile"] = test_profile(self.node.config)
        return result


def install_interviews(node: EdgeNode) -> InterviewService:
    service = InterviewService(node)
    node.extensions["interviews"] = service
    node.add_route("GET", "/v1/commissioning/templates", service.templates, "read_rig")
    # Proposal authority is distinct from configuration application authority.
    for method, suffix, handler in [
        ("GET", "", service.listing),
        ("POST", "", service.create),
        ("GET", "/{interview_id}", service.get),
        ("PATCH", "/{interview_id}", service.update),
        ("POST", "/{interview_id}/answers", service.update),
        ("POST", "/{interview_id}/propose", service.propose),
    ]:
        node.add_route(method, "/v1/commissioning/interviews" + suffix, handler, "commissioning_interview")
    return service
