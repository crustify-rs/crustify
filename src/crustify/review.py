"""Execute one orchestrator-written review task."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn

from crustify.translate import (RUN_FIELDS, RunSettings, check_fields, parse_branch,
                                parse_run, read_object, task_and_log_dir)

_OBJECTIVE = re.compile(r"^[a-z]+$")

#: Both artifacts a review batch writes, named for the role that wrote them.
_LOG_STEM = "reviewer"


@dataclass(frozen=True)
class ReviewBatch:
    """Validated review-batch input.

    A batch reviews one worklist: in a translate campaign, the ``commits``
    its translation batches landed; in an audit, ``modules`` of the crate,
    each a path or a path with the types, trait impls and functions to
    review in it. It
    may also carry ``reports`` to revisit. ``objectives`` is None when the
    batch names none, which enables every objective the reviewer offers that
    applies to it."""

    route: str
    commits: list[str]
    modules: list[object]
    reports: list[str]
    objectives: list[str] | None
    base_branch: str
    run: RunSettings


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"review: {message}")


_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
_RUST_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$")
#: ``<trait> for <type>``, as the impl header spells them: ``Drop for Repository``,
#: ``From<Oid> for String``, ``Iterator for Revwalk<'_>``.
_TRAIT_IMPL = re.compile(r"^[A-Za-z_][\w:]*(<.+>)? for [A-Za-z_&*(\[].*\S$")


def _path(raw: object, field: str) -> str:
    """One repo-relative path."""
    if not isinstance(raw, str) or not raw:
        _fail(f"{field} must be a non-empty path")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        _fail(f"{field} must be a repo-relative path: {raw}")
    return raw


def _paths(raw: object, field: str) -> list[str]:
    """A non-empty array of distinct repo-relative paths."""
    if not isinstance(raw, list) or not raw:
        _fail(f"{field} must be a non-empty array of paths")
    paths = [_path(p, f"{field}[{i}]") for i, p in enumerate(raw)]
    if len(set(paths)) != len(paths):
        _fail(f"{field} contains duplicates")
    return paths


def _names(raw: object, field: str, name: re.Pattern[str] = _RUST_NAME,
           what: str = "Rust names") -> list[str]:
    if (not isinstance(raw, list) or not raw
            or any(not isinstance(n, str) or not name.fullmatch(n)
                   for n in raw)
            or len(set(raw)) != len(raw)):
        _fail(f"{field} must be a non-empty array of distinct {what}")
    return list(raw)


#: The parts of a module an object entry may name, and how each is spelled.
_PARTS = {
    "types": (_RUST_NAME, "Rust names"),
    "trait_impls": (_TRAIT_IMPL, "`<trait> for <type>` impls"),
    "functions": (_RUST_NAME, "Rust names"),
}


def _modules(raw: object) -> list[object]:
    """Paths, or ``{"path", "types", "trait_impls", "functions"}`` naming
    the part of a module too large to review whole."""
    if not isinstance(raw, list) or not raw:
        _fail("modules must be a non-empty array")
    modules: list[object] = []
    for i, module in enumerate(raw):
        label = f"modules[{i}]"
        if isinstance(module, dict):
            if "path" not in module or not set(module) - {"path"} \
                    or set(module) - {"path", *_PARTS}:
                _fail(f"{label} must be a path, or an object with path and "
                      "one or more of types, trait_impls and functions")
            entry = {"path": _path(module["path"], f"{label}.path")}
            for key, (name, what) in _PARTS.items():
                if key in module:
                    entry[key] = _names(module[key], f"{label}.{key}",
                                        name, what)
            modules.append(entry)
        else:
            modules.append(_path(module, label))
    paths = [m["path"] if isinstance(m, dict) else m for m in modules]
    if len(set(paths)) != len(paths):
        _fail("modules names a path twice")
    return modules


def load_batch(path: Path) -> ReviewBatch:
    """Load and strictly validate a review batch.

    ``objectives`` replaces a translation batch's single ``objective``.
    ``reports`` names the report dirs a ``revisit`` batch re-examines, and is
    given exactly when ``revisit`` is. Which objective names exist depends on
    the skills the reviewer carries, so they are checked against the agent,
    not here."""
    raw = read_object(path, _fail)
    check_fields(raw, {"base_branch"} | RUN_FIELDS,
                 {"commits", "modules", "reports", "objectives"}, _fail)
    if "commits" in raw and "modules" in raw:
        _fail("a batch carries commits or modules, not both")
    if not {"commits", "modules", "reports"} & set(raw):
        _fail("a batch needs commits, modules or reports")
    objectives = raw.get("objectives")
    if objectives is not None:
        if (not isinstance(objectives, list) or not objectives
                or any(not isinstance(o, str) or not _OBJECTIVE.fullmatch(o)
                       for o in objectives)):
            _fail("objectives must be a non-empty array of objective names")
        if len(set(objectives)) != len(objectives):
            _fail("objectives contains duplicates")
        if ("revisit" in objectives) != ("reports" in raw):
            _fail("reports are given exactly when revisit is an objective")
    reports = _paths(raw["reports"], "reports") if "reports" in raw else []
    route, commits, modules = "reports", [], []
    if "commits" in raw:
        commits = raw["commits"]
        if (not isinstance(commits, list) or not commits
                or any(not isinstance(c, str) or not _COMMIT.fullmatch(c)
                       for c in commits)
                or len(set(commits)) != len(commits)):
            _fail("commits must be a non-empty array of distinct commit ids")
        route = "commits"
    elif "modules" in raw:
        route, modules = "modules", _modules(raw["modules"])
    return ReviewBatch(route=route, commits=list(commits), modules=modules,
                       reports=reports, objectives=objectives,
                       base_branch=parse_branch(raw, _fail),
                       run=parse_run(raw, _fail))


def execute(
    workdir: Path,
    task_path: Path,
    *,
    log_dir: Path,
    dry_run: bool = False,
) -> None:
    """Run exactly one reviewer in ``workdir``.

    As for a translator, ``workdir`` is the worktree the orchestrator forked
    for this batch and ``log_dir`` the existing directory its log and usage
    record land in; the harness creates and purges neither.
    """
    task_path, output = task_and_log_dir(task_path, log_dir, _fail)
    batch = load_batch(task_path)
    base_branch = batch.base_branch

    from crustify.agents.review import ReviewAgent

    # Built before the dry-run returns: constructing the agent is what checks
    # the batch's objectives against the skills actually installed.
    agent = ReviewAgent(
        workdir.resolve(),
        route=batch.route,
        commits=batch.commits,
        modules=batch.modules,
        reports=batch.reports,
        objectives=batch.objectives,
        git_base=base_branch,
        artifact_dir=output,
        log_stem=_LOG_STEM,
    )
    if dry_run:
        print(
            f"[review dry-run] one {batch.route} agent; "
            f"{len(batch.commits)} commit(s), {len(batch.modules)} module(s), "
            f"{len(batch.reports)} report(s); objectives "
            f"{', '.join(agent.objectives)}; landing on {base_branch}; "
            f"model {batch.run.model} ({batch.run.billing}); no agent spawned."
        )
        return

    print(f"[crustify spawn-reviewer] workdir: {agent.workdir}")
    print(f"[crustify spawn-reviewer] landing on: {base_branch}")
    print(f"[crustify spawn-reviewer] objectives: {', '.join(agent.objectives)}")
    print(f"[crustify spawn-reviewer] model: {batch.run.model} ({batch.run.billing})")
    print(f"[crustify spawn-reviewer] log: {output / f'{_LOG_STEM}.log'}")
    batch.run.apply()
    agent.run()
    print("[crustify spawn-reviewer] batch completed.")
