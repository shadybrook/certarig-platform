"""Every shipped scenario must pass in the simulator. This is the digital-twin regression suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from certarig.sim.cli import SIM_SCENARIOS
from certarig.sim.scenario import ROOT, SKILLS_DIR, discover_scenarios, load_scenario, run_scenario_file

SCENARIOS = discover_scenarios(SKILLS_DIR, SIM_SCENARIOS)


def test_scenarios_were_discovered() -> None:
    assert len(SCENARIOS) >= 13
    for path in SCENARIOS:
        load_scenario(path)  # schema-valid


@pytest.mark.parametrize("path", SCENARIOS, ids=[str(p.relative_to(ROOT)) for p in SCENARIOS])
def test_scenario_passes(path: Path, tmp_path: Path) -> None:
    result = run_scenario_file(path, tmp_path)
    assert result.passed, result.failures
    assert (tmp_path / _slug(result.name) / "scenario_result.json").is_file()
    if result.run is not None:
        assert (Path(result.evidence_dir or "") / "run.json").is_file()


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-")[:60]
