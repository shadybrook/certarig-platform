"""Authoring templates, draft reload, OpenAPI route table."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from certarig.edge.authoring_templates import build_procedure, templates
from certarig.edge.config import load_config
from certarig.edge.openapi import generate_openapi, routes_from
from certarig.edge.runtime.library import ProcedureLibrary, validate_procedure
from tests.support import CONFIG_DIR, edge_server


def test_templates_validate_against_the_sim_rig() -> None:
    config = load_config(CONFIG_DIR / "rig.sim.json")
    assert {row["id"] for row in templates()} >= {"guardrail_trip", "soak", "blank"}
    soak = build_procedure("soak", signal="pressure", concept="pressure", hold_s=1.0)
    assert validate_procedure(soak, config) == []
    assert soak["steps"][-1]["command"] == "safe"


def test_drafts_reload_from_disk(tmp_path: Path) -> None:
    config = load_config(CONFIG_DIR / "rig.sim.json")
    drafts = tmp_path / "procedure_drafts"
    drafts.mkdir()
    procedure = build_procedure("blank", title="Disk draft")
    (drafts / "disk-draft.yaml").write_text(yaml.safe_dump(procedure), encoding="utf-8")
    library = ProcedureLibrary(config, drafts_dir=drafts)
    assert library.drafts()
    assert library.drafts()[0]["id"] == "untitled"


def test_openapi_matches_live_routes() -> None:
    with edge_server() as edge:
        document = generate_openapi(edge.node)
        paths = set(document["paths"])
        live = {path for _method, path in routes_from(edge.node)}
        assert paths == live
        artifact = Path(__file__).resolve().parents[2] / "certarig" / "schemas" / "openapi.yaml"
        if artifact.is_file():
            loaded = yaml.safe_load(artifact.read_text(encoding="utf-8"))
            assert set(loaded["paths"]) == live
        json.dumps(document)
