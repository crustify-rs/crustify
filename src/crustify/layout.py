"""Artifact layout for the translation executor."""
from __future__ import annotations

from pathlib import Path

CRUSTIFY = "crustify"


def crustify_home() -> Path:
    """Crustify's own home, shared by every campaign of this user:
    ``$CRUSTIFY_HOME``, or ``~/.crustify``."""
    import os
    return Path(os.environ.get("CRUSTIFY_HOME") or Path.home() / ".crustify")


class Layout:
    """Resolves every crustify artifact path from one ``crustify/`` root."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = Path(workdir).resolve()
        self.root = self.workdir / CRUSTIFY

    def providers(self, cli: str) -> Path:
        """Config home crustify hands a provider CLI under API-key billing,
        under crustify's own home rather than the checkout: codex's
        ``CODEX_HOME`` and claude's ``CLAUDE_CONFIG_DIR``. Holding no
        subscription login, it leaves the API key the CLI's only credential,
        and its session files stay out of the repository and its worktrees."""
        d = crustify_home() / "providers" / cli
        d.mkdir(parents=True, exist_ok=True)
        return d
