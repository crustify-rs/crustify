from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crustify",
        description="Multi-agent C-to-Rust translation pipeline.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # Options of every command that starts a crustify agent. A parent parser
    # rather than options on `crustify` itself, so they follow the command
    # like any other option: `crustify translate <wd> <TASK> --model ...`.
    agent_opts = argparse.ArgumentParser(add_help=False)
    agent_opts.add_argument(
        "--no-console",
        action="store_true",
        default=False,
        help="Suppress live console output from agents.",
    )
    agent_opts.add_argument(
        "--model",
        default=None,
        metavar="NAME",
        help="Override the agent's model. Named <provider>/<model>, "
             "e.g. anthropic/claude-opus-4-8, openai/gpt-5.6, "
             "openrouter/anthropic/claude-opus-5. The provider selects "
             "billing; an OpenRouter anthropic/* model uses Claude Code, "
             "while other OpenRouter models use Codex. Default: the agent's "
             "hard-coded model.",
    )
    agent_opts.add_argument(
        "--billing",
        default=None,
        choices=["subscription", "api"],
        help="How the provider CLI authenticates: subscription (its own "
             "logged-in account) or api (an API key from the environment). "
             "Default: config.BILLING.",
    )
    agent_opts.add_argument(
        "--override-base-prompt",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Replace the provider CLI's own base prompt with crustify's. "
             "Default is --no-override-base-prompt: the provider's own "
             "instructions stay underneath crustify's stage prompt. Replacing "
             "them is cheaper per invocation but measurably worse output.",
    )

    def add_workdir(p: argparse.ArgumentParser, what: str) -> None:
        p.add_argument(
            "workdir",
            help=f"Full path to {what}. Required and explicit — crustify "
                 "never walks the filesystem to find it.",
        )

    # Each command binds ONE blurb and passes it to both `help=` (which renders
    # in `crustify --help`) and `description=` (which renders on the command's
    # own --help). Without the second, `crustify <command> --help` prints a
    # usage line and a flag list and never says what the command does.

    # -- translate / audit (campaign orchestrators) ----------------------
    # One command per campaign kind, so the name says which orchestrator
    # prompt runs; a wrong guess would start the wrong campaign and spend a
    # budget before anyone reads the transcript.
    _orch_blurbs = {
        "translate": (
            "Start a translation campaign's orchestrator. It reads the "
            "campaign task, sets the campaign up, spawns the planners that "
            "decompose and schedule it, and spawns the binders, translators "
            "and reviewers that execute the schedule."),
        "audit": (
            "Start an audit campaign's orchestrator. It reads the campaign "
            "task and spawns the reviewers itself."),
    }
    for kind, blurb in _orch_blurbs.items():
        orch_p = sub.add_parser(kind, parents=[agent_opts],
                                help=blurb, description=blurb)
        orch_p.set_defaults(kind=kind, handler=_handle_orchestrate)
        add_workdir(orch_p, "the checkout the campaign works in; its "
                            "artifacts live under <workdir>/crustify/")
        orch_p.add_argument(
            "task", type=Path, metavar="TASK", nargs="?",
            help="Campaign TASK.md, copied to <workdir>/crustify/TASK.md, "
                 "the canonical copy the orchestrator reads and you edit to "
                 "change settings mid-campaign. Omit it once that copy "
                 "exists; a TASK that differs from it is refused, so "
                 "resuming never overwrites your edits.")
        orch_p.add_argument(
            "--task-only", action="store_true",
            help="Ablation control: the task file is the entire prompt and "
                 "the harness contributes nothing -- no conventions, no skill "
                 "index, no stage prompt.")

    # -- spawn-planner (one planner run on the campaign branch) --------------
    _spawn_planner_blurb = (
        "Run one planner over the campaign checkout. It decomposes the "
        "campaign into subsystems and schedules it: with no plan committed it "
        "creates subsystems.json, schedule.json and the skills' planning "
        "artifacts; otherwise it reviews and amends the committed plan. Runs "
        "are sequential; each commits on the campaign branch.")
    plan_p = sub.add_parser(
        "spawn-planner", parents=[agent_opts],
        help=_spawn_planner_blurb, description=_spawn_planner_blurb,
    )
    plan_p.set_defaults(handler=_handle_spawn_planner)
    add_workdir(plan_p, "the campaign checkout, on its campaign branch")
    plan_p.add_argument(
        "--output", required=True, type=Path, metavar="DIR",
        help="Directory for this run's artifacts, created if absent. The "
             "agent writes planner.log and planner.usage.json into it, so "
             "give each run its own directory.")

    # -- spawn-binder / spawn-translator (one agent over one projected batch)
    # A binder runs `wrap` batches, raw-lifetime ones included; a translator
    # runs `port` batches. Same arguments, so one loop builds both.
    for role, objective, does in (
            ("binder", "wrap", "binds them: keeps the C implementation and "
             "puts a safe Rust API in front of it"),
            ("translator", "port", "ports them: reimplements them in safe "
             "Rust")):
        blurb = (
            f"Run one {role} over one thin `{objective}` batch, which {does}. "
            "The workdir is the isolated worktree the orchestrator forked for "
            "it; the harness neither creates nor purges that tree. The batch "
            "is the whole input: which items, their objective, and the Rust "
            "home each item belongs in.")
        p = sub.add_parser(f"spawn-{role}", parents=[agent_opts],
                           help=blurb, description=blurb)
        p.set_defaults(handler=_handle_spawn_worklist, role=role)
        add_workdir(p, "the batch's worktree, forked by the orchestrator")
        p.add_argument(
            "batch", type=Path,
            help="Thin batch JSON containing objective and scheduled items.")
        p.add_argument(
            "--base-branch", required=True, metavar="BRANCH",
            help="Unchecked-out wave integration branch the batch lands on.")
        p.add_argument(
            "--output", required=True, type=Path, metavar="DIR",
            help=f"Existing directory for this batch's artifacts. The agent "
                 f"writes {role}.log and {role}.usage.json into it, so give "
                 "each batch its own directory.")
        p.add_argument(
            "--dry-run", action="store_true",
            help="Validate and summarize the batch without spawning an agent.")

    # -- spawn-reviewer (one agent over one orchestrator-projected review batch)
    _spawn_reviewer_blurb = (
        "Run one reviewer over one review batch. The workdir is the isolated "
        "worktree the orchestrator forked for it; the harness neither creates "
        "nor purges that tree. The batch carries the commits a wave's "
        "translation batches landed, or the modules of a crate to audit, the "
        "reports to revisit, and, optionally, the objectives to review for; "
        "without them, every objective the reviewer's prompt and skills offer "
        "that applies to the batch runs.")
    review_p = sub.add_parser(
        "spawn-reviewer", parents=[agent_opts],
        help=_spawn_reviewer_blurb, description=_spawn_reviewer_blurb,
    )
    review_p.set_defaults(handler=_handle_spawn_reviewer)
    add_workdir(review_p, "the batch's worktree, forked by the orchestrator")
    review_p.add_argument(
        "batch", type=Path,
        help="Review batch JSON containing commits or modules, reports, and "
             "optional objectives.")
    review_p.add_argument(
        "--base-branch", required=True, metavar="BRANCH",
        help="Unchecked-out review wave integration branch the batch lands on.")
    review_p.add_argument(
        "--output", required=True, type=Path, metavar="DIR",
        help="Existing directory for this batch's artifacts. The agent writes "
             "reviewer.log and reviewer.usage.json into it, so give each "
             "batch its own directory.")
    review_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without spawning an agent.")

    # -- cost (accounting over the usage records) ------------------------
    _cost_blurb = (
        "Price the per-agent usage.json records named on the command line. "
        "It reads the files it is given and assumes nothing about where they "
        "live: a caller that knows which batch it is asking about says so, "
        "and one that wants a wave passes the wave's records.")
    cost_p = sub.add_parser(
        "cost", help=_cost_blurb, description=_cost_blurb,
    )
    cost_p.set_defaults(handler=_handle_cost)
    cost_p.add_argument(
        "usage", nargs="+", type=Path, metavar="USAGE_JSON",
        help="One or more per-agent .usage.json records.")
    from crustify.log_cost import add_flags as _add_cost_flags
    _add_cost_flags(cost_p)

    args = parser.parse_args()

    if hasattr(args, "workdir"):
        # workdir is explicit: crustify never walks the filesystem to find it.
        workdir = Path(args.workdir).resolve()
        if not workdir.exists():
            print(f"error: workdir does not exist: {workdir}", file=sys.stderr)
            sys.exit(1)
        # A binder, translator or reviewer works inside a campaign the
        # orchestrator set up; an orchestrator may be the first thing to run
        # in a checkout.
        if args.command in ("spawn-binder", "spawn-translator",
                            "spawn-reviewer", "spawn-planner") \
                and not (workdir / "crustify").is_dir():
            print(f"error: no crustify/ under workdir: {workdir}",
                  file=sys.stderr)
            sys.exit(1)

    # -- Apply the agent options ------------------------------------------
    from crustify import config as crustify_config

    if getattr(args, "no_console", False):
        crustify_config.LOG_TO_CONSOLE = False
    if getattr(args, "model", None):
        crustify_config.MODEL_OVERRIDE = args.model
    if getattr(args, "billing", None):
        crustify_config.BILLING = args.billing
    if getattr(args, "override_base_prompt", None) is not None:
        crustify_config.OVERRIDE_BASE_PROMPT = args.override_base_prompt

    args.handler(args)


