from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
import argparse


#: The commands that run one job rather than the assistant. Only these names
#: are read as a command; any other first argument is the assistant's workdir.
SUBCOMMANDS = ("spawn-planner", "spawn-binder", "spawn-translator",
               "spawn-reviewer", "usage")

#: The campaign kinds a settings file can name, and the assistant prompt each
#: one runs: port and wrap are both translation campaigns.
CAMPAIGNS = {"port": "translate", "wrap": "translate", "audit": "audit"}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crustify",
        description="Crustify, your co-translator for C-to-Rust work. "
                    "`crustify [WORKDIR]` opens the assistant; the commands "
                    "below run one job each.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # Options of every command that starts a crustify agent. A parent parser
    # rather than options on `crustify` itself, so they follow the command
    # like any other option: `crustify <workdir> --start --model ...`.
    agent_opts = argparse.ArgumentParser(add_help=False)
    agent_opts.add_argument(
        "--no-console",
        action="store_true",
        default=False,
        help="Suppress live console output from agents.",
    )
    # Model and billing of the commands that start an orchestrator. A spawned
    # agent reads both from its task.json instead, so its batch dir records
    # everything the run depended on.
    model_opts = argparse.ArgumentParser(add_help=False)
    model_opts.add_argument(
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
    model_opts.add_argument(
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

    # -- the assistant: `crustify [WORKDIR]` --------------------------------
    # Not a subcommand: anything that is not one of SUBCOMMANDS opens it.
    assistant = argparse.ArgumentParser(
        prog="crustify", parents=[agent_opts, model_opts],
        description=(
            "Open Crustify, your co-translator, on a checkout. It carries its "
            "workflow in its system prompt, follows the campaign's settings "
            "in crustify/CRUSTIFY.md, and waits for your instructions; "
            "--start runs the campaign right away. Other commands: "
            + ", ".join(SUBCOMMANDS) + " (crustify <command> --help)."),
    )
    assistant.set_defaults(handler=_handle_assist, command="assistant")
    assistant.add_argument(
        "workdir", nargs="?", default=None,
        help="The checkout the campaign works in; its artifacts live under "
             "<workdir>/crustify/. Default: the current directory, or, with "
             "--resume, the checkout of the session it resumes.")
    assistant.add_argument(
        "--campaign", choices=sorted(CAMPAIGNS), default=None,
        help="The campaign, when crustify/CRUSTIFY.md does not exist yet or "
             "leaves it unanswered: Crustify creates the file from the "
             "campaign's template. Asked at the terminal when omitted.")
    assistant.add_argument(
        "--settings", type=Path, metavar="CRUSTIFY_MD", default=None,
        help="A settings file to install as <workdir>/crustify/CRUSTIFY.md, "
             "the copy Crustify reads and you edit mid-campaign. A file that "
             "differs from an existing copy is refused, so resuming never "
             "overwrites your edits.")
    assistant.add_argument(
        "--start", action="store_true",
        help="Start the campaign right away, as CRUSTIFY.md configures it. "
             "Without it Crustify waits for your instructions; a headless "
             "session needs it.")
    assistant.add_argument(
        "--resume", nargs="?", const="", default=None, metavar="SESSION_ID",
        help="Resume an earlier assistant session: the one with that id, from "
             "any directory; without one, the most recent session of WORKDIR, "
             "or of any checkout when WORKDIR is omitted. It continues on the "
             "CLI and model it ran with, unless --model names another model "
             "of the same CLI, under the workflow as it stands now.")
    assistant.add_argument(
        "--task-only", action="store_true",
        help="Ablation control: the settings file is the entire prompt and "
             "the harness contributes nothing -- no conventions, no skill "
             "index, no stage prompt.")

    # -- spawn-planner (one planner run on its planning branch) --------------
    _spawn_planner_blurb = (
        "Run one planner over the campaign checkout. It emits what the plan "
        "-- subsystems.json, each subsystem's schedule.json and the skills' "
        "planning artifacts -- lacks, updates what follows an earlier schema, "
        "corrects what earlier runs decided, filing a report per correction, "
        "and re-emits the schedules its changes move. Runs are sequential; "
        "each commits on its own planning branch.")
    plan_p = sub.add_parser(
        "spawn-planner", parents=[agent_opts],
        help=_spawn_planner_blurb, description=_spawn_planner_blurb,
    )
    plan_p.set_defaults(handler=_handle_spawn_planner)
    add_workdir(plan_p, "the campaign checkout, on the run's planning branch")
    plan_p.add_argument(
        "task", type=Path, metavar="TASK_JSON",
        help="Path to the run's task.json: its model and billing, and "
             "optional additional instructions.")
    plan_p.add_argument(
        "--log-dir", required=True, type=Path, metavar="DIR",
        help="Existing directory for the run's planner.session.json; give "
             "each run its own.")
    plan_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without spawning an agent.")

    # -- spawn-binder / spawn-translator (one agent over one projected batch)
    # A binder runs `wrap` batches; a translator runs `port` batches. Same arguments, so one loop builds both.
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
            "home each item belongs in, and how it runs.")
        p = sub.add_parser(f"spawn-{role}", parents=[agent_opts],
                           help=blurb, description=blurb)
        p.set_defaults(handler=_handle_spawn_worklist, role=role)
        add_workdir(p, "the batch's worktree, forked by the orchestrator")
        p.add_argument(
            "task", type=Path, metavar="TASK_JSON",
            help="Path to the batch's task.json: its objective and items, the "
                 "wave integration branch it lands on, its model and "
                 "billing, and optional additional instructions.")
        p.add_argument(
            "--log-dir", required=True, type=Path, metavar="DIR",
            help=f"Existing directory for the batch's {role}.session.json; "
                 "give each batch its own.")
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
        "task", type=Path, metavar="TASK_JSON",
        help="Path to the batch's task.json: commits or modules, reports, "
             "optional objectives, the review wave integration branch it lands "
             "on, its model and billing, and optional additional "
             "instructions.")
    review_p.add_argument(
        "--log-dir", required=True, type=Path, metavar="DIR",
        help="Existing directory for the batch's reviewer.session.json; give "
             "each batch its own.")
    review_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without spawning an agent.")

    # -- usage (tokens and cost of agent sessions) ----------------------------
    _usage_blurb = (
        "Report the tokens and cost of agent sessions as JSON, from the "
        "transcripts their CLIs kept: a Claude Code session transcript or a "
        "Codex rollout, recognized by its contents. One entry per session, "
        "priced request by request, and a total.")
    usage_p = sub.add_parser("usage", help=_usage_blurb,
                             description=_usage_blurb)
    usage_p.set_defaults(handler=_handle_usage)
    usage_p.add_argument(
        "files", nargs="+", type=Path, metavar="TRANSCRIPT_JSONL",
        help="Paths to session transcripts.")
    usage_p.add_argument(
        "-o", "--output", type=Path, default=None, metavar="FILE",
        help="Write the JSON there instead of to standard output.")
    usage_p.add_argument(
        "--provider", default=None,
        help="The service that billed the sessions, as their session.json "
             "records it. Needed only for a Claude Code session billed through "
             "OpenRouter: by default a Claude Code transcript is priced as "
             "anthropic, and a Codex rollout as the provider it records.")

    argv = sys.argv[1:]
    if argv and argv[0] in SUBCOMMANDS:
        args = parser.parse_args(argv)
    elif argv[:1] in (["-h"], ["--help"]):
        assistant.print_help()
        print()
        parser.print_help()
        return
    else:
        args = assistant.parse_args(argv)

    if getattr(args, "workdir", None) is not None:
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

