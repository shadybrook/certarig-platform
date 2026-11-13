"""Thin public client around :class:`certarig.edge.client.EdgeClient`.

Happy path::

    from certarig.sdk import CertaRig

    rig = CertaRig("http://127.0.0.1:8080", operator_key="...")
    print(rig.health()["ready_to_arm"])
    print(rig.live()["guardrail"]["reason"])
    run = rig.run("relay_truth_table")
    bundle = rig.pull_evidence()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from certarig.edge.client import EdgeClient
from certarig.platform.client import PlatformClient as PlatformClient


class CertaRig:
    def __init__(self, url: str, operator_key: str, *, name: str = "sdk") -> None:
        self.client = EdgeClient(url, operator_key=operator_key, principal_name=name)

    def health(self) -> dict[str, Any]:
        return self.client.health()

    def live(self) -> dict[str, Any]:
        return self.client.state()

    def run(
        self, procedure_id: str, label: str | None = None, *, approval_id: str | None = None
    ) -> dict[str, Any]:
        return self.client.run_procedure(procedure_id, label, approval_id=approval_id)

    def create_interview(self) -> dict[str, Any]:
        return self.client.create_interview()

    def interview(self, interview_id: str) -> dict[str, Any]:
        return self.client.interview(interview_id)

    def answer_interview(
        self, interview_id: str, expected_revision: int, answers: dict[str, Any], sources: dict[str, str]
    ) -> dict[str, Any]:
        return self.client.answer_interview(interview_id, expected_revision, answers, sources)

    def propose_interview(self, interview_id: str) -> dict[str, Any]:
        return self.client.propose_interview(interview_id)

    def sandbox_preflight(self) -> dict[str, Any]:
        return self.client.sandbox_preflight()

    def create_sandbox(self, source: str = "active", procedure_id: str | None = None) -> dict[str, Any]:
        return self.client.create_sandbox(source, procedure_id)

    def sandbox(self, sandbox_id: str) -> dict[str, Any]:
        return self.client.sandbox(sandbox_id)

    def run_sandbox(self, sandbox_id: str, kind: str, source: str = "") -> dict[str, Any]:
        return self.client.run_sandbox(sandbox_id, kind, source)

    def propose_sandbox(self, sandbox_id: str, job_id: str, kind: str = "configuration") -> dict[str, Any]:
        return self.client.propose_sandbox(sandbox_id, job_id, kind)

    def export_sandbox(self, sandbox_id: str, out_file: str | Path) -> Path:
        target = Path(out_file)
        target.write_bytes(self.client.export_sandbox(sandbox_id))
        return target

    def pull_evidence(self, out_dir: str | Path | None = None, run_id: str | None = None) -> dict[str, Any]:
        export = self.client.export_evidence(run_id=run_id)
        if out_dir is None:
            return export
        target = Path(out_dir)
        target.mkdir(parents=True, exist_ok=True)
        data = self.client.download(str(export["path"]))
        path = target / str(export["filename"])
        path.write_bytes(data)
        return {**export, "saved_to": str(path)}
