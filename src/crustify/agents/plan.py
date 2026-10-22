"""One planner: decomposes a campaign into modules and schedules it.

The orchestrator spawns planners one after another, each on its own branch,
after setup and before the Rust tree is scaffolded. Every run does the same:
it emits what the plan -- `modules.json`, the waves of `schedule.json`
and the skills' planning artifacts -- lacks, updates what
follows an earlier schema, corrects what earlier runs decided, filing a
report per correction under `crustify/reviews/planner/`, and re-plans the
`todo` waves its changes move. The branch history and the reports record each
planning decision and its revisions.
"""
from __future__ import annotations

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
    """Plan one campaign, or bring its committed plan up to date."""

    name = "PlanAgent"
    #: The agent its session record names.
    role = "planner"
    #: Every run does the same, so one stage names them all.
    stage = "plan"
    model = "anthropic/claude-opus-5"
    #: A planner runs for many turns over one procedure; keep it out of
    #: compaction's reach, as for the orchestrator.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def _body(self) -> str:
        return expand_includes((_PKG_ROOT / "prompts" / "planner.md").read_text())