#: Where a campaign's artifact tree lives, under `<workdir>/crustify/`. A
#: repository holds one campaign, whose work is cumulative, so the tree is not
#: keyed by any campaign id: a later run resumes it.
ARTIFACTS = "artifacts"


# -- dispatch -------------------------------------------------------------

def _handle_cost(args: argparse.Namespace) -> None:
    """Report agent cost and wall time for the usage records given."""
    from crustify.log_cost import report

    raise SystemExit(report(args.usage, offline=args.offline,
                            price_cache=args.price_cache))


#: Where a campaign's task lives in its checkout. Tracked, and read by the
#: orchestrator rather than handed to it once, so editing it changes the
#: settings of the subsystems that have not started yet.
TASK = "crustify/TASK.md"


def canonical_task(workdir: Path, given: Path | None) -> Path:
    """Install ``given`` as ``workdir``'s canonical task and return its path.

    Without ``given``, the canonical task must already exist. With it, the
    canonical task is created from it, or must already match it: a resume
    that names the original file must not overwrite the edits made since."""
    task = workdir / TASK
    if given is None:
        if not task.is_file():
            raise SystemExit(f"no campaign task at {task}; pass one to start")
        return task
    if not given.is_file():
        raise SystemExit(f"no campaign task at {given}")
    text = given.read_text()
    if task.is_file() and given.resolve() != task.resolve():
        if task.read_text() != text:
            raise SystemExit(
                f"{task} differs from {given}: edit {task} to change the "
                "campaign's settings, or omit TASK to run it as it is")
        return task
    task.parent.mkdir(parents=True, exist_ok=True)
    if not task.is_file():
        task.write_text(text)
    return task


