from __future__ import annotations

import sys
from pathlib import Path
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crustify",
        description="Multi-agent C-to-Rust translation pipeline.",
    )
    parser.add_argument(
        "workdir",
        help="Full path to the checkout this run works in; its artifacts live "
             "under <workdir>/crustify/. An isolated agent's workdir is its "
             "own worktree, which is why this is not called a repository "
             "root. Required and explicit — crustify never walks the "
             "filesystem to find it.",
    )
    parser.add_argument(
        "target",
        help="Repo-relative oracle target id recorded in the schedule "
             "(e.g. ssl/statem). Use . for the repo root.",
    )
    parser.add_argument(
        "--no-console",
        action="store_true",
        default=False,
        help="Suppress live console output from agents.",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="NAME",
        help="Override every agent's model. Named <provider>/<model>, "
             "e.g. anthropic/claude-opus-4-8, openai/gpt-5.6, "
             "openrouter/anthropic/claude-opus-5. The provider selects "
             "billing; an OpenRouter anthropic/* model uses Claude Code, "
             "while other OpenRouter models use Codex. Default: each agent's "
             "hard-coded model.",
    )
    parser.add_argument(
        "--billing",
        default=None,
        choices=["subscription", "api"],
        help="How the provider CLI authenticates: subscription (its own "
             "logged-in account) or api (an API key from the environment). "
             "Default: config.BILLING.",
    )
    parser.add_argument(
        "--override-base-prompt",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Replace the provider CLI's own base prompt with crustify's. "
             "Default is --no-override-base-prompt: the provider's own "
             "instructions stay underneath crustify's stage prompt. Replacing "
             "them is cheaper per invocation but measurably worse output.",
    )
    sub = parser.add_subparsers(dest="command", required=True)


    # Each stage binds ONE blurb and passes it to both `help=` (which renders in
    # the parent's subcommand listing) and `description=` (which renders on the
    # stage's own --help). Without the second, `crustify … <stage> --help`
    # prints a usage line and a flag list and never says what the stage does.
    # -- cost (accounting over the usage records) ------------------------
    _cost_blurb = (
        "Price the per-agent usage.json records named on the command line. "
        "It reads the files it is given and assumes nothing about where they "
        "live: a caller that knows which batch it is asking about says so, "
        "and one that wants a wave passes the wave's records.")
    cost_p = sub.add_parser(
        "cost", help=_cost_blurb, description=_cost_blurb,
    )
    cost_p.add_argument(
        "usage", nargs="+", type=Path, metavar="USAGE_JSON",
        help="One or more per-agent .usage.json records.")
    from crustify.log_cost import add_flags as _add_cost_flags
    _add_cost_flags(cost_p)

    # -- audit (the safety passes, formerly a second entry point) --------
    _audit_blurb = (
        "Find soundness bugs and safety trade-offs in Rust that wraps C. "
        "`unsafe` is deterministic and needs no model, no key and no network; "
        "`ub` drives an agent over its output and costs money.")
    audit_p = sub.add_parser(
        "audit", help=_audit_blurb, description=_audit_blurb,
    )
    from crustify_audit.cli import add_stages as _add_audit_stages
    _add_audit_stages(audit_p.add_subparsers(dest="audit_command", required=True))

    # -- orchestrate (spawn the campaign supervisor) ---------------------
    _orch_blurb = (
        "Start a campaign orchestrator. It reads the campaign task, plans the "
        "sub-campaigns and waves, and spawns the stage agents itself. The "
        "kind selects which orchestrator prompt it runs under; there is no "
        "default, because a wrong guess starts the wrong campaign and spends "
        "a budget before anyone reads the transcript.")
    orch_p = sub.add_parser(
        "orchestrate", help=_orch_blurb, description=_orch_blurb,
    )
    orch_p.add_argument(
        "kind", choices=["translate", "audit"],
        help="Which campaign to supervise.")
    orch_p.add_argument(
        "--task-only", action="store_true",
        help="Ablation control: the task file is the entire prompt and the "
             "harness contributes nothing -- no conventions, no skill index, "
             "no stage prompt.")
    orch_p.add_argument(
        "--task", required=True, type=Path, metavar="PATH",
        help="Campaign TASK.md. Required: the campaign's decisions are an "
             "input, not something the orchestrator interviews for.")

    # -- translate (one agent over one orchestrator-projected batch) -----
    _translate_blurb = (
        "Translate one thin batch in an isolated worktree. It creates the "
        "branch, runs exactly one agent over the batch's items, and lands the "
        "result on the wave's integration branch. The batch is the whole "
        "input: which items, which objective, and the Rust home each item "
        "belongs in.")
    wrap_p = sub.add_parser(
        "translate", help=_translate_blurb, description=_translate_blurb,
    )
    wrap_p.add_argument(
        "batch", type=Path,
        help="Thin batch JSON containing objective and scheduled items.")
    wrap_p.add_argument(
        "--base-branch", required=True, metavar="BRANCH",
        help="Unchecked-out wave integration branch to fork from and land on.")
    wrap_p.add_argument(
        "--output", required=True, type=Path, metavar="DIR",
        help="Existing directory for harness-generated batch log and usage files.")
    wrap_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without creating a worktree or "
             "spawning an agent.")

    args = parser.parse_args()

    # workdir is explicit (no marker-walking); target is repo-relative.
    from crustify.layout import set_workdir
    workdir = Path(args.workdir).resolve()
    set_workdir(workdir)
    target_rel = (args.target or "").strip("/")
    target = workdir if target_rel in ("", ".") else (workdir / target_rel)
    target = target.resolve()
    args._target_path = str(target)

    if not workdir.exists():
        print(f"error: workdir does not exist: {workdir}", file=sys.stderr)
        sys.exit(1)
    if not (workdir / "crustify").is_dir():
        print(f"error: no crustify/ under workdir: {workdir}", file=sys.stderr)
        sys.exit(1)
    if not target.exists():
        print(f"error: target does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    # -- Apply logging flags ----------------------------------------------
    from crustify import config as crustify_config

    if args.no_console:
        crustify_config.LOG_TO_CONSOLE = False
    if getattr(args, "model", None):
        crustify_config.MODEL_OVERRIDE = args.model
    if getattr(args, "billing", None):
        crustify_config.BILLING = args.billing
    if getattr(args, "override_base_prompt", None) is not None:
        crustify_config.OVERRIDE_BASE_PROMPT = args.override_base_prompt

    if args.command == "translate":
        _handle_translate(args, target)

    elif args.command == "orchestrate":
        _handle_orchestrate(args, target)

    elif args.command == "audit":
        _handle_audit(args)

    elif args.command == "cost":
        _handle_cost(args)



# -- analyze dispatch -----------------------------------------------------

def _handle_cost(args: argparse.Namespace) -> None:
    """Report agent cost and wall time for this checkout."""
    from crustify.log_cost import report

    raise SystemExit(report(args.usage, offline=args.offline,
                            price_cache=args.price_cache))


def _handle_audit(args: argparse.Namespace) -> None:
    """Run one audit stage against this checkout."""
    from crustify_audit.cli import dispatch
    from crustify_audit.layout import Layout as AuditLayout

    raise SystemExit(dispatch(AuditLayout(Path(args.workdir)), args,
                              args.audit_command))


def _handle_orchestrate(args: argparse.Namespace, target: Path) -> None:
    """Spawn the campaign orchestrator for this checkout."""
    from crustify import config as _cfg
    from crustify.agents.orchestrate import OrchestrateAgent

    if not args.task.is_file():
        raise SystemExit(f"no campaign task at {args.task}")
    model = _cfg.MODEL_OVERRIDE or "anthropic/claude-opus-5"
    OrchestrateAgent(target, kind=args.kind, task=args.task, model=model,
                     task_only=args.task_only,
                     workdir=Path(args.workdir)).run()


def _handle_translate(args: argparse.Namespace, target: Path) -> None:
    """Execute one orchestrator-projected batch."""
    from crustify.translate import execute
    execute(target, args.batch, base_branch=args.base_branch,
            output=args.output, dry_run=args.dry_run)
