#!/usr/bin/env python3
"""Compose Crustify's agents for Claude Code, from `agents/`.

Claude Code lists the plugin's skills to every agent, so the prompts are composed by the
generic provider without its skill index.

    compose.py build    write the agents under providers/claude/agents/: the stages and the
                        assistant, each after Claude Code's own system prompt

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

#: Each stage's agent: its description is the rule the assistant routes a run by.
STAGES = {
    "planner": "Crustify's planner: runs one planner run of a translation campaign on its "
               "planner branch, deciding modules.json, dependencies.json and the plan "
               "fields of schedule.json, in one commit. Use for every planner run.",
    "binder": "Crustify's binder: runs one `wrap` batch from its task.json in its worktree: "
              "binds its items behind a safe Rust API, tests them, and lands them on its "
              "wave branch. Use for every `wrap` batch.",
    "translator": "Crustify's translator: runs one `port`, `port/layout`, `port/memory` or "
                  "`port/unexport` batch from its task.json in its worktree: ports its "
                  "items to safe Rust, tests them, and lands them on its wave branch. Use "
                  "for every port batch.",
    "reviewer": "Crustify's reviewer: runs one review batch from its task.json in its "
                "worktree: reviews landed commits or a crate's paths for its objectives, "
                "files and reproduces findings, fixes them under `fix`, and lands on its "
                "wave branch. Use for every review batch.",
}


def _claude_system_prompt() -> str:
    """Claude Code's own system prompt, which a plugin agent's body replaces."""
    text = SYSTEM_PROMPT.read_text()
    return re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S).strip() + "\n\n---\n\n"


def _agent(name: str, description: str, body: str) -> None:
    front = f"---\nname: {name}\ndescription: {json.dumps(description)}\n---\n\n"
    (AGENTS / f"{name}.md").write_text(front + _claude_system_prompt()
                                       + body.replace("{crustify_root}", "${CLAUDE_PLUGIN_ROOT}"))


def build() -> None:
    AGENTS.mkdir(exist_ok=True)
    for stage, description in STAGES.items():
        _agent(stage, description, generic.prompt(stage, root="{crustify_root}", index=False))
    for kind, what in (("translate", "a C-to-Rust port or wrap campaign"),
                       ("audit", "an audit of an existing Rust crate")):
        _agent(f"assistant-{kind}",
               f"Crustify's assistant in {what}: plans and orchestrates the campaign with "
               f"the user. Runs as the main agent of a session in the campaign's repository.",
               generic.prompt("assistant", kind, "{crustify_root}", index=False))


def main(argv: list[str]) -> int:
    if argv == ["build"]:
        build()
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
