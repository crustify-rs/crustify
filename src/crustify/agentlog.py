"""Per-agent output sinks.

A CLI-backed agent is a subprocess whose stdout crustify owns. The providers
run in their streaming-JSON mode (claude ``--output-format stream-json``,
codex ``--json``); crustify renders that stream to the console as it happens
and keeps none of it. What a run leaves is its ``<stem>.session.json`` (see
:class:`crustify.core.agentlog.AgentLog`); the CLI's own transcript is the
full record, and ``crustify usage`` prices it.
"""

from __future__ import annotations

from pathlib import Path


from crustify.core.agentlog import AgentLog


def open_agent_log(log_root: Path, stem: str, *, agent: str | None = None,
                   workdir: Path | None = None,
                   index_dir: Path | None = None) -> AgentLog:
    """Build an :class:`AgentLog` for ``stem`` in the requested directory;
    its session record names ``agent``."""
    from crustify import config as _cfg

    return AgentLog(
        log_root,
        stem,
        console=_cfg.LOG_TO_CONSOLE,
        metadata={"agent": agent} if agent else None,
        index_dir=index_dir,
        # Only the index needs the workdir: a resume launches there. The
        # tracked record would carry a dead worktree path, or a machine's.
        index_facts={"workdir": str(workdir)} if workdir else None,
    )
