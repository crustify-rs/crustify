"""Paths for one audit, as a narrowing of the shared crustify layout.

The subject is a repository, not a bare cargo workspace, because a wrapper is
not auditable without the thing it wraps: `ub` requires a reproduction that
links the audited crate, which for an FFI wrapper means building the C library,
whose sources are in the repo — beside the Rust, not inside it.

This used to be a second, independent ``Layout``. It resolved the same
``crustify/`` root and carried its own copy of ``providers()``, which is how
two implementations of one path convention drift. It is now a subclass that
moves ``root`` one level down and adds the artifacts only an audit has, so the
provider-home rule, the workdir resolution and everything else stay
single-sourced.
"""
from __future__ import annotations

from pathlib import Path

from crustify.layout import Layout as _Layout

#: Under `crustify/`, not beside it: auditing a campaign target should put the
#: audit next to the campaign. In its OWN subdirectory, because a target that
#: has been through crustify already has `codeql/`, `rust/`, `crates.json`
#: and the rest at that level, and interleaving two tools' artifacts in one
#: listing makes neither readable — and leaves the next name either side adds
#: free to collide.
ARTIFACT_DIR = "crustify/audit"


class Layout(_Layout):
    """Audit artifacts, rooted at ``<workdir>/crustify/audit``.

    ``root`` is the audit directory, so the inherited ``providers()`` keeps
    giving an audit its own mode-local provider home rather than sharing the
    campaign's — the behaviour the standalone class had, now inherited instead
    of restated.
    """

    def __init__(self, repo: Path) -> None:
        super().__init__(repo)
        self.root = self.workdir / ARTIFACT_DIR

    @property
    def repo(self) -> Path:
        """The audited checkout. ``workdir`` under the shared name."""
        return self.workdir

    @property
    def workspace(self) -> Path:
        """Cargo workspace used by the deterministic scanner.

        Ordinary Rust repositories are scanned at their root. Crustify
        campaigns keep the generated workspace at ``crustify/rust`` while the
        command still receives the repository root so audit artifacts land
        beside campaign state. Unknown layouts stay rooted at the supplied
        repository and fail with Cargo's useful metadata error.
        """
        if (self.workdir / "Cargo.toml").is_file():
            return self.workdir
        campaign = self.workdir / "crustify" / "rust"
        if (campaign / "Cargo.toml").is_file():
            return campaign
        return self.workdir

    # ---- `unsafe`: the deterministic half
    @property
    def scan(self) -> Path:
        """The deterministic pass's output: the unsafe metrics. Reproducible."""
        return self.root / "unsafe.json"

    # ---- `ub`: the agentic half
    @property
    def advisories(self) -> Path:
        """Confirmed bugs and their reproducers."""
        return self.root / "advisories"

    @property
    def leads(self) -> Path:
        """Every investigated candidate, including the cleared ones."""
        return self.root / "leads"

    @property
    def scratch(self) -> Path:
        """Disposable experiments."""
        return self.root / "scratch"

    @property
    def logs(self) -> Path:
        """Agent logs and usage records for this audit."""
        return self.root / "logs"
