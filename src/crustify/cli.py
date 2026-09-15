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
    # -- crates (read-only crates.json interface) ------------------------
    _crates_blurb = (
        "Read-only access to the authored crates.json placement oracle. "
        "Locate C symbols/types in Rust modules or validate placement "
        "consistency; never writes Rust or Cargo files.")
    crates_p = sub.add_parser(
        "crates", help=_crates_blurb, description=_crates_blurb,
    )
    crates_sub = crates_p.add_subparsers(dest="crates_command", required=True)

    locate_p = crates_sub.add_parser(
        "locate",
        help="Resolve crates.json entries to their Rust .rs paths.",
        description="Resolve crates.json entries to their Rust .rs paths "
                    "without modifying the tree.",
    )
    # `--file` lives outside the group because it is both a standalone
    # selection and a qualifier for an ambiguous `--name`.
    locate_sel = locate_p.add_mutually_exclusive_group()
    locate_sel.add_argument(
        "--all", action="store_true",
        help="Print every Rust module path recorded in crates.json.",
    )
    locate_sel.add_argument(
        "--dir", default=None, metavar="DIR",
        help="Print homes reached by C files under DIR, relative to the target.",
    )
    locate_sel.add_argument(
        "--name", nargs="+", action="extend", default=None, metavar="NAME",
        help="Locate these type tags and/or symbol names. A name with several "
             "homes is refused unless --file disambiguates it.",
    )
    locate_p.add_argument(
        "--file", default=None, metavar="FILE",
        help="Locate entries reached by this C file, or qualify --name by its "
             "defining translation unit/header.",
    )

    crates_sub.add_parser(
        "validate",
        help="Validate the crates.json manifest.",
        description="Check manifest uniqueness, dependency validity/cycles, "
                    "and module-path collisions. Rust-tree validity belongs "
                    "to the compiler.",
    )

    # -- translate ---------------------------------------------------------
    _translate_blurb = (
        "Execute one orchestrator-projected translation batch. The harness "
        "forks one isolated worktree from the unchecked-out base branch, "
        "inserts that batch's TODO anchors and starts one translator. The "
        "translator lands atomically on the base branch and prunes its own "
        "successful worktree.")
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

    if args.command == "crates":
        _handle_crates(args, target)

    elif args.command == "translate":
        _handle_translate(args, target)



# -- analyze dispatch -----------------------------------------------------

# -- crates dispatch ------------------------------------------------------

def _handle_crates(args: argparse.Namespace, target: Path) -> None:
    from crustify import crates

    if args.crates_command == "locate":
        crates.locate(target, all=args.all, dir=args.dir, file=args.file,
                      name=args.name)
    elif args.crates_command == "validate":
        crates.validate_command(target)


def _handle_translate(args: argparse.Namespace, target: Path) -> None:
    """Execute one orchestrator-projected batch."""
    from crustify.translate import execute
    execute(target, args.batch, base_branch=args.base_branch,
            output=args.output, dry_run=args.dry_run)
