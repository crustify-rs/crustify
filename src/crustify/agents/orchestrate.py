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

from crustify.agents.base import CrustifyAgent, SkillSpec, _PKG_ROOT

#: Always on: the orchestrator's own role skill is what makes it an
#: orchestrator, so there is no campaign in which it is not rendered.
_CORE_SKILLS = (
    SkillSpec("crustify", "src/crustify/prompts/skills/orchestrator.md"),
)

#: Selectable through `crustify/skills-config.json`. Both are on by default —
#: an ordinary campaign plans with the oracle and reads the audit surface —
#: but both are things the orchestrator is TOLD about rather than things it
#: is, which is what makes them ablatable.
_CAPABILITY_SKILLS: dict[str, SkillSpec] = {
    #: One wavefront skill, two role overlays. The oracle a translator queries
    #: and the oracle an orchestrator plans with are the same tool used for
    #: different work, so the metadata is shared and only the guidance splits.
    "wavefront": SkillSpec(
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront-orchestrator.md",
    ),
    #: `crustify-audit` was folded into `crustify audit`, so its skill ships
    #: in this package rather than in a checkout of its own.
    "audit": SkillSpec(
        "crustify", "src/crustify_audit/SKILL.md", capability="audit",
    ),
}


class OrchestrateAgent(CrustifyAgent):
    """One campaign orchestrator, for a `translate` or `audit` campaign."""

    name = "orchestrator"
    stage = "orchestrate"
    #: Its artifacts belong to the checkout, not to one oracle target.
    tier = "workdir"
    SKILLS = _CORE_SKILLS
    CAPABILITIES = _CAPABILITY_SKILLS
    DEFAULT_CAPABILITIES = tuple(_CAPABILITY_SKILLS)
    skills_role = "orchestrator"

    def __init__(self, target: Path, *, kind: str, task: Path,
                 model: str, task_only: bool = False, **kwargs) -> None:
        self.kind = kind
        self.task = Path(task)
        self.model = model
        self.task_only = task_only
        self.stage_suffix = kind
        super().__init__(target, **kwargs)

    def _task_text(self) -> str:
        text = self.task.read_text().strip()
        if not text:
            raise SystemExit(f"campaign task is empty: {self.task}")
        return text

    def skill_specs(self) -> tuple[SkillSpec, ...]:
        # `--task-only` is the control arm: the harness contributes nothing,
        # so it contributes no skill index either.
        return () if self.task_only else super().skill_specs()

    def _prompt(self) -> str:
        if self.task_only:
            # The ablation control: the harness contributes nothing, so the
            # task file is the whole prompt and the system slot stays empty.
            return self._task_text().replace("{", "{{").replace("}", "}}")
        if self.kind == "audit":
            return (_PKG_ROOT.parent / "crustify_audit" / "prompts"
                    / "orchestrator.md").read_text()
        return (_PKG_ROOT / "prompts" / "orchestrator.md").read_text()

    def _arguments(self) -> dict:
        return {**super()._arguments(), "campaign_kind": self.kind}

    def system_preamble(self) -> str:
        """Conventions, the skill index, and the campaign task.

        The task joins them because campaign decisions are exactly what a long
        run must not paraphrase: an orchestrator that has compacted away which
        model reviews, or whether a UB pass was authorised, spends a budget on
        the wrong thing and says nothing. Everything here is a document; the
        harness composes, it does not author.
        """
        if self.task_only:
            return ""
        task = self._task_text()
        return "\n\n---\n\n".join((
            super().system_preamble(),
            "## Campaign task\n\n"
            "The decisions below are the campaign's input. An unanswered\n"
            "optional decision takes its documented default. Ask the user\n"
            "about one that is unanswered or genuinely ambiguous; never guess\n"
            "it, and never re-ask one the task already answers.\n\n" + task,
        ))
