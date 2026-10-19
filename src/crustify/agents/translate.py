"""One translator: ports one orchestrator-projected thin batch."""
from __future__ import annotations

from crustify.agents.base import SkillSpec
from crustify.agents.worklist import WorklistAgent

#: Every skill a translator can carry, in prompt order. Which of them it
#: actually carries is decided by discovery: a skill whose files are on disk
#: is rendered, one whose files are not is silently absent. Each lives at
#: `prompts/skills/<skill>/translator.md` — one directory per skill, one file
#: per role — so deleting the file ablates it here and deleting the
#: directory ablates it everywhere. There is no role skill: it existed to
#: route the translator to its playbook, and the playbook is now this agent's
#: prompt.
#:
#: Skills are for the external tools a translator reaches for on demand.
#: crustify's own documents -- the coding conventions and the how-tos -- are
#: not skills: the prompt includes them whole.
_SKILLS = (
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/translator.md",
    ),
    SkillSpec(
        "wavefront", "README.md", capability="wavefront",
        role_header="skills/wavefront/translator.md",
        meta="skills/wavefront/SKILL.md",
    ),
    SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox/translator.md",
    ),
)


class TranslateAgent(WorklistAgent):
    """Port one orchestrator-projected batch to safe Rust."""

    name = "TranslateAgent"
    objective = "port"
    prompt = "translator.md"
    SKILLS = _SKILLS
