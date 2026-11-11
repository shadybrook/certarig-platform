from __future__ import annotations

import copy
import io
import tarfile
from unittest.mock import patch

import pytest

from certarig.sandbox.contracts import (
    LIMITS,
    binding,
    blockers,
    identifier,
    safe_name,
    snapshot,
    verify_rehearsal,
)
from certarig.sandbox.engine import DockerEngine, collect_archive, resource_preflight
from certarig.sandbox.worker import rehearse


@pytest.mark.parametrize("name", ["", "../secret", "/etc/passwd", "a\\b", "a:b", "./x", "a\n"])
def test_invalid_paths(name):  # type: ignore[no-untyped-def]
    assert not safe_name(name)
    with pytest.raises(ValueError):
        identifier(name, "sbx")


def test_snapshot_and_binding(value):  # type: ignore[no-untyped-def]
    assert not blockers(value)
    assert binding(value, "image", 1) != binding(value, "image", 2)
    changed = copy.deepcopy(value)
    changed["document"]["hardware"]["simulator"]["thermal"]["heat_input_w"] += 1
    assert binding(value, "image", 1) != binding(changed, "image", 1)
    assert verify_rehearsal(value, {})["passed"] is False
    for key, bad in [("unit", "bar"), ("calibration_id", ""), ("source", {})]:
        changed = copy.deepcopy(value)
        changed["document"]["channels"][0][key] = bad
        assert blockers(changed)
    changed = copy.deepcopy(value)
    changed["document"]["channels"][0]["source"] = {"address": "mqtt://secret@host"}
    with pytest.raises(ValueError):
        snapshot(changed["document"], value["procedure"], "base")
    assert blockers({})


def archive(name="out/x.txt", kind=tarfile.REGTYPE):  # type: ignore[no-untyped-def]
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        item = tarfile.TarInfo(name)
        item.type = kind
        item.size = 1 if kind == tarfile.REGTYPE else 0
        tar.addfile(item, io.BytesIO(b"x") if item.size else None)
    return data.getvalue()


@pytest.mark.parametrize(
    "name,kind",
    [
        ("out/../x", tarfile.REGTYPE),
        ("out/link", tarfile.SYMTYPE),
        ("out/a.html", tarfile.REGTYPE),
        ("elsewhere/x.txt", tarfile.REGTYPE),
    ],
)
def test_archive_rejects_unsafe(name, kind):  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        collect_archive(archive(name, kind))


def test_archive_and_launch_policy(tmp_path):  # type: ignore[no-untyped-def]
    assert collect_archive(archive()) == {"x.txt": b"x"}
    with pytest.raises(ValueError):
        DockerEngine("latest", tmp_path)
    engine = DockerEngine("sha256:" + "1" * 64, tmp_path)
    args = engine.create_args("crsb-job_" + "1" * 16, "python", 120)
    for flag in [
        "--read-only",
        "--network",
        "none",
        "--pids-limit",
        "64",
        "--cap-drop",
        "ALL",
        "--memory-swap",
        "512m",
    ]:
        assert flag in args
    assert "--privileged" not in args and "--mount" not in args and "-v" not in args
    with (
        patch("certarig.sandbox.engine.shutil.disk_usage") as usage,
        patch("certarig.sandbox.engine.platform.system", return_value="Linux"),
    ):
        usage.return_value.free = 1
        assert not resource_preflight(tmp_path)["ready"]
        usage.return_value.free = LIMITS["disk_free_bytes"]
        assert resource_preflight(tmp_path)["ready"]


def test_trusted_rehearsal_raw_replay(value, tmp_path):  # type: ignore[no-untyped-def]
    # Trusted simulator unit test only. This is not a container-isolation qualification.
    out = tmp_path / "out"
    out.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    rehearse({**value, "seed": 11}, out, scratch)
    files = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
    result = verify_rehearsal(value, files)
    assert result["passed"], result
    forged = dict(files)
    forged["stale_source.csv"] = files["candidate_procedure.csv"]
    assert not verify_rehearsal(value, forged)["passed"]
    assert all(p.is_file() for p in out.iterdir())


def test_pressure_flow_rehearsal(tmp_path):  # type: ignore[no-untyped-def]
    import json

    import yaml

    from tests.support import CONFIG_DIR, SKILLS_DIR

    raw = json.loads((CONFIG_DIR / "rig.sim.json").read_text())
    for c in raw["channels"]:
        c["source"] = {"kind": "virtual", "address": "fixture." + c["channel_id"]}
    procedure = yaml.safe_load((SKILLS_DIR / "process/pressure_guardrail/procedure.yaml").read_text())
    value = snapshot(raw, procedure, "base")
    out = tmp_path / "out"
    out.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    rehearse({**value, "seed": 11}, out, scratch)
    assert verify_rehearsal(value, {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()})["passed"]
