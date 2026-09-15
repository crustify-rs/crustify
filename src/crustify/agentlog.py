"""Per-agent output sinks.

A CLI-backed agent is a subprocess whose stdout crustify owns, so there is
no printer abstraction and no rendered-then-reparsed format.

The providers are invoked in their streaming-JSON mode (claude
``--output-format stream-json``, codex ``--json``) rather than their
human-readable default. Both offer a text mode, but a process emits one
stream in one format, and the text modes do not carry what crustify needs
to account for a run: claude's is the final message and nothing else,
codex's reports tokens but never cost. So crustify takes the machine
format and splits the parsed stream two ways:

  ``<stage>.log``        a compact human rendering - what ran, what it
                         called, what it said. This is what you read when
                         an agent fails. Nothing parses it, so its shape is
                         free to change.

  ``<stem>.usage.json``  this run's accounting in CRUSTIFY's shape, built by
                         the backend from the CLI's session transcript - not a
                         provider object passed through. The one file anything
                         parses; ``crustify ... cost`` reads it.

The raw stream itself is never stored. Tool-result events embed whole file
bodies and command output, so a port wave's raw streams would outweigh
every other artifact crustify writes - and everything worth keeping from
them is already in one of the two files above.

The console receives the same text as ``<stage>.log``. Translation harnesses
pass an explicit wave-local output directory and generated batch id; other
agent callers use their campaign-local fallback directory.
"""

from __future__ import annotations

from pathlib import Path


from crustify.core.agentlog import AgentLog


def open_agent_log(log_root: Path, stem: str, *, stage: str | None = None) -> AgentLog:
    """Build an :class:`AgentLog` for ``stem`` in the requested directory."""
    from crustify import config as _cfg

    return AgentLog(
        log_root,
        stem,
        console=_cfg.LOG_TO_CONSOLE,
        metadata={"stage": stage} if stage else None,
    )