def _handle_usage(args: argparse.Namespace) -> None:
    """Report the tokens and cost of the sessions named, as JSON."""
    import json
    from crustify.usage import report
    for path in args.files:
        if not path.is_file():
            raise SystemExit(f"no file at {path}")
    try:
        doc = report(args.files, provider=args.provider)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    text = json.dumps(doc, indent=1) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text)


#: Where a campaign's settings live in its checkout. Tracked, and read by the
#: assistant rather than handed to it once, so editing it changes the settings
#: of the subsystems that have not started yet; its git history records the
#: settings each subsystem ran under.
TASK = "crustify/CRUSTIFY.md"

def canonical_task(workdir: Path, given: Path | None) -> Path:
    """Install ``given`` as ``workdir``'s canonical task and return its path.

    Without ``given``, the canonical task must already exist. With it, the
    canonical task is created from it, or must already match it: a resume
    that names the original file must not overwrite the edits made since."""
    task = workdir / TASK
    if given is None:
        if not task.is_file():
            raise SystemExit(f"no campaign settings at {task}; pass --campaign "
                             "or --settings to create them")
        return task
    if not given.is_file():
        raise SystemExit(f"no campaign settings at {given}")
    text = given.read_text()
    if task.is_file() and given.resolve() != task.resolve():
        if task.read_text() != text:
            raise SystemExit(
                f"{task} differs from {given}: edit {task} to change the "
                "campaign's settings, or omit --settings to run it as it is")
        return task
    task.parent.mkdir(parents=True, exist_ok=True)
    if not task.is_file():
        task.write_text(text)
    return task


