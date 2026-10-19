"""Execute one orchestrator-written planner task."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from crustify.translate import (RUN_FIELDS, RunSettings, check_fields, parse_run, read_object,
                                task_and_log_dir)

#: The planner's two arms. `emit` adds what the plan lacks -- a fresh
#: campaign's artifacts, or the entries a scope change or a new artifact
#: kind calls for -- and leaves the judgements already committed alone;
#: `review` assesses those judgements and corrects them.
OBJECTIVES = ("emit", "review")

#: Both artifacts a planner run writes, named for the role that wrote them.
_LOG_STEM = "planner"


@dataclass(frozen=True)
class PlanBatch:
    """Validated planner task: the one arm this run executes, and how."""

    objective: str
    run: RunSettings


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"plan: {message}")


def load_batch(path: Path) -> PlanBatch:
    """Load and strictly validate a planner task: ``objective``, ``model``
    and ``billing``. A planner commits on the checked-out campaign branch, so
    it lands on no other."""
    raw = read_object(path, _fail)
    check_fields(raw, {"objective"} | RUN_FIELDS, set(), _fail)
    if raw["objective"] not in OBJECTIVES:
        _fail(f"objective must be one of {', '.join(OBJECTIVES)}, "
              f"not {raw['objective']!r}")
    return PlanBatch(objective=raw["objective"], run=parse_run(raw, _fail))


def execute(workdir: Path, task_path: Path, *, log_dir: Path,
            dry_run: bool = False) -> None:
    """Run exactly one planner in ``workdir``, the campaign checkout on its
    campaign branch. ``log_dir`` is the existing directory that receives
    the run's log and usage record."""
    task_path, output = task_and_log_dir(task_path, log_dir, _fail)
    batch = load_batch(task_path)

    from crustify.agents.plan import PlanAgent

    agent = PlanAgent(workdir.resolve(), objective=batch.objective,
                      artifact_dir=output, log_stem=_LOG_STEM)
    if dry_run:
        print(f"[plan dry-run] one planner; objective {batch.objective}; "
              f"model {batch.run.model} ({batch.run.billing}); no agent spawned.")
        return

    print(f"[crustify spawn-planner] workdir: {agent.workdir}")
    print(f"[crustify spawn-planner] objective: {batch.objective}")
    print(f"[crustify spawn-planner] model: {batch.run.model} ({batch.run.billing})")
    print(f"[crustify spawn-planner] session: {output / f'{_LOG_STEM}.session.json'}")
    batch.run.apply()
    agent.run()
    print("[crustify spawn-planner] run completed.")
