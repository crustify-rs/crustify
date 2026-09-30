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
            "campaign task, plans the sub-campaigns and waves, and spawns the "
            "translators itself."),
        "audit": (
            "Start an audit campaign's orchestrator. It reads the campaign "
            "task and spawns the auditors itself."),
    }
    for kind, blurb in _orch_blurbs.items():
        orch_p = sub.add_parser(kind, parents=[agent_opts],
                                help=blurb, description=blurb)
        orch_p.set_defaults(kind=kind, handler=_handle_orchestrate)
        add_workdir(orch_p, "the checkout the campaign works in; its "
                            "artifacts live under <workdir>/crustify/")
        orch_p.add_argument(
            "task", type=Path, metavar="TASK",
            help="Campaign TASK.md: the campaign's decisions are an input, "
                 "not something the orchestrator interviews for.")
        orch_p.add_argument(
            "--task-only", action="store_true",
            help="Ablation control: the task file is the entire prompt and "
                 "the harness contributes nothing -- no conventions, no skill "
                 "index, no stage prompt.")
        if kind == "translate":
            orch_p.add_argument(
                "--campaign", metavar="ID",
                help="Resume the campaign crustify/campaigns/<ID>/ instead of "
                     "starting a new one. Its directory must exist.")

    # -- spawn-translator (one agent over one orchestrator-projected batch) --
    _spawn_translator_blurb = (
        "Run one translator over one thin batch. The workdir is the isolated "
        "worktree the orchestrator forked for it; the harness neither creates "
        "nor purges that tree. The batch is the whole input: which items, "
        "which objective, and the Rust home each item belongs in.")
    wrap_p = sub.add_parser(
        "spawn-translator", parents=[agent_opts],
        help=_spawn_translator_blurb, description=_spawn_translator_blurb,
    )
    wrap_p.set_defaults(handler=_handle_spawn_translator)
    add_workdir(wrap_p, "the batch's worktree, forked by the orchestrator")
    wrap_p.add_argument(
        "batch", type=Path,
        help="Thin batch JSON containing objective and scheduled items.")
    wrap_p.add_argument(
        "--base-branch", required=True, metavar="BRANCH",
        help="Unchecked-out wave integration branch the batch lands on.")
    wrap_p.add_argument(
        "--output", required=True, type=Path, metavar="DIR",
        help="Existing directory for this batch's artifacts. The agent writes "
             "translator.log and translator.usage.json into it, so give each "
             "batch its own directory.")
    wrap_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without spawning an agent.")

    # -- scan-unsafe / spawn-auditor (the audit stages) -------------------
    # Both work on any repository, crustify campaign or not; the auditor
    # carries its own model and billing options.
    from crustify_audit.cli import add_stages as _add_audit_stages
    _add_audit_stages(
        sub, unsafe_name="scan-unsafe", ub_name="spawn-auditor",
        before=lambda p: (
            p.set_defaults(handler=_handle_audit_stage),
            add_workdir(p, "the repository to audit"),
        ),
    )

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
        # A translator works inside a campaign the orchestrator set up; an
        # orchestrator may be the first thing to run in a checkout, and the
        # audit stages take any repository.
        if args.command == "spawn-translator" \
                and not (workdir / "crustify").is_dir():
            print(f"error: no crustify/ under workdir: {workdir}",
                  file=sys.stderr)
            sys.exit(1)

    # -- Apply the agent options ------------------------------------------
    from crustify import config as crustify_config

    if getattr(args, "no_console", False):
        crustify_config.LOG_TO_CONSOLE = False
    if getattr(args, "model", None) and args.command != "spawn-auditor":
        crustify_config.MODEL_OVERRIDE = args.model
    if getattr(args, "billing", None) and args.command != "spawn-auditor":
        crustify_config.BILLING = args.billing
    if getattr(args, "override_base_prompt", None) is not None:
        crustify_config.OVERRIDE_BASE_PROMPT = args.override_base_prompt

    args.handler(args)


# -- dispatch -------------------------------------------------------------

def _handle_cost(args: argparse.Namespace) -> None:
    """Report agent cost and wall time for the usage records given."""
    from crustify.log_cost import report

    raise SystemExit(report(args.usage, offline=args.offline,
                            price_cache=args.price_cache))


def _handle_audit_stage(args: argparse.Namespace) -> None:
    """Run one audit stage against this repository."""
    from crustify_audit.cli import dispatch
    from crustify_audit.layout import Layout as AuditLayout

    raise SystemExit(dispatch(AuditLayout(Path(args.workdir)), args,
                              args.audit_stage))


def _handle_orchestrate(args: argparse.Namespace) -> None:
    """Spawn the campaign orchestrator for this checkout."""
    from crustify import config as _cfg
    from crustify.agents.orchestrate import OrchestrateAgent

    if not args.task.is_file():
        raise SystemExit(f"no campaign task at {args.task}")
    model = _cfg.MODEL_OVERRIDE or "anthropic/claude-opus-5"
    workdir = Path(args.workdir).resolve()
    campaigns = workdir / "crustify" / "campaigns"
    run_start = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    campaign = {}
    if getattr(args, "campaign", None) is not None:
        campaign_dir = campaigns / args.campaign
        if Path(args.campaign).name != args.campaign or not campaign_dir.is_dir():
            raise SystemExit(f"no campaign to resume at {campaign_dir}")
        campaign_id = args.campaign
    elif args.kind == "translate":
        # A new campaign is named by when it started. Minted here, not by the
        # agent, so the orchestrator's log and usage record land in the
        # campaign directory from its first turn.
        campaign_id = run_start
        campaign_dir = campaigns / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=False)
    if args.kind == "translate":
        print(f"[crustify translate] campaign: {campaign_dir}")
        # One log per run, so resuming never overwrites an earlier session's.
        campaign = {"campaign_id": campaign_id, "artifact_dir": campaign_dir,
                    "log_stem": f"orchestrator-{run_start}"}
    # Interactive whenever a person is at the terminal: the orchestrator asks
    # for approval and waits, which a headless run cannot do.
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    OrchestrateAgent(workdir, kind=args.kind, task=args.task, model=model,
                     task_only=args.task_only, interactive=interactive,
                     **campaign).run()


def _handle_spawn_translator(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected batch."""
    from crustify.translate import execute
    execute(Path(args.workdir), args.batch, base_branch=args.base_branch,
            output=args.output, dry_run=args.dry_run)
