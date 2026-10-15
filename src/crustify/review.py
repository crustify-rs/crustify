"""Execute one orchestrator-projected review batch."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn

from crustify.translate import check_fields, parse_items, read_object

_OBJECTIVE = re.compile(r"^[a-z]+$")

#: Both artifacts a review batch writes, named for the role that wrote them.
_LOG_STEM = "reviewer"


@dataclass(frozen=True)
class ReviewBatch:
    """Validated review-batch input.

    A batch reviews one worklist: wavefront ``items`` of one route; or, for a
    crate wavefront does not describe, ``modules``, its source files and
    directories, or ``sites``, the ffimap sites to start from. It may also
    carry ``reports`` to revisit. ``objectives`` is None when the
    batch names none, which enables every objective the reviewer offers that
    applies to it."""

    route: str
    items: list[dict]
    modules: list[str]
    sites: list[dict]
    reports: list[str]
    objectives: list[str] | None


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"review: {message}")


def _paths(raw: object, field: str) -> list[str]:
    """A non-empty array of distinct repo-relative paths."""
    if (not isinstance(raw, list) or not raw
            or any(not isinstance(p, str) or not p for p in raw)):
        _fail(f"{field} must be a non-empty array of paths")
    for p in raw:
        if PurePosixPath(p).is_absolute() or ".." in PurePosixPath(p).parts:
            _fail(f"{field} must hold repo-relative paths: {p}")
    if len(set(raw)) != len(raw):
        _fail(f"{field} contains duplicates")
    return list(raw)


_SITE_FIELDS = frozenset({"counter", "file", "lines"})
_COUNTER = re.compile(r"^[a-z][a-z0-9_]*(:[A-Za-z0-9_:<>]+)?$")


def _sites(raw: object) -> list[dict]:
    """ffimap sites, one counter's lines in one file each: the shape of
    ffimap's own `sites` record, with the counter named."""
    if not isinstance(raw, list) or not raw:
        _fail("sites must be a non-empty array")
    seen: set[tuple[str, str]] = set()
    for index, site in enumerate(raw):
        label = f"sites[{index}]"
        if not isinstance(site, dict) or set(site) != _SITE_FIELDS:
            _fail(f"{label} must be an object with exactly: counter, file, lines")
        if not isinstance(site["counter"], str) \
                or not _COUNTER.fullmatch(site["counter"]):
            _fail(f"{label}.counter must be an ffimap counter name")
        _paths([site["file"]], f"{label}.file")
        lines = site["lines"]
        if (not isinstance(lines, list) or not lines
                or any(not isinstance(n, int) or isinstance(n, bool) or n < 1
                       for n in lines)
                or len(set(lines)) != len(lines)):
            _fail(f"{label}.lines must be a non-empty array of distinct line numbers")
        key = (site["counter"], site["file"])
        if key in seen:
            _fail(f"{label} repeats counter {key[0]} in {key[1]}")
        seen.add(key)
    return [dict(site) for site in raw]


def load_batch(path: Path) -> ReviewBatch:
    """Load and strictly validate a review batch.

    Its ``items`` are a binder's or translator's thin worklist, and
    ``modules`` or ``sites`` replace them for a crate wavefront does not
    describe;
    ``objectives`` replaces their single ``objective``. ``reports`` names the
    report dirs a ``revisit`` batch re-examines, and is given exactly when
    ``revisit`` is. Which objective names exist depends on the skills the
    reviewer carries, so they are checked against the agent, not here."""
    raw = read_object(path, _fail)
    check_fields(raw, set(),
                 {"items", "modules", "sites", "reports", "objectives"}, _fail)
    worklists = sorted({"items", "modules", "sites"} & set(raw))
    if len(worklists) > 1:
        _fail("a batch carries one of items, modules or sites, not "
              + " and ".join(worklists))
    if not worklists and "reports" not in raw:
        _fail("a batch needs items, modules, sites or reports")
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
    route, items, modules, sites = "reports", [], [], []
    if "items" in raw:
        route, items = parse_items(raw["items"], _fail)
    elif "modules" in raw:
        route, modules = "modules", _paths(raw["modules"], "modules")
    elif "sites" in raw:
        route, sites = "sites", _sites(raw["sites"])
    return ReviewBatch(route=route, items=items, modules=modules, sites=sites,
                       reports=reports, objectives=objectives)


def execute(
    workdir: Path,
    batch_path: Path,
    *,
    base_branch: str,
    output: Path,
    dry_run: bool = False,
) -> None:
    """Run exactly one reviewer in ``workdir``.

    As for a translator, ``workdir`` is the worktree the orchestrator forked
    for this batch and ``output`` the directory its artifacts land in; the
    harness creates and purges neither.
    """
    batch = load_batch(batch_path)
    output = output.resolve()
    if not output.is_dir():
        _fail(f"--output must name an existing directory: {output}")

    from crustify.agents.review import ReviewAgent

    # Built before the dry-run returns: constructing the agent is what checks
    # the batch's objectives against the skills actually installed.
    agent = ReviewAgent(
        workdir.resolve(),
        route=batch.route,
        items=batch.items,
        modules=batch.modules,
        sites=batch.sites,
        reports=batch.reports,
        objectives=batch.objectives,
        git_base=base_branch.removeprefix("refs/heads/"),
        artifact_dir=output,
        log_stem=_LOG_STEM,
    )
    if dry_run:
        print(
            f"[review dry-run] one {batch.route} agent; "
            f"{len(batch.items)} item(s), {len(batch.modules)} module(s), "
            f"{len(batch.sites)} site(s), "
            f"{len(batch.reports)} report(s); objectives "
            f"{', '.join(agent.objectives)}; landing on {base_branch}; "
            "no agent spawned."
        )
        return

    print(f"[crustify spawn-reviewer] workdir: {agent.workdir}")
    print(f"[crustify spawn-reviewer] landing on: {base_branch}")
    print(f"[crustify spawn-reviewer] objectives: {', '.join(agent.objectives)}")
    print(f"[crustify spawn-reviewer] log: {output / f'{_LOG_STEM}.log'}")
    agent.run()
    print("[crustify spawn-reviewer] batch completed.")
