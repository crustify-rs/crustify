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
#: The fields an item may carry beside those: its step, and what a step follows.
_ITEM_OPTIONAL = frozenset({"step", "of"})
#: An item's steps: its translation, and the deferred steps of a port campaign
#: (specs/planning/scheduling.md, Deferred items). ``of`` names the library
#: entity a ``std`` step moves onto the standard library.
_STEPS = frozenset({"translate", "layout", "memory", "retire", "std"})
_STEPS_WITH_OF = frozenset({"std"})
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

#: The fields every task carries beside its worklist: how its agent runs.
RUN_FIELDS = frozenset({"backend", "billing"})
#: The run fields a task may carry: the proxy, and the provider CLI's own
#: arguments; ``session_id``, which the spawn command writes once its run
#: has one; and ``model``, an earlier version's, read in place of
#: ``backend``.
RUN_OPTIONAL = frozenset({"model_proxy", "args", "model", "session_id"})
#: The fields that place a binder's, translator's or reviewer's task in the
#: campaign's schedule.json.
BATCH_FIELDS = frozenset({"wave", "batch", "link_unit", "module", "foundational"})

#: The role that runs each objective's tasks; its name is also the stem of
#: the session record a batch's session leaves in crustify's home.
_ROLE = {"wrap": "binder", "port": "translator"}


@dataclass(frozen=True)
class RunSettings:
    """How a task's agent runs: its provider CLI, how it bills, through
    which proxy, and the CLI's own arguments."""

    backend: str
    billing: str
    model_proxy: str | None = None
    args: tuple[str, ...] = ()

    def apply(self) -> None:
        """Make these the settings every agent of this process runs under.
        Arguments given on the command line follow the task's."""
        from crustify import config
        config.BACKEND = self.backend
        config.BILLING = self.billing
        config.MODEL_PROXY = self.model_proxy
        config.PROVIDER_ARGS = [*self.args, *config.PROVIDER_ARGS]

    def describe(self) -> str:
        """One line for the spawn commands' output."""
        parts = [self.backend, self.billing]
        if self.model_proxy:
            parts.append(f"via {self.model_proxy}")
        if self.args:
            parts.append("args: " + " ".join(self.args))
        return ", ".join(parts)


@dataclass(frozen=True)
class Instructions:
    """A task's additional instructions: the file that holds them, and its
    text, which the agent's prompt carries as its own section."""

    path: Path
    text: str


@dataclass(frozen=True)
class Placement:
    """Where a task's batch sits in the schedule: its wave and index, which
    form its batch id, and the link unit and module its wave belongs to: the
    module's name, and whether it is foundational, which tells apart the two
    modules of a split TU."""

    wave: int
    batch: int
    link_unit: str | None
    module: str | None
    foundational: bool = False

    @property
    def batch_id(self) -> str:
        return f"wave-{self.wave}/batch-{self.batch}"

    @property
    def module_label(self) -> str:
        """``<link-unit>/<module>``, with `` (foundational)`` for a
        foundational module, or ``none`` for a wave of no module."""
        if self.module is None:
            return "none"
        label = f"{self.link_unit}/{self.module}"
        return label + " (foundational)" if self.foundational else label


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
    """A task's run fields, checked, so a typo fails here rather than after
    the worktree is set up. A task of an earlier version names a
    ``<provider>/<model>`` in place of ``backend``."""
    from crustify.core.models import from_model, route

    if "session_id" in raw:
        fail(f"this task already ran, as session {raw['session_id']}: a rerun "
             "takes a run dir and a task of its own")
    try:
        if "backend" not in raw and "model" in raw:
            r = from_model(raw["model"], raw.get("billing", "subscription"))
        else:
            if "backend" not in raw:
                fail("missing task field(s): backend")
            if "model" in raw:
                fail("a task names its backend, not a model: pass the model "
                     "in args, in the CLI's own syntax")
            args = raw.get("args", [])
            if not isinstance(args, list):
                fail("args must be an array of strings")
            r = route(raw["backend"], raw.get("billing"),
                      raw.get("model_proxy"), args)
    except ValueError as exc:
        fail(str(exc))
    return RunSettings(r.backend, r.billing, r.model_proxy, r.args)


def task_file(task_path: Path, fail: Callable[[str], NoReturn]) -> Path:
    """The task file, resolved; a failure when it is not where the command
    says, before anything else is read."""
    task_path = task_path.resolve()
    if not task_path.is_file():
        fail(f"no task file at {task_path}")
    return task_path


