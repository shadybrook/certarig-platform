"""Studio-facing agent session: one conversational turn, executed as the agent principal."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from certarig.agent.orchestrator import AgentSession
from certarig.agent.policy import RuleBasedPolicy
from certarig.agent.providers import make_provider
from certarig.agent.providers.fake import FakeProvider
from certarig.agent.skills import SkillIndex
from certarig.agent.tools import ToolRegistry
from certarig.agent.transcript import Transcript
from certarig.edge.bootstrap import DEFAULT_SKILLS_ROOT
from certarig.edge.capabilities import Principal
from certarig.edge.client import InProcessClient
from certarig.edge.server import EdgeNode, HttpError, RequestContext


class AgentService:
    def __init__(self, node: EdgeNode, skills_root: Path | None = None) -> None:
        self.node = node
        self.skills = SkillIndex.load(skills_root or DEFAULT_SKILLS_ROOT)
        self._sessions: dict[str, AgentSession] = {}
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()

    def _provider(self) -> Any:
        import os

        name = os.environ.get("CERTARIG_AGENT_PROVIDER", "fake")
        if name == "fake":
            return FakeProvider(policy=RuleBasedPolicy(self.skills))
        return make_provider(name)

    def _session(self, session_id: str | None) -> AgentSession:
        with self._lock:
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            if self.node.agent_key is None:
                raise HttpError(
                    409, {"error": "this node has no agent principal configured", "code": "no_agent"}
                )
            client = InProcessClient(self.node, agent_key=self.node.agent_key, principal_name="studio-agent")
            registry = ToolRegistry(client, self.skills, poll_s=0.1)
            transcript_dir = self.node.runtime.evidence_dir / "agent_transcripts"
            transcript = Transcript(transcript_dir / "pending.jsonl")
            transcript.path = transcript_dir / f"{transcript.session_id}.jsonl"
            session = AgentSession(self._provider(), registry, transcript)
            self._sessions[session.transcript.session_id] = session
            return session

    def chat(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(
                401 if ctx.principal is Principal.ANONYMOUS else 403, "operator authentication required"
            )
        text = str(ctx.body.get("text") or "").strip()
        if not text:
            raise HttpError(400, "text is required")
        session = self._session(ctx.body.get("session_id"))
        result = session.send(text)
        return 200, {
            "session_id": session.transcript.session_id,
            "text": result.text,
            "stopped_reason": result.stopped_reason,
            "model_calls": result.model_calls,
            "tool_calls": [
                {"name": row.name, "arguments": row.arguments, "ok": row.ok, "result": row.result}
                for row in result.tool_results
            ],
            "transcript": str(session.transcript.path),
        }

    def get_session(self, ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        if ctx.principal is Principal.ANONYMOUS:
            raise HttpError(401, "authentication required")
        session = self._sessions.get(ctx.params["session_id"])
        if session is None:
            raise HttpError(404, "session not found")
        from certarig.agent.orchestrator import summarize_transcript

        return 200, summarize_transcript(str(session.transcript.path))


def install_agent_api(node: EdgeNode, skills_root: Path | None = None) -> AgentService:
    service = AgentService(node, skills_root)
    node.add_route("POST", "/v1/agent/chat", service.chat)
    node.add_route("GET", "/v1/agent/sessions/{session_id}", service.get_session)
    node.extensions["agent"] = service
    return service
