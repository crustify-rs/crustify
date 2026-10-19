"""The base of the agents that work one orchestrator-projected worklist."""
from __future__ import annotations

import json
import re
from pathlib import Path

from crustify.agents.base import CrustifyAgent, _PKG_ROOT, expand_includes


class WorklistAgent(CrustifyAgent):
    """One agent over one thin batch: its route and items, landing on a wave
    integration branch. A subclass names its objective and its prompt."""

    model = "anthropic/claude-opus-5"
    #: The body carries this agent's worklist, so each agent of a wave gets
    #: its own system prefix rather than the shared one. Chosen deliberately:
    #: compaction reaching the procedure costs more than the cache writes it
    #: gives up.
    prompt_in_system_slot = True
    #: `wrap` or `port`: what the usage record's stage leads with.
    objective: str
    #: The stage prompt under `prompts/`.
    prompt: str

    def __init__(
        self,
        workdir: Path,
        *,
        route: str,
        items: list[dict],
        git_base: str,
        artifact_dir: Path,
        log_stem: str,
    ) -> None:
        super().__init__(
            workdir, git_base=git_base, artifact_dir=artifact_dir,
            log_stem=log_stem,
        )
        self._route = route
        self._items = [dict(item) for item in items]

    @property
    def stage(self) -> str:  # type: ignore[override]
        """This agent's stage, ``<objective>-<route>_<key>``, e.g.
        ``port-type_git_delta_index`` / ``wrap-symbol_access``: the name of a
        log stem when the harness gives none. Its session record names the
        agent, the role."""
        key = self._items[0]["name"] if self._items else "batch"
        return (f"{self.objective}-{self._route}_"
                f"{re.sub(r'[^A-Za-z0-9_]+', '_', key or 'batch')}")

    def _body(self) -> str:
        return expand_includes((_PKG_ROOT / "prompts" / self.prompt).read_text())

    def _arguments(self) -> dict:
        # Base first: `workdir` and `git_base` (the wave's integration
        # branch). Building this dict from scratch silently dropped every key
        # the base adds — a template naming one dies with KeyError before the
        # agent issues a request.
        return {
            **super()._arguments(),
            "worklist": json.dumps({"route": self._route, "items": self._items}),
        }
