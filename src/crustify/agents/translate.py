"""One translation agent for one orchestrator-projected thin batch."""
from __future__ import annotations

import json
import re
from pathlib import Path

from crustify.agents.base import CrustifyAgent, SkillSpec, _PKG_ROOT

#: Every skill a translator can carry, in prompt order. Which of them it
#: actually carries is decided by discovery: a skill whose files are on disk
#: is rendered, one whose files are not is silently absent. Each lives at
#: `prompts/skills/<skill>/translator.md` — one directory per skill, one file
#: per role — so deleting the file ablates it here and deleting the
#: directory ablates it everywhere. There is no role skill: it existed to
#: route the translator to its playbook, and the playbook is now this agent's
#: prompt.
#:
#: Nothing crustify ships is here either. `crustify audit` is on the agent's
#: PATH and in its `--help` whatever the index says, so a role header for it
#: could only ablate the instructions and never the tool -- which is not an
#: ablation. Its guidance lives in the prompt with the rest of the workflow.
_SKILLS = (
    SkillSpec(
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront/translator.md",
    ),
    SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox/translator.md",
    ),
)


class TranslateAgent(CrustifyAgent):
    """Translate or review one orchestrator-projected batch."""

    name = "TranslateAgent"
    model = "anthropic/claude-opus-5"
    #: The body carries this agent's worklist, so each translator of a wave
    #: gets its own system prefix rather than the shared one. Chosen
    #: deliberately: compaction reaching the procedure costs more than the
    #: cache writes it gives up.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def __init__(
        self,
        workdir: Path,
        *,
        route: str,
        items: list[dict],
        objective: str,
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
        self._objective = objective

    @property
    def stage(self) -> str:  # type: ignore[override]
        """The stage recorded in this agent's usage record:
        ``<objective>-<route>_<key>``, e.g. ``port-type_git_delta_index`` /
        ``wrap-symbol_access``. ``crustify ... cost`` buckets by its prefix.

        The log file itself takes the harness's fixed stem, ``translator``."""
        key = self._items[0]["name"] if self._items else "batch"
        unit = self._route
        return (f"{self._objective}-{unit}_"
                f"{re.sub(r'[^A-Za-z0-9_]+', '_', key or 'batch')}")

    def _body(self) -> str:
        return (_PKG_ROOT / "prompts" / "translator.md").read_text()

    def _arguments(self) -> dict:
        common = {
            # Base first: `workdir` and `git_base` (the wave's
            # integration branch). Building this dict from scratch silently dropped
            # every key the base adds — a template naming one dies with KeyError
            # before the agent issues a request.
            **super()._arguments(),
            "task_objective": self._objective,
            # No `artifact_dir`: the batch directory holds only the log and
            # usage record the harness writes. A reviewer files its reports in
            # its worktree, under a path derived from its branch.
            # NOTE: no `conventions` key. The conventions doc and skill index are
            # no longer a `.format` slot — they go to the backend's system slot
            # via `system_preamble()`, out of reach of context compaction.
        }
        common["worklist"] = json.dumps(
            {"route": self._route, "items": self._items})
        return common
