"""One translation agent for one orchestrator-projected thin batch."""
from __future__ import annotations

import json
import re
from pathlib import Path

from crustify.agents.base import CrustifyAgent, SkillSpec, _PKG_ROOT

_CORE_SKILLS = (
    SkillSpec("crustify", "src/crustify/prompts/skills/translator.md"),
)

_CAPABILITY_SKILLS: dict[str, SkillSpec] = {
    "wavefront": SkillSpec(
        "wavefront", "SKILL.md", capability="wavefront",
        role_header="skills/wavefront.md",
    ),
    "ffibox": SkillSpec(
        "ffibox", "SKILL.md", capability="ffibox",
        role_header="skills/ffibox.md",
    ),
    "crustify-audit": SkillSpec(
        "crustify-audit", "SKILL.md", capability="crustify-audit",
        role_header="skills/audit.md",
    ),
}


class TranslateAgent(CrustifyAgent):
    """Translate or review one orchestrator-projected batch."""

    name = "TranslateAgent"
    model = "anthropic/claude-opus-5"
    output = None  # scheduler gates via the per-item todo; agent runs when called.

    def __init__(
        self,
        target: Path,
        *,
        route: str,
        items: list[dict],
        objective: str,
        campaign_objective: str,
        prompt_capabilities: tuple[str, ...] | None = None,
        workdir: Path,
        git_base: str,
        log_dir: Path,
        log_stem: str,
    ) -> None:
        super().__init__(
            target, workdir=workdir, git_base=git_base,
            log_dir=log_dir, log_stem=log_stem,
        )
        self._route = route
        self._items = [dict(item) for item in items]
        self._objective = objective
        self._campaign_objective = campaign_objective
        self._prompt_capabilities = (
            tuple(prompt_capabilities) if prompt_capabilities is not None
            else self.configured_capabilities(self.layout)
        )

    @staticmethod
    def configured_capabilities(layout) -> tuple[str, ...]:
        """Read the translator's prompt-only capability set once."""
        p = layout.repo_config
        cfg = json.loads(p.read_text()) if p.exists() else {}
        block = cfg.get("prompt_capabilities") or {}
        names = block.get("translator") or []
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise SystemExit(
                "cli-config.json: prompt_capabilities.translator must be a list of names")
        unknown = sorted(set(names) - set(_CAPABILITY_SKILLS))
        if unknown:
            raise SystemExit(
                "cli-config.json: unknown translator prompt capability: "
                + ", ".join(unknown))
        # Preserve authored order in the prompt; collapse accidental repeats.
        return tuple(dict.fromkeys(names))

    def skill_specs(self) -> tuple[SkillSpec, ...]:
        return _CORE_SKILLS + tuple(
            _CAPABILITY_SKILLS[name] for name in self._prompt_capabilities
        )

    @property
    def stage(self) -> str:  # type: ignore[override]
        """The per-agent log stem: ``<objective>-<kind>_<key>``, e.g.
        ``port-type_git_delta_index`` / ``wrap-symbol_access``.

        This fallback is used outside the batch harness; normal translation
        logs use the harness-generated batch id."""
        key = self._items[0]["name"] if self._items else "batch"
        unit = self._route
        return (f"{self._objective}-{unit}_"
                f"{re.sub(r'[^A-Za-z0-9_]+', '_', key or 'batch')}")

    def _prompt(self) -> str:
        return (_PKG_ROOT / "prompts" / "translator.md").read_text()

    def _wavefront_config(self) -> str:
        """Return the campaign-wide config translators use for oracle queries."""
        try:
            doc = json.loads(self.layout.subsystems_json.read_text())
        except (OSError, ValueError):
            doc = {}
        configured = doc.get("oracle_config")
        if isinstance(configured, dict):
            configured = configured.get("path")
        if isinstance(configured, str) and configured:
            return configured
        legacy = doc.get("oracle_target")
        if isinstance(legacy, str) and legacy:
            return str(Path("crustify/wavefront/targets") / legacy
                       / "wavefront-config.json")
        return "crustify/wavefront/wavefront-config.json"

    def _arguments(self) -> dict:
        common = {
            # Base first: `target`, `workdir`, and `git_base` (the wave's
            # integration branch). Building this dict from scratch silently dropped
            # every key the base adds — a template naming one dies with KeyError
            # before the agent issues a request.
            **super()._arguments(),
            "task_objective": self._objective,
            "workspace_root": str(self.layout.rust),
            "build_json":     str(self.layout.build_json),
            "wavefront_config": self._wavefront_config(),
            # NOTE: no `conventions` key. The conventions doc and skill index are
            # no longer a `.format` slot — they go to the backend's system slot
            # via `system_preamble()`, out of reach of context compaction.
        }
        common["campaign_objective"] = self._campaign_objective

        common["worklist"] = json.dumps(
            {"route": self._route, "items": self._items})
        return common