import re as _re

#: A settings question's answer: the backticked value on the `- Answer:` line
#: that follows the question's `(id: <id>)` tag. `<...>` is unanswered.
def _answer_re(question: str) -> "_re.Pattern[str]":
    return _re.compile(r"\(`id: " + _re.escape(question)
                       + r"`\)(?:.|\n)*?- Answer: `([^`]*)`")


def settings_answer(text: str, question: str) -> str | None:
    """The answer to ``question`` in a settings file, or None when it is
    missing or still its template placeholder."""
    m = _answer_re(question).search(text)
    if m is None or m.group(1).startswith("<"):
        return None
    return m.group(1).strip()


def _set_answer(text: str, question: str, answer: str) -> str:
    m = _answer_re(question).search(text)
    if m is None:
        raise SystemExit(f"the settings have no `{question}` question")
    return text[:m.start(1)] + answer + text[m.end(1):]


def campaign_settings(workdir: Path, given: Path | None, campaign: str | None,
                      ask) -> tuple[Path, str]:
    """``workdir``'s settings file and its campaign, ``port``, ``wrap`` or
    ``audit``.

    ``given`` is installed as the canonical copy, as on every run. A checkout
    with no settings yet gets them from its campaign's template; an
    unanswered campaign is filled in. The campaign comes from the file, then
    ``campaign``, then ``ask()``, which returns None where nobody can answer.
    A ``campaign`` that contradicts the file is refused: the file is what
    the campaign runs under."""
    from crustify import deps

    task = workdir / TASK
    if given is not None:
        task = canonical_task(workdir, given)
    if task.is_file():
        text = task.read_text()
        recorded = settings_answer(text, "campaign")
        if recorded is not None:
            if recorded not in CAMPAIGNS:
                raise SystemExit(f"{task}: campaign must be one of "
                                 f"{', '.join(CAMPAIGNS)}, not {recorded!r}")
            if campaign is not None and campaign != recorded:
                raise SystemExit(
                    f"{task} configures a {recorded} campaign, not {campaign}: "
                    "edit it to change the campaign")
            return task, recorded
    else:
        text = None
    campaign = campaign or ask()
    if campaign not in CAMPAIGNS:
        raise SystemExit("which campaign is this? pass --campaign "
                         + " | ".join(CAMPAIGNS))
    if text is None:
        template = deps.CHECKOUT / "templates" / CAMPAIGNS[campaign] / "CRUSTIFY.template.md"
        text = template.read_text()
        task.parent.mkdir(parents=True, exist_ok=True)
        print(f"[crustify] created {task} from {template.name}")
    elif _answer_re("campaign").search(text) is None:
        # A settings file with no campaign question, such as the bare
        # ablation's: the campaign comes from the command line alone.
        return task, campaign
    task.write_text(_set_answer(text, "campaign", campaign))
    return task, campaign


