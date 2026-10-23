"""Pluggable agent backends for a crustify pipeline stage.

A ``Backend`` abstracts the provider-CLI call used by both translation and
agentic audit modes to drive an LLM agent.

Each backend shells out to a provider CLI, one subprocess per agent, and
streams its stdout into the agent's :class:`~crustify.agentlog.AgentLog`.
Running the agent out-of-process is what makes per-agent accounting exact:
the provider reports usage for that invocation and nothing else, so
concurrent agents cannot interleave their numbers.

The contract is deliberately thin, matching what crustify actually needs:
render a prompt, run an agent confined to a shell tool in a work dir, and
stream its output to a log. Stage completion is judged by the caller via
on-disk artifacts, so a backend's return value is discarded.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol, runtime_checkable

from pathlib import Path

from crustify.core.agentlog import AgentLog
from crustify.core.models import Route


def _atomic_write_text(path: Path, text: str) -> None:
    """Publish shared prompt text without exposing a truncated intermediate."""
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@contextmanager
def system_prompt_file(
    text: str, *, directory: Path | None = None,
) -> Iterator[Path]:
    """Hand a CLI its system text as a file, and take the file back after.

    Neither backend may pass the preamble on the command line: a single argv
    element is capped at ``MAX_ARG_STRLEN`` -- 32 pages, 128 KiB on Linux --
    however large ``ARG_MAX`` is, and a translate preamble exceeds it. Both
    CLIs read the slot from a file instead (``--system-prompt-file`` and
    ``--append-system-prompt-file`` for claude, ``model_instructions_file``
    for codex), and each reads it while starting up, so the file is needed
    only until the CLI exits.

    The name is unique per run. A provider home is shared across a wave's
    worktrees, so a fixed name would have N concurrent agents writing and
    unlinking one path; ``mkstemp`` creates the file exclusively, which is
    what makes publication atomic without a rename.
    """
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(
        dir=directory, prefix="crustify-base-prompt-", suffix=".md"
    )
    path = Path(name)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        yield path
    finally:
        path.unlink(missing_ok=True)


@runtime_checkable
class Backend(Protocol):
    def run(
        self,
        *,
        name: str,
        route: Route,
        prompt: str,
        system_preamble: str,
        work_dir: str,
        log: AgentLog,
        billing: str = "subscription",
        effort: str | None = None,
        override_base_prompt: bool = False,
        provider_home: Path | None = None,
        interactive: bool = False,
        resume: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Drive one agent to completion.

        ``route`` fixes the CLI backend, provider and model before execution;
        ``prompt`` arrives as the first user message. ``billing`` and
        ``provider_home`` select authentication without either backend importing
        a mode-specific config or layout module. The return value is
        intentionally unused -- success is judged by on-disk artifacts.

        ``system_preamble`` goes to the CLI's system-instruction slot instead,
        The two CLIs offer different system slots -- Claude can append while
        Codex can only replace -- so each backend places the same role-owned
        string its own way; the content never diverges.

        ``interactive`` hands the terminal to the CLI's own interface instead of
        streaming a headless run into ``log``: the person at the terminal reads
        the agent and answers it. The session transcript still yields the
        usage record once the CLI exits.

        ``resume`` continues the session with that id instead of starting one:
        same id, same transcript. ``session_id`` is the id a new session takes,
        where the CLI accepts one (claude does, codex picks its own).
        """
        ...


def get_backend(name: str) -> Backend:
    """Resolve a backend by name (see :mod:`crustify.core.models`)."""
    if name == "claude_cli":
        from crustify.agents.backends.claude_cli import ClaudeCliBackend
        return ClaudeCliBackend()
    if name == "codex_cli":
        from crustify.agents.backends.codex_cli import CodexCliBackend
        return CodexCliBackend()
    raise ValueError(
        f"Unknown backend {name!r}; expected one of: claude_cli, codex_cli."
    )
