"""``certarig agent`` sub-commands: chat, run one intent, author a procedure, replay a transcript."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

from certarig.edge.bootstrap import DEFAULT_SKILLS_ROOT
from certarig.edge.client import EdgeClient

from .authoring import author_procedure
from .orchestrator import AgentSession, pretty, replay_session, summarize_transcript
from .policy import RuleBasedPolicy
from .providers import ProviderError, make_provider
from .providers.fake import FakeProvider
from .skills import SkillIndex
from .tools import ToolRegistry
from .transcript import Transcript


def _client(args: argparse.Namespace) -> EdgeClient:
    key = args.agent_key or os.environ.get("CERTARIG_AGENT_KEY")
    if not key:
        raise SystemExit(
            "set CERTARIG_AGENT_KEY (or --agent-key) so the agent can authenticate as the agent principal"
        )
    return EdgeClient(args.url, agent_key=key, principal_name=args.name)


def _session(args: argparse.Namespace) -> tuple[AgentSession, ToolRegistry]:
    skills = SkillIndex.load(args.skills_root)
    registry = ToolRegistry(_client(args), skills)
    if args.provider == "fake":
        provider = FakeProvider(policy=RuleBasedPolicy(skills))
    else:
        try:
            provider = make_provider(args.provider, args.model)  # type: ignore[assignment]
        except ProviderError as exc:
            raise SystemExit(str(exc)) from exc
    stamp = time.strftime("%Y%m%dT%H%M%S")
    transcript = Transcript(
        Path(args.transcript_dir) / f"{stamp}-{args.provider}-{uuid.uuid4().hex[:6]}.jsonl"
    )
    session = AgentSession(
        provider,
        registry,
        transcript,
        on_event=(lambda entry: print(pretty(entry), file=sys.stderr, flush=True)) if args.verbose else None,
    )
    return session, registry


def agent_chat(args: argparse.Namespace) -> None:
    session, _ = _session(args)
    print(
        f"CertaRig agent ({session.provider.name}/{session.provider.model}) connected to {args.url}. Ctrl-D to exit."
    )
    try:
        while True:
            try:
                line = input("operator> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            result = session.send(line)
            print(f"agent> {result.text}")
    finally:
        session.close()
        print(f"transcript: {session.transcript.path}", file=sys.stderr)


def agent_run(args: argparse.Namespace) -> None:
    session, _ = _session(args)
    try:
        result = session.send(args.intent)
        print(json.dumps({**result.to_dict(), "transcript": str(session.transcript.path)}, indent=2))
    finally:
        session.close()


def agent_author(args: argparse.Namespace) -> None:
    client = _client(args)
    if args.provider == "fake":
        raise SystemExit("authoring needs a real model provider (anthropic or openai)")
    try:
        provider = make_provider(args.provider, args.model)
    except ProviderError as exc:
        raise SystemExit(str(exc)) from exc
    example = None
    if args.example:
        example = client.get(f"/v1/procedures/{args.example}")["procedure"]
    result = author_procedure(provider, client, args.request, example=example)
    print(
        json.dumps(
            {"ok": result.ok, "errors": result.errors, "attempts": result.attempts, "draft": result.draft},
            indent=2,
        )
    )
    if not result.ok:
        sys.exit(1)


def agent_replay(args: argparse.Namespace) -> None:
    outputs = replay_session(args.transcript, strict=not args.lenient)
    print(json.dumps({"summary": summarize_transcript(args.transcript), "replayed_turns": outputs}, indent=2))


def add_agent_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    agent = subparsers.add_parser("agent", help="LLM agent that operates the rig through the Edge API")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)

    def common(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--url", default="http://127.0.0.1:8080")
        parser.add_argument("--agent-key", default=None)
        parser.add_argument("--name", default="certarig-agent")
        parser.add_argument("--provider", default="fake", choices=["fake", "anthropic", "openai"])
        parser.add_argument("--model", default=None)
        parser.add_argument("--skills-root", default=str(DEFAULT_SKILLS_ROOT))
        parser.add_argument("--transcript-dir", default="evidence/agent_transcripts")
        parser.add_argument("--verbose", action="store_true")

    chat = agent_sub.add_parser("chat", help="interactive operator chat")
    common(chat)
    chat.set_defaults(func=agent_chat)

    run = agent_sub.add_parser("run", help="run a single operator intent and print the result")
    common(run)
    run.add_argument("intent")
    run.set_defaults(func=agent_run)

    author = agent_sub.add_parser("author", help="draft a procedure from a natural-language request")
    common(author)
    author.add_argument("request")
    author.add_argument(
        "--example", default="relay_truth_table", help="existing procedure id to show as reference"
    )
    author.set_defaults(func=agent_author)

    replay = agent_sub.add_parser("replay", help="replay a session transcript offline")
    replay.add_argument("transcript")
    replay.add_argument("--lenient", action="store_true", help="do not fail on context divergence")
    replay.set_defaults(func=agent_replay)
