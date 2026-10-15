"""One review agent for one orchestrator-projected review batch."""
from __future__ import annotations

import json
import re
from pathlib import Path

from crustify.agents.base import (
    CrustifyAgent, SkillSpec, _PKG_ROOT, filter_objectives, objective_keys,
)

#: Every skill a reviewer can carry, in prompt order; discovery decides which
#: it actually carries, exactly as for the translator. A skill's reviewer
#: header may contribute objectives of its own: `lifecycle` comes from
#: wavefront's and `conventions` from the conventions skill's, so a reviewer
#: pointed at a crate that neither describes is never asked for them.
_SKILLS = (
    SkillSpec(
        "crustify", "docs/translate/coding-conventions.md",
        capability="conventions",
        role_header="skills/conventions/reviewer.md",
    ),
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/testing/SKILL.md",
        capability="testing",
        role_header="skills/testing/reviewer.md",
    ),
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/reviewer.md",
    ),
    SkillSpec(
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront/reviewer.md",
    ),
    SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox/reviewer.md",
    ),
)

#: The order objectives are listed in, whichever of them a run carries. One
#: not named here sorts after these, so a skill can add one without touching
#: this module.
OBJECTIVE_ORDER = (
    "lifecycle", "unsafety", "ub", "equiv", "internal", "conventions", "misc",
    "coverage", "fix",
)


#: Objectives that own no section. `fix` decides whether the others patch
#: what they find, which each section states in prose, so it is offered
#: whatever the prompt and skills gate.
_UNGATED = frozenset({"fix"})


def _ordered(keys: set[str]) -> list[str]:
    rank = {key: i for i, key in enumerate(OBJECTIVE_ORDER)}
    return sorted(keys, key=lambda k: (rank.get(k, len(rank)), k))


class ReviewAgent(CrustifyAgent):
    """Review one orchestrator-projected batch for a set of objectives."""

    name = "ReviewAgent"
    model = "anthropic/claude-opus-5"
    #: As for the translator: the body carries this agent's worklist and
    #: objectives, and compaction reaching the procedure costs more than the
    #: cache writes the shared prefix would save.
    prompt_in_system_slot = True
    SKILLS = _SKILLS

    def __init__(
        self,
        workdir: Path,
        *,
        route: str,
        items: list[dict],
        objectives: list[str] | None,
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
        available = set(self.available_objectives())
        if objectives is None:
            self._objectives = frozenset(available)
        else:
            missing = sorted(set(objectives) - available)
            if missing:
                raise SystemExit(
                    "review: objective(s) not offered by this reviewer's prompt "
                    "and skills: " + ", ".join(missing)
                    + "; available: " + ", ".join(_ordered(available)))
            self._objectives = frozenset(objectives)

    @staticmethod
    def _template() -> str:
        return (_PKG_ROOT / "prompts" / "reviewer.md").read_text()

    def available_objectives(self) -> list[str]:
        """Every objective this reviewer can run: ``fix``, those its prompt
        has sections for, and those the role headers of the skills it carries
        have sections for. A skill that is not installed contributes none."""
        keys = set(_UNGATED) | objective_keys(self._template())
        for spec in self.skill_specs():
            if spec.role_header:
                keys |= objective_keys(
                    (_PKG_ROOT / "prompts" / spec.role_header).read_text())
        return _ordered(keys)

    @property
    def objectives(self) -> list[str]:
        return _ordered(set(self._objectives))

    @property
    def stage(self) -> str:  # type: ignore[override]
        """``review-<route>_<key>``, the record ``crustify cost`` buckets as
        ``review-type`` / ``review-symbol`` / ``review-raw-lifetime``, as it
        did when review ran under the translator."""
        key = self._items[0]["name"] if self._items else "batch"
        return (f"review-{self._route}_"
                f"{re.sub(r'[^A-Za-z0-9_]+', '_', key or 'batch')}")

    def _body(self) -> str:
        return filter_objectives(self._template(), self._objectives)

    def _role_guidance(self, text: str) -> str:
        return filter_objectives(text, self._objectives)

    def _arguments(self) -> dict:
        return {
            **super()._arguments(),
            "objectives": ", ".join(self.objectives),
            "worklist": json.dumps({"route": self._route, "items": self._items}),
        }
