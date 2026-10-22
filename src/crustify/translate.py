"""Execute one orchestrator-written binder or translator task."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NoReturn


_OBJECTIVES = frozenset({"wrap", "port"})
_KINDS = frozenset({"type", "symbol", "callback"})
_ITEM_FIELDS = frozenset({"name", "defined_in", "kind", "field_anchors", "home"})
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: How a provider CLI authenticates: its own logged-in account, or an API key
#: from the environment.
BILLINGS = ("subscription", "api")
#: The fields every task carries beside its worklist: how its agent runs.
RUN_FIELDS = frozenset({"model", "billing"})
#: The fields that place a binder's, translator's or reviewer's task in the
#: campaign's schedule.json.
BATCH_FIELDS = frozenset({"wave", "batch", "link_unit", "module"})

#: The role that runs each objective's tasks; its name is also the stem of
#: the log and usage record a batch writes into its own `--log-dir`, so
#: nothing has to be unique.
_ROLE = {"wrap": "binder", "port": "translator"}


@dataclass(frozen=True)
class RunSettings:
    """How a task's agent runs: its model and how its provider CLI bills."""

    model: str
    billing: str

    def apply(self) -> None:
        """Make these the settings every agent of this process runs under."""
        from crustify import config
        config.MODEL_OVERRIDE = self.model
        config.BILLING = self.billing


@dataclass(frozen=True)
class Instructions:
    """A task's additional instructions: the file that holds them, and its
    text, which the agent's prompt carries as its own section."""

    path: Path
    text: str


@dataclass(frozen=True)
class Placement:
    """Where a task's batch sits in the schedule: its wave and index, which
    form its batch id, and the link unit and module its wave belongs to."""

    wave: int
    batch: int
    link_unit: str | None
    module: str | None

    @property
    def batch_id(self) -> str:
        return f"wave-{self.wave}/batch-{self.batch}"

    @property
    def module_label(self) -> str:
        """``<link-unit>/<module>``, or ``none`` for a wave of no
        module."""
        if self.module is None:
            return "none"
        return f"{self.link_unit}/{self.module}"


@dataclass(frozen=True)
class Batch:
    """Validated binder or translator task."""

    objective: str
    route: str
    items: list[dict]
    base_branch: str
    run: RunSettings
    placement: Placement
    instructions: Instructions | None = None


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"translate: {message}")


def _route(kind: str) -> str:
    return "type" if kind == "type" else "symbol"


