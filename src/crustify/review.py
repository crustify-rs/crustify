"""Execute one orchestrator-projected review batch."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import EllipsisType
from typing import NoReturn

from crustify.translate import check_fields, parse_items, read_object

_OBJECTIVE = re.compile(r"^[a-z]+$")

#: Both artifacts a review batch writes, named for the role that wrote them.
_LOG_STEM = "reviewer"


@dataclass(frozen=True)
class ReviewBatch:
    """Validated review-batch input. ``objectives`` is None when the batch
    names none, which enables every objective the reviewer offers."""

    route: str
    items: list[dict]
    objectives: list[str] | None
    #: The batch's `conventions`: absent (``...``) means Crustify's own,
    #: ``None`` means the reviewed codebase has none, and a string names its
    #: document, relative to the workdir unless absolute.
    conventions: str | None | EllipsisType = ...


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"review: {message}")


def load_batch(path: Path) -> ReviewBatch:
    """Load and strictly validate a review batch.

    Its items are a translator's thin worklist; ``objectives`` replaces the
    translator's single ``objective``. Which objective names exist depends on
    the skills the reviewer carries, so they are checked against the agent,
    not here."""
    raw = read_object(path, _fail)
    check_fields(raw, {"items"}, {"objectives", "conventions"}, _fail)
    conventions = raw.get("conventions", ...)
    if conventions is not ... and conventions is not None \
            and (not isinstance(conventions, str) or not conventions):
        _fail("conventions must be a path to a document, or null")
    objectives = raw.get("objectives")
    if objectives is not None:
        if (not isinstance(objectives, list) or not objectives
                or any(not isinstance(o, str) or not _OBJECTIVE.fullmatch(o)
                       for o in objectives)):
            _fail("objectives must be a non-empty array of objective names")
        if len(set(objectives)) != len(objectives):
            _fail("objectives contains duplicates")
    route, items = parse_items(raw["items"], _fail)
    return ReviewBatch(route=route, items=items, objectives=objectives,
                       conventions=conventions)


def _conventions(batch: ReviewBatch, workdir: Path) -> Path | None:
    """The conventions document a batch names, resolved."""
    from crustify.agents.review import CRUSTIFY_CONVENTIONS
    if batch.conventions is ...:
        return CRUSTIFY_CONVENTIONS
    if batch.conventions is None:
        return None
    path = Path(batch.conventions)
    return path if path.is_absolute() else workdir / path


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
    workdir = workdir.resolve()
    agent = ReviewAgent(
        workdir,
        route=batch.route,
        items=batch.items,
        objectives=batch.objectives,
        conventions=_conventions(batch, workdir),
        git_base=base_branch.removeprefix("refs/heads/"),
        artifact_dir=output,
        log_stem=_LOG_STEM,
    )
    if dry_run:
        print(
            f"[review dry-run] one {batch.route} agent; "
            f"{len(batch.items)} item(s); objectives "
            f"{', '.join(agent.objectives)}; landing on {base_branch}; "
            "no agent spawned."
        )
        return

    print(f"[crustify spawn-reviewer] workdir: {agent.workdir}")
    print(f"[crustify spawn-reviewer] landing on: {base_branch}")
    print(f"[crustify spawn-reviewer] objectives: {', '.join(agent.objectives)}")
    print(f"[crustify spawn-reviewer] conventions: {agent._arguments()['conventions']}")
    print(f"[crustify spawn-reviewer] log: {output / f'{_LOG_STEM}.log'}")
    agent.run()
    print("[crustify spawn-reviewer] batch completed.")