def _ask_campaign() -> str | None:
    """Ask at the terminal which campaign this is; None without one."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    answer = input("Which campaign is this: port, wrap or audit? ").strip().lower()
    return answer or None


def assistant_session(workdir: Path | None, session_id: str | None) -> dict:
    """The record of an earlier assistant session, from the index in
    crustify's home: the one with ``session_id``, or the most recent one, of
    ``workdir`` when given. The record names the session's workdir."""
    import json
    from crustify.layout import crustify_home
    records = []
    for path in sorted((crustify_home() / "sessions").glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and record.get("session_id") \
                and record.get("workdir"):
            records.append(record)
    if session_id:
        records = [r for r in records if r["session_id"] == session_id]
    if workdir is not None:
        records = [r for r in records if Path(r["workdir"]) == workdir]
    if not records:
        where = f" of {workdir}" if workdir is not None else ""
        raise SystemExit(f"no assistant session {session_id}{where}" if session_id
                         else f"no earlier assistant session{where}")
    return max(records, key=lambda r: r.get("started_at") or "")


def _handle_assist(args: argparse.Namespace) -> None:
    """Start Crustify's assistant on this checkout's campaign."""
    from crustify import config as _cfg
    from crustify.agents.assist import AssistAgent

    given = Path(args.workdir).resolve() if args.workdir else None
    workdir = given or Path(".").resolve()
    model = _cfg.MODEL_OVERRIDE or "anthropic/claude-opus-5"
    resume = None
    if getattr(args, "resume", None) is not None:
        from crustify.core.models import resolve
        record = assistant_session(given, args.resume or None)
        resume = record["session_id"]
        workdir = Path(record["workdir"])
        recorded = f"{record.get('provider')}/{record.get('model')}"
        model = _cfg.MODEL_OVERRIDE or recorded
        cli = "claude_cli" if record.get("cli") == "claude" else "codex_cli"
        try:
            backend = resolve(model).backend
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if backend != cli:
            raise SystemExit(
                f"session {resume} ran on {record.get('cli')}, which {model} "
                "does not: only the CLI that ran a session can resume it")
        print(f"[crustify] resuming session {resume} ({model})")
    # Interactive whenever a person is at the terminal: the assistant waits
    # for instructions and approvals, which a headless run cannot do.
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive and not args.start:
        raise SystemExit("a headless session has nobody to instruct it: pass "
                         "--start to run the campaign as CRUSTIFY.md configures it")
    task, campaign = campaign_settings(workdir, args.settings, args.campaign,
                                       _ask_campaign)
    kind = CAMPAIGNS[campaign]
    run_start = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    # Created here, not by the agent, so the assistant's log and usage
    # record land in it from its first turn.
    artifact_dir = workdir / "crustify" / ARTIFACTS / "assistant"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    print(f"[crustify] {campaign} campaign; artifacts: {artifact_dir}")
    if interactive and not args.start:
        print("[crustify] Crustify is waiting for your instructions.")
    # One log per run, so resuming never overwrites an earlier session's.
    AssistAgent(workdir, kind=kind, task=task, model=model,
                task_only=args.task_only, interactive=interactive,
                start=args.start, resume=resume, artifact_dir=artifact_dir,
                log_stem=f"assistant-{run_start}").run()


def _handle_spawn_planner(args: argparse.Namespace) -> None:
    """Run one planner over the campaign checkout."""
    from crustify.plan import execute
    execute(Path(args.workdir), args.task, log_dir=args.log_dir,
            dry_run=args.dry_run)


def _handle_spawn_worklist(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected batch under its binder or
    translator."""
    from crustify.translate import execute
    execute(Path(args.workdir), args.task, role=args.role,
            log_dir=args.log_dir, dry_run=args.dry_run)


def _handle_spawn_reviewer(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected review batch."""
    from crustify.review import execute
    execute(Path(args.workdir), args.task, log_dir=args.log_dir,
            dry_run=args.dry_run)
