#!/usr/bin/env python3
"""Compose Crustify's system prompt for any host, from `agents/crustify.md` and `skills/`.

    compose.py          print the prompt, with the index of every skill at its
                        `<!-- SKILL INDEX -->` marker and `{crustify_root}` as this
                        checkout's path

A host that lists the skills itself, as Claude Code and Codex do, composes without the
index: its provider imports this module.

Standard library only: it runs under whatever Python the host has.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPT = ROOT / "agents" / "crustify.md"
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


def prompt(root: str = str(ROOT), index: bool = True) -> str:
    """Crustify's system prompt."""
    text = PROMPT.read_text().replace("<!-- SKILL INDEX -->\n\n", skill_index() + "\n\n" if index else "")
    return text.replace("{crustify_root}", root)


def main(argv: list[str]) -> int:
    if argv:
        print(__doc__, file=sys.stderr)
        return 2
    print(prompt(), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