def _handle_orchestrate(args: argparse.Namespace) -> None:
    """Spawn the campaign orchestrator for this checkout."""
    from crustify import config as _cfg
    from crustify.agents.orchestrate import OrchestrateAgent

    model = _cfg.MODEL_OVERRIDE or "anthropic/claude-opus-5"
    workdir = Path(args.workdir).resolve()
    task = canonical_task(workdir, args.task)
    run_start = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    # Created here, not by the agent, so the orchestrator's log and usage
    # record land in it from its first turn.
    artifact_dir = workdir / "crustify" / ARTIFACTS
    artifact_dir.mkdir(parents=True, exist_ok=True)
    print(f"[crustify {args.kind}] artifacts: {artifact_dir}")
    # Interactive whenever a person is at the terminal: the orchestrator asks
    # for approval and waits, which a headless run cannot do.
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    # One log per run, so resuming never overwrites an earlier session's.
    OrchestrateAgent(workdir, kind=args.kind, task=task, model=model,
                     task_only=args.task_only, interactive=interactive,
                     artifact_dir=artifact_dir,
                     log_stem=f"orchestrator-{run_start}").run()


def _handle_spawn_planner(args: argparse.Namespace) -> None:
    """Run one planner over the campaign checkout."""
    from crustify.agents.plan import PlanAgent

    workdir = Path(args.workdir).resolve()
    output = args.output if args.output.is_absolute() else workdir / args.output
    output.mkdir(parents=True, exist_ok=True)
    print(f"[crustify spawn-planner] log: {output / 'planner.log'}")
    PlanAgent(workdir, artifact_dir=output, log_stem="planner").run()


def _handle_spawn_worklist(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected batch under its binder or
    translator."""
    from crustify.translate import execute
    execute(Path(args.workdir), args.batch, role=args.role,
            base_branch=args.base_branch, output=args.output,
            dry_run=args.dry_run)


def _handle_spawn_reviewer(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected review batch."""
    from crustify.review import execute
    execute(Path(args.workdir), args.batch, base_branch=args.base_branch,
            output=args.output, dry_run=args.dry_run)
