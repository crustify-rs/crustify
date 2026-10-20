"""Execute one orchestrator-written planner task."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from crustify.translate import (RUN_FIELDS, Instructions, RunSettings, check_fields,
                                instructions_note, parse_instructions, parse_run,
                                read_object, task_and_log_dir)

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
    """Load and strictly validate a planner task: ``model`` and ``billing``,
    and optionally ``instructions``. A planner commits on the planning
    branch checked out in the base dir; the orchestrator promotes it."""
    raw = read_object(path, _fail)
    check_fields(raw, set(RUN_FIELDS), {"instructions"}, _fail)
    return PlanBatch(run=parse_run(raw, _fail),
                     instructions=parse_instructions(raw, path, _fail))


def execute(workdir: Path, task_path: Path, *, log_dir: Path,
            dry_run: bool = False) -> None:
    """Run exactly one planner in ``workdir``, the campaign checkout on its
    planning branch. ``log_dir`` is the existing directory that receives
    the run's log and usage record."""
    task_path, output = task_and_log_dir(task_path, log_dir, _fail)
    batch = load_batch(task_path)

    from crustify.agents.plan import PlanAgent

    agent = PlanAgent(workdir.resolve(), artifact_dir=output, log_stem=_LOG_STEM)
    agent.instructions = batch.instructions
    if dry_run:
        print(f"[plan dry-run] one planner; "
              f"model {batch.run.model} ({batch.run.billing}); "
              f"{instructions_note(batch.instructions)}; no agent spawned.")
        return

    print(f"[crustify spawn-planner] workdir: {agent.workdir}")
    print(f"[crustify spawn-planner] model: {batch.run.model} ({batch.run.billing})")
    print(f"[crustify spawn-planner] session: {output / f'{_LOG_STEM}.session.json'}")
    if batch.instructions is not None:
        print("[crustify spawn-planner] additional instructions: "
              f"{batch.instructions.path}")
    batch.run.apply()
    agent.run()
    print("[crustify spawn-planner] run completed.")
