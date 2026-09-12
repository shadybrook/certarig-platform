"""Run the lab happy-path scenarios so twin-gate stamps exist for a raspberry_pi node."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .scenario import SKILLS_DIR, run_scenario_file

LAB_HAPPY_PATHS = (
    "electronics/relay_truth_table/scenarios/happy_path.yaml",
    "electronics/adc_validation/scenarios/happy_path.yaml",
    "electronics/estop_anti_restart/scenarios/happy_path.yaml",
    "process/pressure_guardrail/scenarios/happy_path.yaml",
    "process/flow_guardrail/scenarios/happy_path.yaml",
    "process/dual_pot_guardrail/scenarios/happy_path.yaml",
)


def stamp_lab_twin_gate(out: str | Path) -> dict[str, Any]:
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failed = 0
    for relative in LAB_HAPPY_PATHS:
        path = SKILLS_DIR / relative
        result = run_scenario_file(path, target)
        rows.append(
            {
                "scenario": relative,
                "passed": result.passed,
                "procedure_id": (result.run or {}).get("procedure_id"),
                "failures": result.failures,
            }
        )
        failed += 0 if result.passed else 1
    stamps = sorted((target / "twin_gate").glob("*.json")) if (target / "twin_gate").is_dir() else []
    return {
        "out": str(target.resolve()),
        "passed": failed == 0,
        "scenarios": rows,
        "stamps": [str(path.name) for path in stamps],
        "stamp_count": len(stamps),
    }
