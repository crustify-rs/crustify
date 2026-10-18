"""One planner: decomposes a campaign into subsystems and schedules it.

The orchestrator spawns planners one after another on the campaign branch,
after setup and before the Rust tree is scaffolded. A planner that finds no
plan creates `subsystems.json`, `schedule.json` and the skills' planning
artifacts; one that finds a plan reviews and amends it, filing a report per
edit under `crustify/reviews/planner/`, so the branch history and the
reports record each planning decision and its revisions.
"""
from __future__ import annotations

from crustify.agents.base import (
    CrustifyAgent, SkillSpec, _PKG_ROOT, expand_includes,
)

#: Every skill a planner can carry, in prompt order; discovery decides which
#: it actually carries. Each lives at `prompts/skills/<skill>/planner.md`.
_SKILLS = (
    SkillSpec(
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront/planner.md",
    ),
)


class PlanAgent(CrustifyAgent):
    """Plan one campaign, or review and amend the plan already committed."""

    name = "PlanAgent"
    stage = "plan"
    model = "anthropic/claude-opus-5"
    #: A planner runs for many turns over one procedure; keep it out of
    #: compaction's reach, as for the orchestrator.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def _body(self) -> str:
        return expand_includes((_PKG_ROOT / "prompts" / "planner.md").read_text())
