#!/usr/bin/env python3
"""Compose Crustify's agent for Claude Code, from `agents/crustify.md`.

Claude Code lists the plugin's skills to every agent, so the prompt is composed by the
generic provider without its skill index.

    compose.py build    write providers/claude/agents/crustify.md: Crustify's prompt after
                        Claude Code's own system prompt, which a plugin agent's body
                        replaces

Open it as the main agent of a session: `claude --agent crustify:crustify`.

Standard library only: it runs under whatever Python the host has.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "crustify_generic_compose", ROOT / "providers" / "generic" / "compose.py")
generic = importlib.util.module_from_spec(_spec)  # the neutral composer
_spec.loader.exec_module(generic)
AGENTS = Path(__file__).resolve().parent / "agents"
SYSTEM_PROMPT = Path(__file__).resolve().parent / "system-prompt.md"
DESCRIPTION = ("Crustify: brings C code to safe Rust, porting it, wrapping it or auditing a "
               "crate that meets it. Runs as the main agent of a session.")


def _claude_system_prompt() -> str:
    """Claude Code's own system prompt, which a plugin agent's body replaces."""
    text = SYSTEM_PROMPT.read_text()
    return re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S).strip() + "\n\n---\n\n"


def build() -> None:
    AGENTS.mkdir(exist_ok=True)
    front = f"---\nname: crustify\ndescription: {json.dumps(DESCRIPTION)}\n---\n\n"
    body = generic.prompt(root="${CLAUDE_PLUGIN_ROOT}", index=False)
    (AGENTS / "crustify.md").write_text(front + _claude_system_prompt() + body)


def main(argv: list[str]) -> int:
    if argv == ["build"]:
        build()
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
