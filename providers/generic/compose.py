#!/usr/bin/env python3
"""Compose Crustify's agents for any host, from `agents/` and `skills/`.

    compose.py <agent> [<kind>]   print the agent's prompt: planner, binder, translator,
                                  reviewer, or assistant with its campaign kind, translate
                                  (the default) or audit

Each prompt is `agents/common.md`, with the index of every skill at its
`<!-- SKILL INDEX -->` marker, then the agent's own file, with `{crustify_root}` as this
checkout's path. A host that lists the skills itself, as Claude Code does, composes without
the index: its provider imports this module.

Standard library only: it runs under whatever Python the host has.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents"
SKILLS = ROOT / "skills"
STAGES = ("planner", "binder", "translator", "reviewer")
KINDS = ("translate", "audit")


def skill_index() -> str:
    """Every skill's name and description, by group."""
    lines = []
    for group in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        for skill in sorted(group.rglob("SKILL.md")):
            front = skill.read_text().split("---", 2)[1]
            name = re.search(r"^name: (.+)$", front, re.M).group(1).strip()
            description = json.loads(re.search(r"^description: (.+)$", front, re.M).group(1))
            lines.append(f"- `{name}` ({skill.parent.parent.relative_to(SKILLS)}): {description}")
    return "\n".join(lines)


def _file(name: str) -> str:
    return (AGENTS / f"{name}.md").read_text()


def prompt(agent: str, kind: str = "translate", root: str = str(ROOT), index: bool = True) -> str:
    """The agent's prompt; `kind` selects the assistant's campaign."""
    common = _file("common").replace("<!-- SKILL INDEX -->\n\n", skill_index() + "\n\n" if index else "")
    if agent == "assistant":
        role, _, workflow = _file(f"assistant/{kind}").partition("<!-- WORKFLOW -->")
        body = (_file("assistant/assistant")
                .replace("<!-- CAMPAIGN ROLE -->", role.strip())
                .replace("<!-- CAMPAIGN WORKFLOW -->", workflow.strip()))
    elif agent in STAGES:
        body = _file(agent)
    else:
        raise SystemExit(f"unknown agent {agent!r}: one of {', '.join(STAGES)}, assistant")
    return (common + body).replace("{crustify_root}", root)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help") or len(argv) > 2 or (argv[1:] and argv[1] not in KINDS):
        print(__doc__, file=sys.stderr)
        return 2
    print(prompt(argv[0], *argv[1:]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