def read_object(path: Path, fail: Callable[[str], NoReturn]) -> dict:
    """The task file's JSON object, or a failure naming what is wrong."""
    try:
        raw = json.loads(path.read_text())
    except OSError as exc:
        fail(f"cannot read task {path}: {exc}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(raw, dict):
        fail("task must be a JSON object")
    return raw


def parse_run(raw: dict, fail: Callable[[str], NoReturn]) -> RunSettings:
    """A task's ``model`` and ``billing``. The model must name a known
    provider, so a typo fails here rather than after the worktree is set up."""
    from crustify.core.models import resolve

    model, billing = raw["model"], raw["billing"]
    if not isinstance(model, str) or not model:
        fail("model must be a non-empty <provider>/<model> name")
    try:
        resolve(model)
    except ValueError as exc:
        fail(str(exc))
    if billing not in BILLINGS:
        fail(f"billing must be one of: {', '.join(BILLINGS)}")
    return RunSettings(model=model, billing=billing)


def task_and_log_dir(task_path: Path, log_dir: Path,
                     fail: Callable[[str], NoReturn]) -> tuple[Path, Path]:
    """The task file and the log dir, both resolved; a failure when either
    is not where the command says, before anything else is read."""
    task_path, log_dir = task_path.resolve(), log_dir.resolve()
    if not task_path.is_file():
        fail(f"no task file at {task_path}")
    if not log_dir.is_dir():
        fail(f"--log-dir must name an existing directory: {log_dir}")
    return task_path, log_dir


def parse_branch(raw: dict, fail: Callable[[str], NoReturn]) -> str:
    """The unchecked-out integration branch a task lands on."""
    branch = raw["base_branch"]
    if not isinstance(branch, str) or not branch.strip():
        fail("base_branch must name a branch")
    return branch.removeprefix("refs/heads/")


def parse_placement(raw: dict, fail: Callable[[str], NoReturn]) -> Placement:
    """A task's ``wave``, ``batch``, ``link_unit`` and ``module``."""
    for key in ("wave", "batch"):
        value = raw[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail(f"{key} must be a non-negative index")
    for key in ("link_unit", "module"):
        value = raw[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            fail(f"{key} must be a name or null")
    if raw["module"] is not None and raw["link_unit"] is None:
        fail("a module needs its link_unit")
    return Placement(wave=raw["wave"], batch=raw["batch"],
                     link_unit=raw["link_unit"], module=raw["module"])


def parse_instructions(raw: dict, task_path: Path,
                       fail: Callable[[str], NoReturn]) -> Instructions | None:
    """The file a task's optional ``instructions`` names, resolved against the
    task's own directory, and its text; a failure when it is unreadable or
    empty."""
    if "instructions" not in raw:
        return None
    name = raw["instructions"]
    if not isinstance(name, str) or not name.strip():
        fail("instructions must name a file")
    path = (task_path.parent / name).resolve()
    try:
        text = path.read_text().strip()
    except OSError as exc:
        fail(f"cannot read instructions {path}: {exc}")
    if not text:
        fail(f"instructions file is empty: {path}")
    return Instructions(path=path, text=text)


def instructions_note(instructions: Instructions | None) -> str:
    """How a dry run reports a task's additional instructions."""
    if instructions is None:
        return "no additional instructions"
    return f"additional instructions from {instructions.path}"


def check_fields(raw: dict, required: set[str], optional: set[str],
                 fail: Callable[[str], NoReturn]) -> None:
    """Reject unknown and missing top-level task fields."""
    unknown = sorted(set(raw) - required - optional)
    missing = sorted(required - set(raw))
    if unknown:
        fail("unknown task field(s): " + ", ".join(unknown))
    if missing:
        fail("missing task field(s): " + ", ".join(missing))


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
                f"{label}.kind must be one of: callback, symbol, type")
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

        if not isinstance(defined_in, str) or not defined_in:
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
    return routes.pop(), validated


def load_batch(path: Path) -> Batch:
    """Load and strictly validate a binder or translator task, ``path``
    resolved."""
    raw = read_object(path, _fail)
    check_fields(raw, {"objective", "items", "base_branch"} | RUN_FIELDS | BATCH_FIELDS,
                 {"instructions"}, _fail)
    objective = raw["objective"]
    if not isinstance(objective, str) or objective not in _OBJECTIVES:
        _fail("objective must be one of: port, wrap"
              + ("; a review batch runs under `crustify spawn-reviewer`"
                 if objective == "review" else ""))
    route, items = parse_items(raw["items"], _fail)
    return Batch(objective=objective, route=route, items=items,
                 base_branch=parse_branch(raw, _fail),
                 run=parse_run(raw, _fail),
                 placement=parse_placement(raw, _fail),
                 instructions=parse_instructions(raw, path, _fail))


def execute(
    workdir: Path,
    task_path: Path,
    *,
    role: str,
    log_dir: Path,
    dry_run: bool = False,
) -> None:
    """Run exactly one binder or translator, as ``role`` says, in ``workdir``.

    A binder runs `wrap` tasks; a translator runs `port` tasks. ``workdir`` is the isolated worktree the
    orchestrator forked for this batch, and ``log_dir`` the existing
    directory its log and usage record land in; the harness creates and
    purges neither.
    """
    task_path, output = task_and_log_dir(task_path, log_dir, _fail)
    batch = load_batch(task_path)
    base_branch = batch.base_branch
    if _ROLE[batch.objective] != role:
        _fail(f"a {batch.objective} batch runs under "
              f"`crustify spawn-{_ROLE[batch.objective]}`")
    workdir = workdir.resolve()
    if dry_run:
        print(
            f"[{role} dry-run] one {batch.route} agent for "
            f"{batch.placement.batch_id} ({batch.placement.module_label}); "
            f"{len(batch.items)} item(s); campaign objective "
            f"{batch.objective}; landing on {base_branch}; "
            f"model {batch.run.model} ({batch.run.billing}); "
            f"{instructions_note(batch.instructions)}; no agent spawned."
        )
        return

    # Fixed names: `output` is this run's own directory, so there is nothing
    # to disambiguate. The orchestrator decides what a run is called by
    # deciding where its artifacts go.
    print(f"[crustify spawn-{role}] workdir: {workdir}")
    print(f"[crustify spawn-{role}] landing on: {base_branch}")
    print(f"[crustify spawn-{role}] model: {batch.run.model} ({batch.run.billing})")
    print(f"[crustify spawn-{role}] session: {output / f'{role}.session.json'}")
    if batch.instructions is not None:
        print(f"[crustify spawn-{role}] additional instructions: "
              f"{batch.instructions.path}")

    if role == "binder":
        from crustify.agents.bind import BindAgent as Agent
    else:
        from crustify.agents.translate import TranslateAgent as Agent

    batch.run.apply()
    agent = Agent(
        workdir,
        route=batch.route,
        items=batch.items,
        git_base=base_branch,
        artifact_dir=output,
        log_stem=role,
    )
    agent.instructions = batch.instructions
    agent.placement = batch.placement
    agent.run()
    print(f"[crustify spawn-{role}] batch completed.")
