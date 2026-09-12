from __future__ import annotations

import copy

import yaml

from certarig.agent.authoring import SUBMIT_TOOL, author_procedure
from certarig.agent.providers.fake import FakeProvider, call, say, tool_call
from tests.support import SKILLS_DIR, edge_server

GOOD = yaml.safe_load((SKILLS_DIR / "electronics" / "relay_truth_table" / "procedure.yaml").read_text())


def _new_procedure() -> dict:  # type: ignore[type-arg]
    proc = copy.deepcopy(GOOD)
    proc["id"] = "relay_single_cycle"
    proc["title"] = "Single relay cycle"
    proc["steps"] = proc["steps"][:5]
    proc["evaluate"] = [{"event_observed": "permit_accepted"}]
    return proc


def test_author_repairs_invalid_drafts_and_stores_an_unapproved_draft() -> None:
    broken = _new_procedure()
    broken["steps"][1]["expect"] = {"signal": "ghost_channel", "op": ">", "value": 1}
    duplicate = copy.deepcopy(GOOD)  # reuses an existing id
    provider = FakeProvider(
        script=[
            say("Thinking..."),  # forgot to call the tool
            call(tool_call("submit_procedure", {"procedure": duplicate})),
            call(tool_call("submit_procedure", {"procedure": broken})),
            call(tool_call("submit_procedure", {"procedure": _new_procedure()})),
        ]
    )
    with edge_server() as edge:
        result = author_procedure(provider, edge.agent(), "run one relay cycle", example=GOOD, max_attempts=4)
        assert result.ok, result.errors
        assert result.attempts == 4
        assert result.history[0]["errors"] == ["the model did not call submit_procedure"]
        assert any("already exists" in e for e in result.history[1]["errors"])
        assert any("ghost_channel" in e for e in result.history[2]["errors"])
        assert result.draft is not None and result.draft["approved"] is False
        draft_hash = result.draft["procedure_hash"]
        drafts = edge.operator().get("/v1/procedures/drafts")["drafts"]
        assert any(d["procedure_hash"] == draft_hash for d in drafts)
        # not runnable until an operator approves it
        assert "relay_single_cycle" not in {p["id"] for p in edge.operator().procedures()["procedures"]}
        edge.operator().post(f"/v1/procedures/drafts/{draft_hash}/approve", {})
        assert "relay_single_cycle" in {p["id"] for p in edge.operator().procedures()["procedures"]}
        # the tool the model saw is the single submit tool
        assert provider.calls[0]["tools"] == [SUBMIT_TOOL.name]
        assert "Rig signals" in provider.calls[0]["system"]


def test_author_gives_up_after_max_attempts() -> None:
    broken = _new_procedure()
    del broken["steps"]
    provider = FakeProvider(script=[call(tool_call("submit_procedure", {"procedure": broken}))] * 2)
    with edge_server() as edge:
        result = author_procedure(provider, edge.agent(), "bad", max_attempts=2)
        assert result.ok is False
        assert result.attempts == 2
        assert result.errors
        assert edge.operator().get("/v1/procedures/drafts")["drafts"] == []
