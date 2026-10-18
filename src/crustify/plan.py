"""Execute one orchestrator-written planner batch."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from crustify.translate import check_fields, read_object

#: The planner's two arms. `emit` adds what the plan lacks -- a fresh
#: campaign's artifacts, or the entries a scope change or a new artifact
#: kind calls for -- and leaves the judgements already committed alone;
#: `review` assesses those judgements and corrects them.
OBJECTIVES = ("emit", "review")

#: Both artifacts a planner run writes, named for the role that wrote them.
_LOG_STEM = "planner"


@dataclass(frozen=True)
class PlanBatch:
    """Validated planner-batch input: the one arm this run executes."""

    objective: str


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"plan: {message}")


def load_batch(path: Path) -> PlanBatch:
    """Load and strictly validate a planner batch: exactly ``objective``."""
    raw = read_object(path, _fail)
    check_fields(raw, {"objective"}, set(), _fail)
    if raw["objective"] not in OBJECTIVES:
        _fail(f"objective must be one of {', '.join(OBJECTIVES)}, "
              f"not {raw['objective']!r}")
    return PlanBatch(objective=raw["objective"])


def execute(workdir: Path, batch_path: Path, *, output: Path,
            dry_run: bool = False) -> None:
    """Run exactly one planner in ``workdir``, the campaign checkout on its
    campaign branch. ``output`` is the run's existing artifact dir, which
    holds its ``batch.json`` and receives its log and usage record."""
    batch = load_batch(batch_path)
    output = output.resolve()
    if not output.is_dir():
        _fail(f"--output must name an existing directory: {output}")

    from crustify.agents.plan import PlanAgent

    agent = PlanAgent(workdir.resolve(), objective=batch.objective,
                      artifact_dir=output, log_stem=_LOG_STEM)
    if dry_run:
        print(f"[plan dry-run] one planner; objective {batch.objective}; "
              "no agent spawned.")
        return

    print(f"[crustify spawn-planner] workdir: {agent.workdir}")
    print(f"[crustify spawn-planner] objective: {batch.objective}")
    print(f"[crustify spawn-planner] log: {output / f'{_LOG_STEM}.log'}")
    agent.run()
    print("[crustify spawn-planner] run completed.")
