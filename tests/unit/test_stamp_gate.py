from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from certarig.edge.twin_gate import accept_twin_gate
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


def test_accept_twin_gate_copies_valid_stamps(tmp_path: Path) -> None:
    source = tmp_path / "sim" / "twin_gate"
    source.mkdir(parents=True)
    (source / "hash1.json").write_text(
        '{"procedure_hash": "hash1", "procedure_id": "relay_truth_table"}', encoding="utf-8"
    )
    (source / "empty.json").write_text("{}", encoding="utf-8")
    dest = tmp_path / "sidecar"
    result = accept_twin_gate(tmp_path / "sim", dest)
    assert result["count"] == 1
    assert result["skipped"] == ["empty.json"]
    assert (dest / "twin_gate" / "hash1.json").is_file()
