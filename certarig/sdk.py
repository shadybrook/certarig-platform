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


class CertaRig:
    def __init__(self, url: str, operator_key: str, *, name: str = "sdk") -> None:
        self.client = EdgeClient(url, operator_key=operator_key, principal_name=name)

    def health(self) -> dict[str, Any]:
        return self.client.health()

    def live(self) -> dict[str, Any]:
        return self.client.state()

    def run(self, procedure_id: str, label: str | None = None) -> dict[str, Any]:
        return self.client.run_procedure(procedure_id, label)

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
