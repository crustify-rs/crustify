"""Artifact layout for the translation executor."""
from __future__ import annotations

import os
from pathlib import Path

CRUSTIFY = "crustify"

_REPO_ROOT: Path | None = None  # pinned once by the CLI; never marker-walked


def set_workdir(workdir: Path) -> None:
    """Pin the repo root explicitly — the CLI's first positional. Once set,
    :meth:`Layout.discover` returns it directly: crustify never walks the
    filesystem looking for a ``crustify/`` marker."""
    global _REPO_ROOT
    _REPO_ROOT = Path(workdir).resolve()


def find_workdir(start: Path) -> Path:
    """The pinned repo root (:func:`set_workdir`). With nothing pinned —
    e.g. a direct library/test caller — ``start`` itself is taken as the repo
    root. **Never** walks ancestors; the repo root is an explicit input."""
    if _REPO_ROOT is not None:
        return _REPO_ROOT
    return Path(start).resolve()


class Layout:
    """Resolves every crustify artifact path from one ``crustify/`` root."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = Path(workdir).resolve()
        self.root = self.workdir / CRUSTIFY

    @classmethod
    def discover(cls, start: Path) -> "Layout":
        return cls(find_workdir(start))

    # ----------------------------------------------------- repo-tier (shared)
    @property
    def build_json(self) -> Path:
        return self.root / "build.json"

    @property
    def subsystems_json(self) -> Path:
        return self.root / "subsystems.json"

    @property
    def rust(self) -> Path:
        return self.root / "rust"

    @property
    def skills_config(self) -> Path:
        """Which optional skills each agent role carries in its system prompt.

        Tracked, like `build.json` and `subsystems.json`, and for the same
        reason: it decides what a wave's agents were told, so the commits a
        wave lands must carry it. See :mod:`crustify.skills_config`."""
        return self.root / "skills-config.json"

    def providers(self, cli: str) -> Path:
        """Config home crustify hands a provider CLI (``claude`` / ``codex``),
        so a run reads crustify's settings rather than the operator's.

        Not a full sandbox: claude keeps session transcripts in the real
        ``~/.claude/projects/`` regardless of ``ANTHROPIC_CONFIG_DIR``, and
        codex resolves auth from ``CODEX_HOME`` — so pointing that at a
        crustify path loses a ChatGPT-subscription login (an OpenRouter
        ``env_key`` needs no auth file and is unaffected)."""
        d = self.root / ".providers" / cli
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------- target identity
    def rel_target(self, target: Path) -> str:
        t = Path(target).resolve()
        if t == self.workdir:
            return "."
        return t.relative_to(self.workdir).as_posix()

    @property
    def campaigns(self) -> Path:
        """Root of all target-scoped campaign artifacts."""
        return self.root / "campaigns"

    def campaign_dir(self, target: Path) -> Path:
        """Tracked wave plans and logs for one explicit oracle target."""
        return self.campaigns / self.rel_target(target)

    def logs(self, target: Path) -> Path:
        return self.campaign_dir(target) / "logs"
