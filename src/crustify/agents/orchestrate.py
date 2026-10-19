"""The campaign orchestrator, run as an ordinary crustify agent.

It used to be started by shell: the container cat'd a prompt, appended a task
and some context, and exec'd `claude` or `codex` directly. That path had no
system slot at all -- every word the longest-lived agent in a campaign was
given sat in `messages`, where compaction can paraphrase it away -- and it
wrote no `usage.json`, so the supervision cost of every campaign to date is
unrecorded. Routing it through the same backend as every other agent fixes
both, and deletes the second implementation of model routing that lived in
that shell.
"""
from __future__ import annotations

from pathlib import Path

from crustify.agents.base import (
    CrustifyAgent, SkillSpec, _PKG_ROOT, expand_includes,
)

#: Every skill an orchestrator can carry, per campaign kind, in prompt order.
#: Which of them it actually carries is decided by discovery: a skill whose
#: files are on disk is rendered, one whose files are not is silently absent.
#: Each lives at `prompts/skills/<skill>/<kind>-orchestrator.md`, named like
#: the kind's prompt — one directory per skill, one file per role — so
#: deleting the file ablates it for that kind and deleting the directory
#: ablates it everywhere.
#:
#: The coding conventions are not a skill: the prompt includes them whole.
TRANSLATE_SKILLS = (
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/translate-orchestrator.md",
    ),
    #: One wavefront skill, two role overlays. The oracle a translator queries
    #: and the oracle an orchestrator plans with are the same tool used for
    #: different work, so the metadata is shared and only the guidance splits.
    SkillSpec(
        "wavefront", "README.md", capability="wavefront",
        role_header="skills/wavefront/translate-orchestrator.md",
        meta="skills/wavefront/SKILL.md",
    ),
)

#: An audit plans from the crate's unsafe surface, which is ffimap's; it has
#: no C decomposition to plan, so it carries no wavefront.
AUDIT_SKILLS = (
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/audit-orchestrator.md",
    ),
)

SKILLS_BY_KIND = {"translate": TRANSLATE_SKILLS, "audit": AUDIT_SKILLS}


class OrchestrateAgent(CrustifyAgent):
    """One campaign orchestrator, for a `translate` or `audit` campaign."""

    name = "orchestrator"
    stage = "orchestrate"
    prompt_in_system_slot = True
    SKILLS = TRANSLATE_SKILLS

    def __init__(self, workdir: Path, *, kind: str, task: Path,
                 model: str, task_only: bool = False,
                 interactive: bool = False,
                 **kwargs) -> None:
        self.kind = kind
        self.SKILLS = SKILLS_BY_KIND[kind]
        self.task = Path(task)
        self.model = model
        self.task_only = task_only
        #: The orchestrator presents a brief and waits at approval gates, so
        #: with a person at the terminal it runs in the CLI's own interface.
        self.interactive = interactive
        self.stage_suffix = kind
        super().__init__(workdir, **kwargs)

    def _task_text(self) -> str:
        text = self.task.read_text().strip()
        if not text:
            raise SystemExit(f"campaign settings file is empty: {self.task}")
        return text

    def skill_specs(self) -> tuple[SkillSpec, ...]:
        # `--task-only` is the control arm: the harness contributes nothing,
        # so it contributes no skill index either.
        return () if self.task_only else super().skill_specs()

    def _body(self) -> str:
        """The stage prompt. The campaign settings are not in it: the prompt says
        where the task lives, and the orchestrator reads it from there, so an
        edit made mid-campaign is what the next subsystem runs under."""
        self._task_text()
        return expand_includes(
            (_PKG_ROOT / "prompts" / f"{self.kind}-orchestrator.md").read_text())

    def _prompt(self) -> str:
        if self.task_only:
            # The ablation control: the harness contributes nothing, so the
            # task file is the whole prompt and the system slot stays empty.
            return self._task_text().replace("{", "{{").replace("}", "}}")
        return super()._prompt()

    def system_preamble(self) -> str:
        """Empty for the ablation arm, the base composition otherwise.

        The base puts this agent's whole body in the system slot, because
        `prompt_in_system_slot` is set: the orchestrator is one agent running
        for hundreds of turns, and what compaction would paraphrase away is
        its own procedure. The campaign's decisions are not here: they live
        in the task file, which the procedure tells it to reread.
        """
        return "" if self.task_only else super().system_preamble()
