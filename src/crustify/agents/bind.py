"""One binder: binds the items of one orchestrator-written task."""
from __future__ import annotations

from crustify.agents.base import SkillSpec
from crustify.agents.worklist import WorklistAgent

#: Every skill a binder can carry, in prompt order; discovery decides which it
#: actually carries, as for the translator. Each lives at
#: `prompts/skills/<skill>/binder.md`.
_SKILLS = (
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/binder.md",
    ),
    SkillSpec(
        "wavefront", "README.md", capability="wavefront",
        role_header="skills/wavefront/binder.md",
        meta="skills/wavefront/SKILL.md",
    ),
    SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox/binder.md",
    ),
)


class BindAgent(WorklistAgent):
    """Bind one orchestrator-projected batch: keep its C implementation and
    put a safe Rust API in front of it."""

    name = "BindAgent"
    #: The agent its session record names.
    role = "binder"
    objective = "wrap"
    prompt = "binder.md"
    SKILLS = _SKILLS
