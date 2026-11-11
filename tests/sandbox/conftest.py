import json

import pytest
import yaml

from certarig.sandbox.contracts import snapshot
from tests.support import CONFIG_DIR, SKILLS_DIR


@pytest.fixture
def value():  # type: ignore[no-untyped-def]
    raw = json.loads((CONFIG_DIR / "rig.thermal.capstone.json").read_text())
    procedure = yaml.safe_load((SKILLS_DIR / "reliability/thermal_soak/procedure.yaml").read_text())
    return snapshot(raw, procedure, "base")


@pytest.fixture(scope="session")
def rehearsal_files(tmp_path_factory):  # type: ignore[no-untyped-def]
    # Trusted simulator fixture; not an execution-isolation qualification.
    from certarig.sandbox.worker import rehearse

    raw = json.loads((CONFIG_DIR / "rig.thermal.capstone.json").read_text())
    procedure = yaml.safe_load((SKILLS_DIR / "reliability/thermal_soak/procedure.yaml").read_text())
    model = snapshot(raw, procedure, "base")
    root = tmp_path_factory.mktemp("trusted-rehearsal")
    out = root / "out"
    out.mkdir()
    scratch = root / "scratch"
    scratch.mkdir()
    rehearse({**model, "seed": 11}, out, scratch)
    return {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
