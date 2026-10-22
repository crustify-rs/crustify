"""One review agent for one orchestrator-projected review batch."""
from __future__ import annotations

import json
import re
from pathlib import Path

from crustify.agents.base import (
    CrustifyAgent, SkillSpec, _PKG_ROOT, expand_includes,
)

#: Every skill a reviewer can carry, in prompt order; discovery decides which
#: it actually carries, exactly as for the translator. A skill's reviewer
#: header may describe objectives of its own (see `SKILL_OBJECTIVES`).
_SKILLS = (
    SkillSpec(
        "crustify", "src/crustify/prompts/skills/ffimap/SKILL.md",
        capability="ffimap",
        role_header="skills/ffimap/reviewer.md",
    ),
    SkillSpec(
        "wavefront", "README.md", capability="wavefront",
        role_header="skills/wavefront/reviewer.md",
        meta="skills/wavefront/SKILL.md",
    ),
    SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox/reviewer.md",
    ),
)

#: The objectives the reviewer's prompt describes, each under a heading named
#: by its id, in the order they are listed. `fix` has no heading: it decides
#: whether the Fixes step runs. `conventions` applies to a Crustify-generated
#: batch only, which the prompt states. `revisit` applies to a batch that
#: names reports, and only to one.
OBJECTIVES = (
    "unsafety", "contracts", "ub", "equiv", "internal", "conventions", "misc",
    "coverage", "revisit", "disclose", "fix",
)

#: Objectives a skill's reviewer header describes, offered only while that
#: skill is carried: a reviewer pointed at a crate wavefront does not
#: describe is never asked about its lifecycles.
SKILL_OBJECTIVES = {"wavefront": ("lifecycle",)}

#: Listing order: the skills' objectives lead, since they review the
#: analysis every binding was built from.
OBJECTIVE_ORDER = (
    *(o for objectives in SKILL_OBJECTIVES.values() for o in objectives),
    *OBJECTIVES,
)

def _ordered(keys: set[str]) -> list[str]:
    rank = {key: i for i, key in enumerate(OBJECTIVE_ORDER)}
    return sorted(keys, key=rank.__getitem__)


class ReviewAgent(CrustifyAgent):
    """Review one orchestrator-projected batch for a set of objectives."""

    name = "ReviewAgent"
    #: The agent its session record names.
    role = "reviewer"
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
        commits: list[str] = (),
        paths: list[object] = (),
        reports: list[str] = (),
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
        self._commits = list(commits)
        self._paths = [dict(m) if isinstance(m, dict) else m for m in paths]
        self._reports = list(reports)
        available = set(self.available_objectives())
        if objectives is None:
            # Every objective that applies: `revisit` exactly when there are
            # reports to revisit.
            self._objectives = frozenset(
                available - {"revisit"} | ({"revisit"} if reports else set()))
        else:
            missing = sorted(set(objectives) - available)
            if missing:
                raise SystemExit(
                    "review: objective(s) not offered by this reviewer's prompt "
                    "and skills: " + ", ".join(missing)
                    + "; available: " + ", ".join(_ordered(available)))
            self._objectives = frozenset(objectives)

    def available_objectives(self) -> list[str]:
        """Every objective this reviewer can run: those its prompt describes,
        plus those of the skills it carries."""
        keys = set(OBJECTIVES)
        for spec in self.skill_specs():
            keys |= set(SKILL_OBJECTIVES.get(spec.capability or "", ()))
        return _ordered(keys)

    @property
    def objectives(self) -> list[str]:
        return _ordered(set(self._objectives))

    @property
    def stage(self) -> str:  # type: ignore[override]
        """``review-<route>_<key>``: the name of a log stem when the harness
        gives none."""
        if self._commits:
            key = self._commits[0][:12]
        elif self._paths:
            first = self._paths[0]
            key = first["path"] if isinstance(first, dict) else first
        else:
            key = "batch"
        return (f"review-{self._route}_"
                f"{re.sub(r'[^A-Za-z0-9_]+', '_', key)}")

    def _body(self) -> str:
        return expand_includes(
            (_PKG_ROOT / "prompts" / "reviewer.md").read_text())

    def _arguments(self) -> dict:
        return {
            **super()._arguments(),
            "objectives": ", ".join(self.objectives),
            "worklist": json.dumps(
                {"route": self._route, "paths": self._paths}
                if self._paths else
                {"route": self._route, "commits": self._commits}),
            "reports": ", ".join(self._reports) or "none",
        }
