"""Git-worktree isolation for one-agent translation batch invocations.

The orchestrator creates one unchecked-out integration branch per wave and
passes it to every batch harness. Each harness creates exactly one child branch
and worktree from that ref. The translator commits there, atomically pushes to
the integration branch, rebases and retries a rejected fast-forward, then
prunes its own successful worktree. Failed worktrees remain inspectable.

The integration branch must not be checked out: Git rejects pushes to a checked
out branch, and update-in-place modes are unsafe under concurrent landings.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import NamedTuple

_WT_DIR = "crustify/.worktrees"   # gitignored; failed batch worktrees survive here


def _git(repo: Path, *args: str, check: bool = True) -> str:
    """Run a git command in ``repo`` and return stdout (stripped)."""
    r = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
    )
    if check and r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({r.returncode}): {r.stderr.strip()[:400]}")
    return r.stdout.strip()


class BatchWorktree(NamedTuple):
    path: Path
    branch: str
    base_commit: str


def validate_base_branch(repo: Path, base_branch: str) -> str:
    """Return the tip of an existing, unchecked-out local base branch."""
    base_branch = base_branch.removeprefix("refs/heads/")
    if not base_branch:
        raise RuntimeError("base branch must not be empty")
    base_ref = f"refs/heads/{base_branch}"
    base_commit = _git(repo, "rev-parse", "--verify", base_ref, check=False)
    if not base_commit:
        raise RuntimeError(f"base branch does not exist: {base_branch}")
    checked_out = {
        line.removeprefix("branch refs/heads/")
        for line in _git(repo, "worktree", "list", "--porcelain").splitlines()
        if line.startswith("branch refs/heads/")
    }
    if base_branch in checked_out:
        raise RuntimeError(f"base branch is checked out: {base_branch}")
    return base_commit


def add_batch_worktree(repo: Path, base_branch: str, batch_id: str) -> BatchWorktree:
    """Fork one uniquely named batch worktree from an unchecked-out branch."""
    base_branch = base_branch.removeprefix("refs/heads/")
    base_ref = f"refs/heads/{base_branch}"
    validate_base_branch(repo, base_branch)

    branch = f"crustify/batch/{batch_id}"
    wt = repo / _WT_DIR / batch_id
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "--quiet", "-b", branch, str(wt), base_ref)
    # The integration branch may advance while concurrent harnesses are
    # starting. Record the commit this worktree actually forked, not the tip
    # observed by the read-only preflight just before `worktree add`.
    base_commit = _git(wt, "rev-parse", "HEAD")
    return BatchWorktree(wt, branch, base_commit)


#: Derived, read-only-across-a-wave artifacts symlinked into each worktree.
#: A TRACKED artifact must not be here: git checks it out from HEAD, so the
#: worktree already holds its own copy, and sharing a written one would send
#: every agent's writes into the same file. `ownership-store.json` is tracked
#: for that reason — an agent submits through `query --update` into its own
#: copy and its landing commit carries the findings, the route its Rust output
#: already takes.
_SHARED = (".providers", "wavefront", "campaigns", "tmp", "cli-config.json")

#: Shared entries created ON DEMAND rather than by an earlier stage, so the
#: main checkout may not hold them yet when the first wave starts. They are
#: seeded there before linking (see :func:`link_shared`); everything else in
#: `_SHARED` is produced by a prior stage and its absence is a real error.
_SHARED_LAZY_DIRS = (".providers", "tmp")


def link_shared(wt: Path, repo: Path) -> None:
    """Symlink the gitignored, read-only-across-a-wave crustify artifacts from
    the main checkout into the worktree, so the worktree is a *complete*
    functional crustify tree. Wavefront extraction/cache data and campaign logs
    resolve to the shared copy without being duplicated. Tracked Wavefront configs,
    schedule documents, and ownership-store entries already present in the worktree
    win over the recursive links.

    `build.json`, `subsystems.json`, and `crates.json` are deliberately NOT
    here. All three are tracked
    (see `specs/gitignore`), so `git worktree add` checks each one out from HEAD
    and the worktree already holds its own copy — which is the rule stated on
    `_SHARED` above. They are still read-only across a wave: `build.json` and
    `subsystems.json` are written before any wave, and the orchestrator fully
    populates `crates.json` for a wave's units before it starts, so agents only
    ever READ them. A
    genuine miss-fill therefore surfaces as a per-worktree edit that its landing
    commit carries, not as a write racing into the shared main copy.

    ``.providers`` must be here for a subtle reason: the agent backends resolve
    the provider CLI's config home as ``Layout(repo_root).providers(cli)``, and an
    isolated agent's ``repo_root`` IS its worktree — while ``Layout.providers``
    **mkdirs** the path. Unlinked, every worktree therefore gets a freshly created
    EMPTY provider config instead of crustify's shared one, and the CLI runs
    against it with no error: a silent loss of provider settings, which is the
    worst available failure mode.

    ``cli-config.json`` is the one shared FILE, and it is here because it is the
    inverse of the two above: hand-authored, machine-local (absolute paths to the
    crustify, wavefront, ffibox and audit checkouts, and to their binaries), and
    therefore gitignored — so HEAD cannot carry it into a worktree. Without the
    symlink an agent's ``Layout.repo_config`` resolves to a file that is not
    there, every skill path fails to resolve, and the whole set silently
    disappears from its system prompt as the literal "(no skills configured)"
    beside conventions.md."""
    for d in _SHARED:
        src = repo / "crustify" / d
        dst = wt / "crustify" / d
        # A lazily-created shared dir must be MATERIALIZED in the main checkout
        # before the link, not skipped for not existing yet. `.providers` is
        # created on demand by `Layout.providers()` (which mkdirs), so on the
        # first wave in a fresh tree it is absent here — the `src.exists()`
        # guard below then skips it, `Layout.providers()` mkdirs a REAL dir
        # inside the worktree, and the purge takes it with the worktree. That is
        # exactly the silent failure this docstring warns about, plus a worse
        # one: codex's session rollout lands in CODEX_HOME, so the run's cost
        # accounting is destroyed with the worktree ("no session rollout found;
        # this run is unaccounted"). Only dirs are seeded — the one shared FILE
        # (cli-config.json) must stay skipped when absent, since an empty
        # stand-in for it is worse than none.
        if not src.exists() and d in _SHARED_LAZY_DIRS:
            src.mkdir(parents=True, exist_ok=True)
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            _link_into(src, dst)


def _link_into(src: Path, dst: Path) -> None:
    """Symlink ``src`` at ``dst``, or — when ``dst`` already exists as a real
    directory — link ``src``'s missing children into it, recursively.

    The plain case is a whole shared dir that the worktree does not have. The
    recursive case exists because a shared dir may be PARTIALLY materialized by
    the checkout: tracked Wavefront configs, ownership findings, and wave plans
    coexist with gitignored extraction caches and logs. Existing tracked files
    win while missing derived children are linked.

    A destination that already exists as a symlink or file is left alone: it is
    either a previous link or a tracked artifact that must win."""
    if not dst.exists():
        dst.symlink_to(src.resolve())
        return
    if dst.is_symlink() or not (dst.is_dir() and src.is_dir()):
        return
    for child in src.iterdir():
        _link_into(child, dst / child.name)
