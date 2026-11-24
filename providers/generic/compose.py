#!/usr/bin/env python3
"""Compose Crustify's system prompt for any host, from `agents/crustify.md` and `skills/`.

    compose.py [agent]  print the prompt of `agents/<agent>.md`, `crustify` unless named,
                        with the index of every skill at its `<!-- SKILL INDEX -->`
                        marker and `{crustify_root}` as this checkout's path

A host that lists the skills itself, as Claude Code and Codex do, composes without the
index: its provider imports this module.

Standard library only: it runs under whatever Python the host has.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents"
PROMPT = AGENTS / "crustify.md"
SKILLS = ROOT / "skills"


def skill_index() -> str:
    """Every skill's name and description, by group."""
    lines = []
    for group in sorted(d for d in SKILLS.iterdir() if d.is_dir()):
        for skill in sorted(group.rglob("SKILL.md")):
            front = skill.read_text().split("---", 2)[1]
            name = re.search(r"^name: (.+)$", front, re.M).group(1).strip()
            description = json.loads(re.search(r"^description: (.+)$", front, re.M).group(1))
            lines.append(f"- `{name}` ({skill.parent.relative_to(SKILLS)}): {description}")
    return "\n".join(lines)


def prompt(root: str = str(ROOT), index: bool = True, agent: str = "crustify") -> str:
    """The system prompt of one of Crustify's agents, `agents/<agent>.md`."""
    text = (AGENTS / f"{agent}.md").read_text().replace("<!-- SKILL INDEX -->\n\n", skill_index() + "\n\n" if index else "")
    return text.replace("{crustify_root}", root)


def main(argv: list[str]) -> int:
    if len(argv) > 1 or (argv and not (AGENTS / f"{argv[0]}.md").is_file()):
        print(__doc__, file=sys.stderr)
        return 2
    print(prompt(agent=argv[0] if argv else "crustify"), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
