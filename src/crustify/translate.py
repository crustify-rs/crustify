"""Execute one orchestrator-projected translation batch."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NoReturn


_OBJECTIVES = frozenset({"wrap", "port"})
_KINDS = frozenset({"type", "symbol", "callback", "raw-lifetime"})
_ITEM_FIELDS = frozenset({"name", "defined_in", "kind", "field_anchors", "home"})
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LIFETIME_TIERS = frozenset({"void", "string"})

#: Both artifacts a batch writes, named for the role that wrote them. They sit
#: in the batch's own `--output` directory, so nothing has to be unique.
_LOG_STEM = "translator"


@dataclass(frozen=True)
class Batch:
    """Validated thin-batch input."""

    objective: str
    route: str
    items: list[dict]


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"translate: {message}")


def _route(kind: str) -> str:
    if kind == "type":
        return "type"
    if kind in ("symbol", "callback"):
        return "symbol"
    return "raw-lifetime"


def read_object(path: Path, fail: Callable[[str], NoReturn]) -> dict:
    """The batch file's JSON object, or a failure naming what is wrong."""
    try:
        raw = json.loads(path.read_text())
    except OSError as exc:
        fail(f"cannot read batch {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(raw, dict):
        fail("batch must be a JSON object")
    return raw


def check_fields(raw: dict, required: set[str], optional: set[str],
                 fail: Callable[[str], NoReturn]) -> None:
    """Reject unknown and missing top-level batch fields."""
    unknown = sorted(set(raw) - required - optional)
    missing = sorted(required - set(raw))
    if unknown:
        fail("unknown batch field(s): " + ", ".join(unknown))
    if missing:
        fail("missing batch field(s): " + ", ".join(missing))


def parse_items(items: object, fail: Callable[[str], NoReturn]
                ) -> tuple[str, list[dict]]:
    """Validate a batch's items; return their one route and the items.

    Shared by the translator and the reviewer: both take the same thin
    worklist, and differ only in what else the batch says."""
    if not isinstance(items, list) or not items:
        fail("items must be a non-empty array")

    routes: set[str] = set()
    identities: set[tuple[str, str | None]] = set()
    validated: list[dict] = []
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            fail(f"{label} must be an object")
        item_unknown = sorted(set(item) - _ITEM_FIELDS)
        item_missing = sorted(_ITEM_FIELDS - set(item))
        if item_unknown:
            fail(f"{label} has unknown field(s): " + ", ".join(item_unknown))
        if item_missing:
            fail(f"{label} is missing field(s): " + ", ".join(item_missing))

        name = item["name"]
        defined_in = item["defined_in"]
        kind = item["kind"]
        anchors = item["field_anchors"]
        home = item["home"]
        if not isinstance(name, str) or not name:
            fail(f"{label}.name must be a non-empty string")
        if not isinstance(kind, str) or kind not in _KINDS:
            fail(
                f"{label}.kind must be one of: callback, raw-lifetime, symbol, type")
        if not isinstance(anchors, list):
            fail(f"{label}.field_anchors must be an array")
        if any(not isinstance(anchor, str) or not _FIELD_NAME.fullmatch(anchor)
               for anchor in anchors):
            fail(f"{label}.field_anchors must contain C field identifiers")
        if len(set(anchors)) != len(anchors):
            fail(f"{label}.field_anchors contains duplicates")
        if kind != "type" and anchors:
            fail(f"{label}.field_anchors must be empty for kind {kind!r}")

        # The authored Rust file this item belongs in, decided by the
        # orchestrator and carried in the worklist. An agent resolves no
        # repo-tier artifact to find it: the batch is the whole input.
        if not isinstance(home, str) or not home or not home.endswith(".rs"):
            fail(f"{label}.home must be a repo-relative .rs path")

        if kind == "raw-lifetime":
            if defined_in is not None:
                fail(f"{label}.defined_in must be null for raw-lifetime")
        elif not isinstance(defined_in, str) or not defined_in:
            fail(f"{label}.defined_in must be a non-empty string")

        identity = (name, defined_in)
        if identity in identities:
            fail(f"duplicate item: {kind} {name!r} defined in {defined_in!r}")
        identities.add(identity)
        routes.add(_route(kind))
        validated.append({
            "name": name,
            "defined_in": defined_in,
            "kind": kind,
            "field_anchors": list(anchors),
            "home": home,
        })

    if len(routes) != 1:
        fail("items resolve to mixed agent routes: " + ", ".join(sorted(routes)))
    route = routes.pop()
    if route == "raw-lifetime":
        if len(validated) != 1 or validated[0]["name"] not in _LIFETIME_TIERS:
            fail("raw-lifetime batches must contain exactly one void or string item")
    return route, validated


def load_batch(path: Path) -> Batch:
    """Load and strictly validate the thin batch schema."""
    raw = read_object(path, _fail)
    check_fields(raw, {"objective", "items"}, set(), _fail)
    objective = raw["objective"]
    if not isinstance(objective, str) or objective not in _OBJECTIVES:
        _fail("objective must be one of: port, wrap"
              + ("; a review batch runs under `crustify spawn-reviewer`"
                 if objective == "review" else ""))
    route, items = parse_items(raw["items"], _fail)
    return Batch(objective=objective, route=route, items=items)


def _task_objective(batch: Batch) -> str:
    """Raw-lifetime discovery always wraps, in a port campaign too."""
    if batch.route == "raw-lifetime":
        return "wrap"
    return batch.objective


def execute(
    workdir: Path,
    batch_path: Path,
    *,
    base_branch: str,
    output: Path,
    dry_run: bool = False,
) -> None:
    """Run exactly one translator in ``workdir``.

    ``workdir`` is the isolated worktree the orchestrator forked for this
    batch and ``output`` the directory that batch's artifacts land in; the
    harness creates and purges neither.
    """
    batch = load_batch(batch_path)
    output = output.resolve()
    if not output.is_dir():
        _fail(f"--output must name an existing directory: {output}")

    workdir = workdir.resolve()
    effective = _task_objective(batch)
    if dry_run:
        normalized = (
            f"; task objective normalized to {effective}"
            if effective != batch.objective else ""
        )
        print(
            f"[translate dry-run] one {batch.route} agent; "
            f"{len(batch.items)} item(s); campaign objective "
            f"{batch.objective}{normalized}; landing on {base_branch}; "
            "no agent spawned."
        )
        return

    # Fixed names: `output` is this batch's own directory, so there is nothing
    # to disambiguate. The orchestrator decides what a batch is called by
    # deciding where its artifacts go.
    print(f"[crustify spawn-translator] workdir: {workdir}")
    print(f"[crustify spawn-translator] landing on: {base_branch}")
    print(f"[crustify spawn-translator] log: {output / f'{_LOG_STEM}.log'}")

    from crustify.agents.translate import TranslateAgent

    TranslateAgent(
        workdir,
        route=batch.route,
        items=batch.items,
        objective=effective,
        git_base=base_branch.removeprefix("refs/heads/"),
        artifact_dir=output,
        log_stem=_LOG_STEM,
    ).run()
    print("[crustify spawn-translator] batch completed.")
