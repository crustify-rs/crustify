"""Execute one orchestrator-written review task."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn

from crustify.translate import (BATCH_FIELDS, RUN_FIELDS, RUN_OPTIONAL, Instructions, Placement,
                                RunSettings, check_fields, instructions_note,
                                parse_branch, parse_instructions, parse_placement,
                                parse_run, read_object, session_recorder,
                                task_file)

_OBJECTIVE = re.compile(r"^[a-z]+$")

#: Both artifacts a review batch writes, named for the role that wrote them.
_LOG_STEM = "reviewer"


@dataclass(frozen=True)
class ReviewBatch:
    """Validated review-batch input.

    A batch reviews one worklist: in a translate campaign, the ``commits``
    its translation batches landed; in an audit, ``paths`` of the crate,
    each a path or a path with the types, trait impls and functions to
    review in it. It
    may also carry ``reports`` to revisit. ``objectives`` is None when the
    batch names none, which enables every objective the reviewer offers that
    applies to it."""

    route: str
    commits: list[str]
    paths: list[object]
    reports: list[str]
    objectives: list[str] | None
    base_branch: str
    run: RunSettings
    placement: Placement
    instructions: Instructions | None = None
    #: Whether the batch runs its wave's gates: it is the wave's last review
    #: batch, launched once every translation batch of the wave has landed.
    wave_gates: bool = False


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


def _worklist_paths(raw: object) -> list[object]:
    """Paths, or ``{"path", "types", "trait_impls", "functions"}`` naming
    the part of a module too large to review whole."""
    if not isinstance(raw, list) or not raw:
        _fail("paths must be a non-empty array")
    entries: list[object] = []
    for i, module in enumerate(raw):
        label = f"paths[{i}]"
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
            entries.append(entry)
        else:
            entries.append(_path(module, label))
    named = [m["path"] if isinstance(m, dict) else m for m in entries]
    if len(set(named)) != len(named):
        _fail("paths names a path twice")
    return entries


def load_batch(path: Path) -> ReviewBatch:
    """Load and strictly validate a review batch.

    ``objectives`` replaces a translation batch's single ``objective``.
    ``reports`` names the report dirs a ``revisit`` batch re-examines, and is
    given exactly when ``revisit`` is. Which objective names exist depends on
    the tools the reviewer carries, so they are checked against the agent,
    not here."""
    raw = read_object(path, _fail)
    check_fields(raw, {"base_branch", "billing"} | BATCH_FIELDS,
                 {"commits", "paths", "reports", "objectives", "instructions",
                  "wave_gates"}
                 | RUN_FIELDS | RUN_OPTIONAL, _fail)
    if "commits" in raw and "paths" in raw:
        _fail("a batch carries commits or paths, not both")
    if not {"commits", "paths", "reports"} & set(raw):
        _fail("a batch needs commits, paths or reports")
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
    wave_gates = raw.get("wave_gates", False)
    if not isinstance(wave_gates, bool):
        _fail("wave_gates must be true or false")
    if wave_gates and "commits" not in raw:
        _fail("only a batch that reviews commits runs its wave's gates")
    reports = _paths(raw["reports"], "reports") if "reports" in raw else []
    route, commits, paths = "reports", [], []
    if "commits" in raw:
        commits = raw["commits"]
        if (not isinstance(commits, list) or not commits
                or any(not isinstance(c, str) or not _COMMIT.fullmatch(c)
                       for c in commits)
                or len(set(commits)) != len(commits)):
            _fail("commits must be a non-empty array of distinct commit ids")
        route = "commits"
    elif "paths" in raw:
        route, paths = "paths", _worklist_paths(raw["paths"])
    return ReviewBatch(route=route, commits=list(commits), paths=paths,
                       reports=reports, objectives=objectives,
                       base_branch=parse_branch(raw, _fail),
                       run=parse_run(raw, _fail),
                       placement=parse_placement(raw, _fail),
                       instructions=parse_instructions(raw, path, _fail),
                       wave_gates=wave_gates)


def execute(
    workdir: Path,
    task_path: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Run exactly one reviewer in ``workdir``.

    As for a translator, ``workdir`` is the worktree the orchestrator forked
    for this batch, which the harness neither creates nor purges.
    """
    task_path = task_file(task_path, _fail)
    batch = load_batch(task_path)
    base_branch = batch.base_branch

    from crustify.agents.review import ReviewAgent

    # Built before the dry-run returns: constructing the agent is what checks
    # the batch's objectives against the tools actually installed.
    agent = ReviewAgent(
        workdir.resolve(),
        route=batch.route,
        commits=batch.commits,
        paths=batch.paths,
        reports=batch.reports,
        objectives=batch.objectives,
        wave_gates=batch.wave_gates,
        git_base=base_branch,
        log_stem=_LOG_STEM,
    )
    agent.instructions = batch.instructions
    agent.placement = batch.placement
    agent.on_session = session_recorder(task_path)
    if dry_run:
        print(
            f"[review dry-run] one {batch.route} agent for "
            f"{batch.placement.batch_id} ({batch.placement.module_label}); "
            f"{len(batch.commits)} commit(s), {len(batch.paths)} path(s), "
            f"{len(batch.reports)} report(s); "
            f"{'runs' if batch.wave_gates else 'no'} wave gates; objectives "
            f"{', '.join(agent.objectives)}; landing on {base_branch}; "
            f"{batch.run.describe()}; "
            f"{instructions_note(batch.instructions)}; no agent spawned."
        )
        return

    print(f"[crustify spawn-reviewer] workdir: {agent.workdir}")
    print(f"[crustify spawn-reviewer] landing on: {base_branch}")
    print(f"[crustify spawn-reviewer] objectives: {', '.join(agent.objectives)}")
    print(f"[crustify spawn-reviewer] run: {batch.run.describe()}")
    if batch.instructions is not None:
        print("[crustify spawn-reviewer] additional instructions: "
              f"{batch.instructions.path}")
    batch.run.apply()
    agent.run()
    print("[crustify spawn-reviewer] batch completed.")
