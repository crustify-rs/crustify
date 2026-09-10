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

from typing import Protocol, runtime_checkable

from pathlib import Path

from crustify.core.agentlog import AgentLog
from crustify.core.models import Route


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
