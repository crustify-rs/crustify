"""One planner: decomposes a campaign into subsystems and schedules it.

The orchestrator spawns planners one after another on the campaign branch,
after setup and before the Rust tree is scaffolded, each with one objective
(`crustify.plan.OBJECTIVES`). An `emit` run creates the plan --
`subsystems.json`, each subsystem's `schedule.json` and the skills' planning artifacts -- or
adds what an existing plan lacks, and leaves its judgements alone; a
`review` run assesses those judgements, amends them and files a report per
edit under `crustify/reviews/planner/`. The branch history and the reports
record each planning decision and its revisions.
"""
from __future__ import annotations

from pathlib import Path

from crustify.agents.base import (
    CrustifyAgent, SkillSpec, _PKG_ROOT, expand_includes,
)

#: Every skill a planner can carry, in prompt order; discovery decides which
#: it actually carries. Each lives at `prompts/skills/<skill>/planner.md`.
_SKILLS = (
    SkillSpec(
        "wavefront", "README.md", capability="wavefront",
        role_header="skills/wavefront/planner.md",
        meta="skills/wavefront/SKILL.md",
    ),
)


class PlanAgent(CrustifyAgent):
    """Plan one campaign for one objective: `emit` or `review`."""

    name = "PlanAgent"
    #: The agent its session record names.
    role = "planner"
    model = "anthropic/claude-opus-5"
    #: A planner runs for many turns over one procedure; keep it out of
    #: compaction's reach, as for the orchestrator.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def __init__(self, workdir: Path, *, objective: str, **kwargs) -> None:
        from crustify.plan import OBJECTIVES
        if objective not in OBJECTIVES:
            raise SystemExit(f"plan: objective must be one of "
                             f"{', '.join(OBJECTIVES)}, not {objective!r}")
        self.objective = objective
        super().__init__(workdir, **kwargs)

    @property
    def stage(self) -> str:  # type: ignore[override]
        """``plan-emit`` or ``plan-review``."""
        return f"plan-{self.objective}"

    def _body(self) -> str:
        return expand_includes((_PKG_ROOT / "prompts" / "planner.md").read_text())

    def _arguments(self) -> dict:
        return {**super()._arguments(), "objective": self.objective}
