"""Skill index: SKILL.md files with YAML front matter, matched to operator intents."""

from __future__ import annotations

import builtins
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Skill:
    name: str
    domain: str
    procedure_id: str | None
    intents: tuple[str, ...]
    body: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        first_heading = next(
            (line.lstrip("# ").strip() for line in self.body.splitlines() if line.startswith("#")), ""
        )
        return {
            "name": self.name,
            "domain": self.domain,
            "procedure_id": self.procedure_id,
            "intents": list(self.intents),
            "title": first_heading,
        }


_STOPWORDS = {
    "the", "a", "an", "to", "of", "and", "or", "i", "want", "please", "run", "do", "on", "for", "me",
    "is", "it", "this", "that", "rig", "bench", "with", "my", "our", "now", "in", "at", "be", "can", "you",
}  # fmt: skip


def _tokens(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if word not in _STOPWORDS}


def load_skill(path: str | Path) -> Skill:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    match = _FRONT_MATTER.match(text)
    if not match:
        raise ValueError(f"{source}: SKILL.md needs YAML front matter")
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    procedure_file = meta.get("procedure")
    procedure_id: str | None = None
    if procedure_file:
        procedure_path = source.parent / str(procedure_file)
        if procedure_path.is_file():
            procedure_id = str((yaml.safe_load(procedure_path.read_text(encoding="utf-8")) or {}).get("id"))
    return Skill(
        name=str(meta.get("name") or source.parent.name),
        domain=str(meta.get("domain") or source.parent.parent.name),
        procedure_id=procedure_id,
        intents=tuple(str(item) for item in meta.get("intents", [])),
        body=body,
        path=str(source),
        metadata=dict(meta),
    )


class SkillIndex:
    def __init__(self, skills: list[Skill]) -> None:
        self.skills = {skill.name: skill for skill in skills}

    @classmethod
    def load(cls, root: str | Path) -> SkillIndex:
        return cls([load_skill(path) for path in sorted(Path(root).rglob("SKILL.md"))])

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def list(self) -> builtins.list[dict[str, Any]]:
        return [skill.summary() for skill in self.skills.values()]

    def match(self, request: str, limit: int = 3) -> builtins.list[tuple[Skill, float]]:
        """Rank skills by token overlap between the request and their intents/name."""
        words = _tokens(request)
        scored: builtins.list[tuple[Skill, float]] = []
        for skill in self.skills.values():
            best = 0.0
            for intent in (*skill.intents, skill.name.replace("_", " ")):
                intent_words = _tokens(intent)
                if not intent_words:
                    continue
                overlap = len(words & intent_words) / len(intent_words)
                best = max(best, overlap)
            if best > 0:
                scored.append((skill, round(best, 3)))
        scored.sort(key=lambda item: (-item[1], item[0].name))
        return scored[:limit]

    def prompt_index(self) -> str:
        lines = []
        for skill in self.skills.values():
            intents = "; ".join(skill.intents[:3])
            lines.append(
                f"- {skill.name} ({skill.domain}) procedure={skill.procedure_id or 'none'}: {intents}"
            )
        return "\n".join(lines)