def session_recorder(task_path: Path) -> Callable[[str], None]:
    """What writes a run's session id into its task, as soon as the CLI has
    one: the task is the run's record in the campaign, and its session's
    records are in crustify's home, under that id."""
    def record(session_id: str) -> None:
        raw = json.loads(task_path.read_text())
        raw["session_id"] = session_id
        tmp = task_path.with_name(task_path.name + ".tmp")
        tmp.write_text(json.dumps(raw, indent=2) + "\n")
        tmp.replace(task_path)
    return record


def parse_branch(raw: dict, fail: Callable[[str], NoReturn]) -> str:
    """The unchecked-out integration branch a task lands on."""
    branch = raw["base_branch"]
    if not isinstance(branch, str) or not branch.strip():
        fail("base_branch must name a branch")
    return branch.removeprefix("refs/heads/")


def parse_placement(raw: dict, fail: Callable[[str], NoReturn]) -> Placement:
    """A task's ``wave``, ``batch``, ``link_unit``, ``module`` and
    ``foundational``."""
    for key in ("wave", "batch"):
        value = raw[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            fail(f"{key} must be a non-negative index")
    link_unit, module = raw["link_unit"], raw["module"]
    foundational = raw["foundational"]
    for key, value in (("link_unit", link_unit), ("module", module)):
        if value is not None and (not isinstance(value, str)
                                  or not value.strip()):
            fail(f"{key} must be a name or null")
    if not isinstance(foundational, bool):
        fail("foundational must be true or false")
    if module is not None and link_unit is None:
        fail("a module needs its link_unit")
    if module is None and foundational:
        fail("a wave of no module is not foundational")
    return Placement(wave=raw["wave"], batch=raw["batch"],
                     link_unit=link_unit, module=module,
                     foundational=foundational)


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
    identities: set[tuple] = set()
    validated: list[dict] = []
    for index, item in enumerate(items):
        label = f"items[{index}]"
        if not isinstance(item, dict):
            fail(f"{label} must be an object")
        item_unknown = sorted(set(item) - _ITEM_FIELDS - _ITEM_OPTIONAL)
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

        step = item.get("step", "translate")
        if not isinstance(step, str) or step not in _STEPS:
            fail(f"{label}.step must be one of: " + ", ".join(sorted(_STEPS)))
        of = item.get("of")
        if step in _STEPS_WITH_OF:
            if (not isinstance(of, dict) or set(of) != {"name", "defined_in"}
                    or not all(isinstance(v, str) and v for v in of.values())):
                fail(f"{label}.of must name what its {step} step follows, "
                     "as {name, defined_in}")
        elif of is not None:
            fail(f"{label}.of is only carried by a std step")

        identity = (name, defined_in, step,
                    None if of is None else (of["name"], of["defined_in"]))
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
            "step": step,
            "of": None if of is None else dict(of),
        })

    if len(routes) != 1:
        fail("items resolve to mixed agent routes: " + ", ".join(sorted(routes)))
    return routes.pop(), validated


def load_batch(path: Path) -> Batch:
    """Load and strictly validate a binder or translator task, ``path``
    resolved."""
    raw = read_object(path, _fail)
    check_fields(raw, {"objective", "items", "base_branch", "billing"} | BATCH_FIELDS,
                 {"instructions"} | RUN_FIELDS | RUN_OPTIONAL, _fail)
    objective = raw["objective"]
    if not isinstance(objective, str) or objective not in _OBJECTIVES:
        _fail("objective must be one of: port, wrap"
              + ("; a review batch runs under `crustify spawn-reviewer`"
                 if objective == "review" else ""))
    route, items = parse_items(raw["items"], _fail)
    if objective == "wrap" and any(item["step"] != "translate" for item in items):
        _fail("a deferred step (layout, memory, retire, std) "
              "is only carried by a port batch")
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
    dry_run: bool = False,
) -> None:
    """Run exactly one binder or translator, as ``role`` says, in ``workdir``.

    A binder runs `wrap` tasks; a translator runs `port` tasks. ``workdir``
    is the isolated worktree the orchestrator forked for this batch, which
    the harness neither creates nor purges.
    """
    task_path = task_file(task_path, _fail)
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
            f"{batch.run.describe()}; "
            f"{instructions_note(batch.instructions)}; no agent spawned."
        )
        return

    print(f"[crustify spawn-{role}] workdir: {workdir}")
    print(f"[crustify spawn-{role}] landing on: {base_branch}")
    print(f"[crustify spawn-{role}] run: {batch.run.describe()}")
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
        log_stem=role,
    )
    agent.instructions = batch.instructions
    agent.placement = batch.placement
    agent.on_session = session_recorder(task_path)
    agent.run()
    print(f"[crustify spawn-{role}] batch completed.")
