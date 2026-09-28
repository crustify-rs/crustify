"""Execute one orchestrator-projected translation batch."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


_OBJECTIVES = frozenset({"wrap", "port", "review"})
_KINDS = frozenset({"type", "symbol", "callback", "raw-lifetime"})
_ITEM_FIELDS = frozenset({"name", "defined_in", "kind", "field_anchors", "home"})
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_LIFETIME_TIERS = frozenset({"void", "string"})


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


def load_batch(path: Path) -> Batch:
    """Load and strictly validate the thin batch schema."""
    try:
        raw = json.loads(path.read_text())
    except OSError as exc:
        _fail(f"cannot read batch {path}: {exc}")
    except json.JSONDecodeError as exc:
        _fail(f"invalid JSON in {path}: {exc}")

    if not isinstance(raw, dict):
        _fail("batch must be a JSON object")
    unknown = sorted(set(raw) - {"objective", "items"})
    missing = sorted({"objective", "items"} - set(raw))
    if unknown:
        _fail("unknown batch field(s): " + ", ".join(unknown))
    if missing:
        _fail("missing batch field(s): " + ", ".join(missing))

    objective = raw["objective"]
    if not isinstance(objective, str) or objective not in _OBJECTIVES:
        _fail("objective must be one of: port, review, wrap")
    items = raw["items"]
    if not isinstance(items, list) or not items:
        _fail("items must be a non-empty array")

    routes: set[str] = set()
    identities: set[tuple[str, str | None]] = set()
    validated: list[dict] = []
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            _fail(f"{label} must be an object")
        item_unknown = sorted(set(item) - _ITEM_FIELDS)
        item_missing = sorted(_ITEM_FIELDS - set(item))
        if item_unknown:
            _fail(f"{label} has unknown field(s): " + ", ".join(item_unknown))
        if item_missing:
            _fail(f"{label} is missing field(s): " + ", ".join(item_missing))

        name = item["name"]
        defined_in = item["defined_in"]
        kind = item["kind"]
        anchors = item["field_anchors"]
        home = item["home"]
        if not isinstance(name, str) or not name:
            _fail(f"{label}.name must be a non-empty string")
        if not isinstance(kind, str) or kind not in _KINDS:
            _fail(
                f"{label}.kind must be one of: callback, raw-lifetime, symbol, type")
        if not isinstance(anchors, list):
            _fail(f"{label}.field_anchors must be an array")
        if any(not isinstance(anchor, str) or not _FIELD_NAME.fullmatch(anchor)
               for anchor in anchors):
            _fail(f"{label}.field_anchors must contain C field identifiers")
        if len(set(anchors)) != len(anchors):
            _fail(f"{label}.field_anchors contains duplicates")
        if kind != "type" and anchors:
            _fail(f"{label}.field_anchors must be empty for kind {kind!r}")

        # The authored Rust file this item belongs in, decided by the
        # orchestrator and carried in the worklist. A translator resolves no
        # repo-tier artifact to find it: the batch is the whole input.
        if not isinstance(home, str) or not home or not home.endswith(".rs"):
            _fail(f"{label}.home must be a repo-relative .rs path")

        if kind == "raw-lifetime":
            if defined_in is not None:
                _fail(f"{label}.defined_in must be null for raw-lifetime")
        elif not isinstance(defined_in, str) or not defined_in:
            _fail(f"{label}.defined_in must be a non-empty string")

        identity = (name, defined_in)
        if identity in identities:
            _fail(f"duplicate item: {kind} {name!r} defined in {defined_in!r}")
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
        _fail("items resolve to mixed agent routes: " + ", ".join(sorted(routes)))
    route = routes.pop()
    if route == "raw-lifetime":
        if len(validated) != 1 or validated[0]["name"] not in _LIFETIME_TIERS:
            _fail("raw-lifetime batches must contain exactly one void or string item")

    return Batch(objective=objective, route=route, items=validated)


def _task_objective(batch: Batch) -> str:
    """Raw-lifetime discovery always wraps, except during explicit review."""
    if batch.route == "raw-lifetime" and batch.objective != "review":
        return "wrap"
    return batch.objective


def _validate_base_branch(repo: Path, base_branch: str) -> str:
    """The base branch's commit, or a failure naming why it cannot be landed on.

    Not worktree management -- the orchestrator owns that now. This is input
    validation: the agent's last act is an atomic fast-forward onto this
    branch, and both failures it catches would otherwise surface there, after
    the batch has been paid for.
    """
    base_branch = base_branch.removeprefix("refs/heads/")
    r = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify",
         f"refs/heads/{base_branch}"],
        capture_output=True, text=True)
    if r.returncode != 0:
        _fail(f"base branch does not exist: {base_branch}")
    for line in subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, check=True).stdout.splitlines():
        if line.strip() == f"branch refs/heads/{base_branch}":
            _fail(f"base branch is checked out in a worktree: {base_branch}")
    return r.stdout.strip()


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
    batch; the harness neither creates nor purges it. It validates the batch
    and the landing branch, then spends on the agent.
    """
    batch = load_batch(batch_path)
    output = output.resolve()
    if not output.is_dir():
        _fail(f"--output must name an existing directory: {output}")

    workdir = workdir.resolve()
    base_commit = _validate_base_branch(workdir, base_branch)

    effective = _task_objective(batch)
    if dry_run:
        normalized = (
            f"; task objective normalized to {effective}"
            if effective != batch.objective else ""
        )
        print(
            f"[translate dry-run] one {batch.route} agent; "
            f"{len(batch.items)} item(s); campaign objective "
            f"{batch.objective}{normalized}; base {base_branch} at "
            f"{base_commit}; no agent spawned."
        )
        return

    # The worktree's directory name is the batch id the orchestrator chose, so
    # a batch's logs carry the same name as the tree that produced them.
    batch_id = workdir.name
    print(f"[crustify translate] batch id: {batch_id}")
    print(f"[crustify translate] workdir: {workdir}")
    print(f"[crustify translate] base: {base_branch} at {base_commit}")
    print(f"[crustify translate] log: {output / f'{batch_id}.log'}")

    from crustify.agents.translate import TranslateAgent

    TranslateAgent(
        workdir,
        route=batch.route,
        items=batch.items,
        objective=effective,
        git_base=base_branch.removeprefix("refs/heads/"),
        log_dir=output,
        log_stem=batch_id,
    ).run()
    print(f"[crustify translate] batch {batch_id} completed.")
