"""One planner: decomposes a campaign into subsystems and schedules it.

The orchestrator spawns planners one after another on the campaign branch,
after setup and before the Rust tree is scaffolded. The first run creates
`subsystems.json`, `schedule.json` and the skills' planning artifacts; every
later run reviews what the previous one committed and amends it, so the
branch history is the record of each planning decision and its revisions.
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
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront/planner.md",
    ),
)


class PlanAgent(CrustifyAgent):
    """Plan one campaign: run ``run`` of ``runs``."""

    name = "PlanAgent"
    stage = "plan"
    model = "anthropic/claude-opus-5"
    #: A planner runs for many turns over one procedure; keep it out of
    #: compaction's reach, as for the orchestrator.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def __init__(self, workdir: Path, *, run: int, runs: int, **kwargs) -> None:
        if not 1 <= run <= runs:
            raise SystemExit(f"planner run {run} is not within 1..{runs}")
        self.run_index = run
        self.runs = runs
        super().__init__(workdir, **kwargs)

    def _body(self) -> str:
        return expand_includes((_PKG_ROOT / "prompts" / "planner.md").read_text())

    def _arguments(self) -> dict:
        return {**super()._arguments(), "run": self.run_index, "runs": self.runs}
