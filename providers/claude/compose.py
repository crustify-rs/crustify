#!/usr/bin/env python3
"""Compose Crustify's roles for Claude Code, from `agents/` and the campaign's settings.

    compose.py build                  write the agents under providers/claude/agents/: the
                                      stages and the assistant, each after Claude Code's own
                                      system prompt
    compose.py assistant [--cwd DIR]  print the assistant's prompt for the campaign at DIR
    compose.py session-start          the SessionStart hook: in a campaign's repository, tell
                                      a session that is not the assistant how to start it

Standard library only: it runs as a hook, under whatever Python the host has.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROLES = ROOT / "agents"
AGENTS = Path(__file__).resolve().parent / "agents"
SYSTEM_PROMPT = Path(__file__).resolve().parent / "system-prompt.md"
ADDENDUM = Path(__file__).resolve().parent / "assistant.md"
SETTINGS = Path("crustify") / "CRUSTIFY.md"
KINDS = {"port": "translate", "wrap": "translate", "audit": "audit"}

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


#: What the SessionStart hook injects in a campaign's repository when the session is not
#: already Crustify's assistant: how to start it.
HEADER = """This session's repository, `{repo}`, holds a Crustify campaign ({campaign}), and this
session is not Crustify's assistant. The assistant starts with
`claude --agent crustify:assistant-{kind}`; `{{"agent": "crustify:assistant-{kind}"}}` in the
repository's `.claude/settings.json` makes every session opened there start as it."""


def _claude_system_prompt() -> str:
    """Claude Code's own system prompt, which a plugin agent's body replaces."""
    text = SYSTEM_PROMPT.read_text()
    return re.sub(r"^<!--.*?-->\s*", "", text, flags=re.S).strip() + "\n\n---\n\n"


def _role(name: str) -> str:
    return (ROLES / f"{name}.md").read_text()


def _answer(text: str, question: str) -> str | None:
    m = re.search(r"\(`id: " + re.escape(question) + r"`\)(?:.|\n)*?- Answer: `([^`]*)`", text)
    return m.group(1).strip() if m else None


def assistant_prompt(kind: str, root: str) -> str:
    campaign = _role(f"assistant/{kind}")
    part, _, skills = campaign.partition("<!-- SKILLS -->")
    text = (_role("common") + _role("assistant/assistant")
            .replace("<!-- CAMPAIGN -->", part.strip())
            .replace("<!-- CAMPAIGN SKILLS -->", skills.strip()))
    return text.replace("{crustify_root}", root)


def find_campaign(start: Path) -> Path | None:
    for d in (start, *start.parents):
        if (d / SETTINGS).is_file():
            return d
        if (d / ".git").exists():
            return None
    return None


def campaign_kind(repo: Path | None) -> str:
    if repo is None:
        return "translate"
    return KINDS.get(_answer((repo / SETTINGS).read_text(), "campaign") or "", "translate")


def _agent(name: str, description: str, body: str) -> None:
    front = f"---\nname: {name}\ndescription: {json.dumps(description)}\n---\n\n"
    (AGENTS / f"{name}.md").write_text(front + _claude_system_prompt()
                                       + body.replace("{crustify_root}", "${CLAUDE_PLUGIN_ROOT}"))


def build() -> None:
    AGENTS.mkdir(exist_ok=True)
    for stage, description in STAGES.items():
        _agent(stage, description, _role("common") + _role(stage))
    for kind, what in (("translate", "a C-to-Rust port or wrap campaign"),
                       ("audit", "an audit of an existing Rust crate")):
        _agent(f"assistant-{kind}",
               f"Crustify's assistant in {what}: plans and orchestrates the campaign with "
               f"the user. Runs as the main agent of a session in the campaign's repository.",
               assistant_prompt(kind, "{crustify_root}") + "\n---\n\n" + ADDENDUM.read_text())


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "build":
        build()
        return 0
    if cmd == "assistant":
        cwd = Path(argv[argv.index("--cwd") + 1]) if "--cwd" in argv else Path.cwd()
        repo = find_campaign(cwd.resolve())
        print(assistant_prompt(campaign_kind(repo), str(ROOT)))
        return 0
    if cmd == "session-start":
        event = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        repo = find_campaign(Path(event.get("cwd") or os.getcwd()).resolve())
        if repo is None or str(event.get("agent_type", "")).startswith("crustify:assistant"):
            return 0
        answer = _answer((repo / SETTINGS).read_text(), "campaign") or "not configured yet"
        prompt = HEADER.format(repo=repo, campaign=answer, kind=campaign_kind(repo))
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": prompt}}))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
