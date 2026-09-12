from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from certarig.sim.stamp_gate import LAB_HAPPY_PATHS, stamp_lab_twin_gate


def test_stamp_lab_twin_gate_writes_stamps(tmp_path: Path, monkeypatch: object) -> None:
    def fake_run(path: Path, out: Path) -> SimpleNamespace:
        dest = Path(out) / "twin_gate"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"{path.parent.parent.name}.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(passed=True, run={"procedure_id": path.parent.parent.name}, failures=[])

    monkeypatch.setattr("certarig.sim.stamp_gate.run_scenario_file", fake_run)  # type: ignore[attr-defined]
    result = stamp_lab_twin_gate(tmp_path)
    assert result["passed"] is True
    assert result["stamp_count"] == len(LAB_HAPPY_PATHS)
    assert len(result["scenarios"]) == 6
