"""Execute one orchestrator-written planner task."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from crustify.translate import (RUN_FIELDS, RUN_OPTIONAL, Instructions, RunSettings, check_fields,
                                instructions_note, parse_instructions, parse_run,
                                read_object, session_recorder, task_file)

#: Both artifacts a planner run writes, named for the role that wrote them.
_LOG_STEM = "planner"


@dataclass(frozen=True)
class PlanBatch:
    """Validated planner task: how the run runs."""

    run: RunSettings
    instructions: Instructions | None = None


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"plan: {message}")


def load_batch(path: Path) -> PlanBatch:
    """Load and strictly validate a planner task: its run fields,
    and optionally ``instructions``. A planner commits on the planning
    branch checked out in the base dir; the orchestrator promotes it."""
    raw = read_object(path, _fail)
    check_fields(raw, {"billing"}, {"instructions"} | RUN_FIELDS | RUN_OPTIONAL,
                 _fail)
    return PlanBatch(run=parse_run(raw, _fail),
                     instructions=parse_instructions(raw, path, _fail))


def execute(workdir: Path, task_path: Path, *, dry_run: bool = False) -> None:
    """Run exactly one planner in ``workdir``, the campaign checkout on its
    planning branch."""
    task_path = task_file(task_path, _fail)
    batch = load_batch(task_path)

    from crustify.agents.plan import PlanAgent

    agent = PlanAgent(workdir.resolve(), log_stem=_LOG_STEM)
    agent.instructions = batch.instructions
    agent.on_session = session_recorder(task_path)
    if dry_run:
        print(f"[plan dry-run] one planner; "
              f"{batch.run.describe()}; "
              f"{instructions_note(batch.instructions)}; no agent spawned.")
        return

    print(f"[crustify spawn-planner] workdir: {agent.workdir}")
    print(f"[crustify spawn-planner] run: {batch.run.describe()}")
    if batch.instructions is not None:
        print("[crustify spawn-planner] additional instructions: "
              f"{batch.instructions.path}")
    batch.run.apply()
    agent.run()
    print("[crustify spawn-planner] run completed.")
