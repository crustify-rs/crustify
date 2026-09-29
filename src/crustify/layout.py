"""Artifact layout for the translation executor."""
from __future__ import annotations

from pathlib import Path

CRUSTIFY = "crustify"


class Layout:
    """Resolves every crustify artifact path from one ``crustify/`` root."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = Path(workdir).resolve()
        self.root = self.workdir / CRUSTIFY

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
