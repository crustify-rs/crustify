from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
import argparse


#: The commands that run one job rather than the assistant. Only these names
#: are read as a command; any other first argument is the assistant's workdir.
SUBCOMMANDS = ("spawn-planner", "spawn-binder", "spawn-translator",
               "spawn-reviewer", "usage")

#: The campaign kinds a settings file can name, and the part of the assistant's
#: prompt each one loads, `prompts/assistant/<kind>.md`: port and wrap are both
#: translation campaigns.
CAMPAIGNS = {"port": "translate", "wrap": "translate", "audit": "audit"}


#: How options reach the provider CLI, in every command's help.
_FORWARDED = ("Options after `--` are passed unchanged to the provider CLI "
              "(claude or codex) of every agent the command runs, after "
              "crustify's own: crustify spawn-binder ... -- --effort high.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crustify",
        description="Crustify, your co-translator for C-to-Rust work. "
                    "`crustify [WORKDIR]` opens the assistant; the commands "
                    "below run one job each.",
        epilog=_FORWARDED,
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
    # How the commands that start an assistant run its CLI. A spawned agent
    # reads the same from its task.json instead, so its run dir records
    # everything the run depended on.
    model_opts = argparse.ArgumentParser(add_help=False)
    model_opts.add_argument(
        "--backend",
        default=None,
        choices=["claude", "codex"],
        help="The provider CLI to run: claude (Claude Code) or codex. It runs "
             "its own default model; name another after `--`, in the CLI's own "
             "syntax: -- --model opus, or -- -m gpt-6-sol. Default: claude, or, "
             "with --resume, the session's.",
    )
    model_opts.add_argument(
        "--billing",
        default=None,
        choices=["subscription", "api"],
        help="How the CLI authenticates: subscription (its own logged-in "
             "account) or api (an API key from the environment). Default: "
             "subscription, or, with --resume, the session's.",
    )
    model_opts.add_argument(
        "--model-proxy",
        default=None,
        metavar="PROXY",
        help="Send the CLI's requests through a gateway, with its key: "
             "openrouter (OPENROUTER_API_KEY). Needs --billing api. Default: "
             "none, or, with --resume, the session's.",
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
        epilog=_FORWARDED,
    )
    assistant.set_defaults(handler=_handle_assist, command="assistant")
    assistant.add_argument(
        "workdir", nargs="?", default=None,
        help="Where the session starts. When it holds crustify/CRUSTIFY.md, it "
             "is the campaign's repository, whose artifacts live under "
             "<workdir>/crustify/; otherwise Crustify establishes the repository "
             "with you and writes its crustify/CRUSTIFY.md when the work starts. "
             "Default: the current directory, or, with --resume, the directory "
             "of the session it resumes. The session's own records live in "
             "crustify's home, under sessions/<id>/.")
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
             "overwrites your edits. Before the repository is established, "
             "Crustify writes it there; a headless session needs it then.")
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
             "the harness contributes nothing -- no specs, no tool specs, "
             "no stage prompt.")

    # -- spawn-planner (one planner run on its planner branch) ---------------
    _spawn_planner_blurb = (
        "Run one planner over the campaign checkout. It emits what the plan "
        "-- modules.json, the waves of schedule.json and the tools' "
        "planning artifacts -- lacks, updates what follows an earlier schema, "
        "corrects what earlier runs decided, filing a report per correction, "
        "and re-plans the waves its changes move that have not started. Runs "
        "are sequential; each commits on its own planner branch.")
    plan_p = sub.add_parser(
        "spawn-planner", parents=[agent_opts],
        help=_spawn_planner_blurb, description=_spawn_planner_blurb,
        epilog=_FORWARDED,
    )
    plan_p.set_defaults(handler=_handle_spawn_planner)
    add_workdir(plan_p, "the campaign checkout, on the run's planner branch")
    plan_p.add_argument(
        "task", type=Path, metavar="TASK_JSON",
        help="Path to the run's task.json: its run fields, and "
             "optional additional instructions.")
    # Accepted and ignored: session records are filed in crustify's home.
    plan_p.add_argument(
        "--log-dir", type=Path, default=None, help=argparse.SUPPRESS)
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
                           help=blurb, description=blurb, epilog=_FORWARDED)
        p.set_defaults(handler=_handle_spawn_worklist, role=role)
        add_workdir(p, "the batch's worktree, forked by the orchestrator")
        p.add_argument(
            "task", type=Path, metavar="TASK_JSON",
            help="Path to the batch's task.json: its objective and items, its "
                 "wave and batch indices, link unit and module, the wave "
                 "integration branch it lands on, its run fields, and "
                 "optional additional instructions.")
        # Accepted and ignored: session records are filed in crustify's home.
        p.add_argument(
            "--log-dir", type=Path, default=None, help=argparse.SUPPRESS)
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
        "without them, every objective the reviewer's prompt and tools offer "
        "that applies to the batch runs.")
    review_p = sub.add_parser(
        "spawn-reviewer", parents=[agent_opts],
        help=_spawn_reviewer_blurb, description=_spawn_reviewer_blurb,
        epilog=_FORWARDED,
    )
    review_p.set_defaults(handler=_handle_spawn_reviewer)
    add_workdir(review_p, "the batch's worktree, forked by the orchestrator")
    review_p.add_argument(
        "task", type=Path, metavar="TASK_JSON",
        help="Path to the batch's task.json: commits or paths, reports, "
             "optional objectives, its wave and batch indices, link unit and "
             "module, the review wave integration branch it lands on, its "
             "run fields, and optional additional instructions.")
    # Accepted and ignored: session records are filed in crustify's home.
    review_p.add_argument(
        "--log-dir", type=Path, default=None, help=argparse.SUPPRESS)
    review_p.add_argument(
        "--dry-run", action="store_true",
        help="Validate and summarize the batch without spawning an agent.")

    # -- usage (tokens and cost of agent sessions) ----------------------------
    _usage_blurb = (
        "Report the tokens and cost of one agent session as JSON, from the "
        "transcript its CLI kept: a Claude Code session transcript or a Codex "
        "rollout, recognized by its contents, and priced request by request, "
        "as the session's record in crustify's home says it ran. A session is "
        "priced at the rate snapshot its record names; one priced for the "
        "first time, at the rates fetched now, kept as a dated snapshot when "
        "they changed, which its record then names.")
    usage_p = sub.add_parser("usage", help=_usage_blurb,
                             description=_usage_blurb)
    usage_p.set_defaults(handler=_handle_usage)
    usage_p.add_argument(
        "session_id", metavar="SESSION_ID",
        help="The session's id, as its task.json or session record names it.")
    usage_p.add_argument(
        "transcript", type=Path, metavar="TRANSCRIPT_JSONL",
        help="Path to the session's transcript.")
    usage_p.add_argument(
        "-o", "--output", type=Path, default=None, metavar="FILE",
        help="Write the JSON there instead of to standard output.")
    usage_p.add_argument(
        "--rates", default=None, metavar="SNAPSHOT",
        help="Price at this kept rate snapshot instead of the one the "
             "session's record names: its timestamp, its file, or `latest`. "
             "The record then names it.")
    usage_p.add_argument(
        "--backend", default=None, choices=["claude", "codex"],
        help="For a session crustify keeps no record of: the CLI that ran it. "
             "Default: read off the transcript.")
    usage_p.add_argument(
        "--model-proxy", default=None, metavar="PROXY",
        help="For a session crustify keeps no record of: the model proxy it "
             "ran through, whose rates price it.")

    argv = sys.argv[1:]
    # Everything after `--` is the provider CLI's, not crustify's.
    provider_args: list[str] = []
    if "--" in argv:
        cut = argv.index("--")
        argv, provider_args = argv[:cut], argv[cut + 1:]
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
    if getattr(args, "backend", None):
        crustify_config.BACKEND = args.backend
    if getattr(args, "billing", None):
        crustify_config.BILLING = args.billing
    if getattr(args, "model_proxy", None):
        crustify_config.MODEL_PROXY = args.model_proxy
    if getattr(args, "override_base_prompt", None) is not None:
        crustify_config.OVERRIDE_BASE_PROMPT = args.override_base_prompt
    crustify_config.PROVIDER_ARGS = provider_args

    args.handler(args)


#: Where a campaign's artifact tree lives, under `<workdir>/crustify/`. A
#: repository holds one campaign, whose work is cumulative, so the tree is not
#: keyed by any campaign id: a later run resumes it.


# -- dispatch -------------------------------------------------------------

def _handle_usage(args: argparse.Namespace) -> None:
    """Report the tokens and cost of one session, as JSON."""
    import json
    from crustify.usage import price_session
    if not args.transcript.is_file():
        raise SystemExit(f"no file at {args.transcript}")
    try:
        doc = price_session(args.session_id, args.transcript, snapshot=args.rates,
                            backend=args.backend, model_proxy=args.model_proxy)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    text = json.dumps(doc, indent=1) + "\n"
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text)


#: Where a campaign's settings live in its checkout. Tracked, and read by the
#: assistant rather than handed to it once, so editing it changes the settings
#: of the modules that have not started yet; its git history records the
#: settings each module ran under.
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
    """The settings file of ``workdir``, a campaign's checkout, and its
    campaign, ``port``, ``wrap`` or ``audit``.

    ``given`` must match the checkout's copy, so that a resume naming the
    original file overwrites no edit made since. An unanswered campaign is
    filled in, from ``campaign``, then ``ask()``, which returns None where
    nobody can answer. A ``campaign`` that contradicts the file is refused:
    the file is what the campaign runs under."""
    task = canonical_task(workdir, given)
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
    campaign = campaign or ask()
    if campaign not in CAMPAIGNS:
        raise SystemExit("which campaign is this? pass --campaign "
                         + " | ".join(CAMPAIGNS))
    if _answer_re("campaign").search(text) is None:
        # A settings file with no campaign question, such as the bare
        # ablation's: the campaign comes from the command line alone.
        return task, campaign
    task.write_text(_set_answer(text, "campaign", campaign))
    return task, campaign


def detached_settings(given: Path | None, campaign: str | None,
                      ask) -> tuple[Path, str]:
    """The settings of a session whose repository is not established yet,
    and its campaign.

    Nothing is written: the settings are ``given``, or the campaign's
    template, which the assistant writes as ``<repo>/crustify/CRUSTIFY.md``
    once the user and it have established the repository. The campaign
    comes from the file, then ``campaign``, then ``ask()``."""
    from crustify import deps
    recorded = None
    if given is not None:
        if not given.is_file():
            raise SystemExit(f"no campaign settings at {given}")
        recorded = settings_answer(given.read_text(), "campaign")
        if recorded is not None and campaign is not None and campaign != recorded:
            raise SystemExit(f"{given} configures a {recorded} campaign, "
                             f"not {campaign}: edit it to change the campaign")
    campaign = recorded or campaign or ask()
    if campaign not in CAMPAIGNS:
        raise SystemExit("which campaign is this? pass --campaign "
                         + " | ".join(CAMPAIGNS))
    if given is not None:
        return given.resolve(), campaign
    return (deps.CHECKOUT / "templates" / CAMPAIGNS[campaign]
            / "CRUSTIFY.template.md"), campaign


def _ask_campaign() -> str | None:
    """Ask at the terminal which campaign this is; None without one."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    answer = input("Which campaign is this: port, wrap or audit? ").strip().lower()
    return answer or None


#: Where a session's directory in crustify's home records the checkout the
#: assistant created, when it started without one.
SESSION_WORKDIR = "workdir"


def assistant_session(workdir: Path | None, session_id: str | None) -> dict:
    """The record of an earlier assistant session, from the index in
    crustify's home: the one with ``session_id``, by its CLI's id or its
    directory's, or the most recent one, of ``workdir`` when given, the
    checkout or the directory it ran in.

    Each session's directory, ``sessions/<id>/``, holds its ``index.json``,
    which names the directory the CLI ran in (``cwd``), the checkout
    (``workdir``), and the directory itself (``dir``). A checkout the
    assistant created after starting is in the directory's ``workdir`` file.
    The flat ``sessions/<id>.json`` of earlier versions are read too."""
    import json
    from crustify.layout import crustify_home
    sessions = crustify_home() / "sessions"
    records = []
    for path in sorted([*sessions.glob("*/index.json"), *sessions.glob("*.json")]):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not (isinstance(record, dict) and record.get("session_id")):
            continue
        created = path.parent / SESSION_WORKDIR
        if path.name == "index.json" and created.is_file():
            record["workdir"] = created.read_text().strip() or record.get("workdir")
        record.setdefault("cwd", record.get("workdir"))
        if record.get("cwd"):
            records.append(record)
    if session_id:
        records = [r for r in records
                   if session_id in (r["session_id"], Path(r.get("dir") or "").name)]
    if workdir is not None:
        records = [r for r in records
                   if workdir in {Path(p) for p in (r.get("workdir"), r["cwd"]) if p}]
    if not records:
        where = f" of {workdir}" if workdir is not None else ""
        raise SystemExit(f"no assistant session {session_id}{where}" if session_id
                         else f"no earlier assistant session{where}")
    return max(records, key=lambda r: r.get("started_at") or "")


def _handle_assist(args: argparse.Namespace) -> None:
    """Start Crustify's assistant on this checkout's campaign."""
    from crustify import config as _cfg
    from crustify.agents.assist import AssistAgent

    import uuid
    from crustify.layout import crustify_home

    given = Path(args.workdir).resolve() if args.workdir else None
    # Where the CLI runs: the directory the session starts in. It is the
    # campaign's repository when it holds the campaign's settings; otherwise
    # crustify writes nothing there, and the assistant establishes the
    # repository with the user.
    workdir = given or Path(".").resolve()
    checkout = workdir if (workdir / TASK).is_file() else None
    resume = None
    session_id = str(uuid.uuid4())
    session_dir = crustify_home() / "sessions" / session_id
    if getattr(args, "resume", None) is not None:
        record = assistant_session(given, args.resume or None)
        resume = record["session_id"]
        workdir = Path(record["cwd"])
        checkout = Path(record["workdir"]) if record.get("workdir") else None
        session_dir = Path(record.get("dir") or crustify_home() / "sessions" / resume)
        _resume_run(args, record, _cfg)
        print(f"[crustify] resuming session {resume} ({_cfg.BACKEND}, "
              f"{_cfg.BILLING}{', via ' + _cfg.MODEL_PROXY if _cfg.MODEL_PROXY else ''})")
    # Interactive whenever a person is at the terminal: the assistant waits
    # for instructions and approvals, which a headless run cannot do.
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive and not args.start:
        raise SystemExit("a headless session has nobody to instruct it: pass "
                         "--start to run the campaign as CRUSTIFY.md configures it")
    if checkout is not None:
        task, campaign = campaign_settings(checkout, args.settings, args.campaign,
                                           _ask_campaign)
    else:
        if not interactive and args.settings is None:
            raise SystemExit(
                f"{workdir} holds no {TASK}, and a headless session has nobody to "
                "establish its repository with: pass --settings with its source")
        task, campaign = detached_settings(args.settings, args.campaign,
                                           _ask_campaign)
    kind = CAMPAIGNS[campaign]
    run_start = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    # Created here, not by the agent, so the assistant's log and usage
    # record land in it from its first turn: the session's own directory in
    # crustify's home, never the checkout, which it may not have yet.
    session_dir.mkdir(parents=True, exist_ok=True)
    print(f"[crustify] {campaign} campaign; session: {session_dir}")
    print(f"[crustify] checkout: {checkout or 'none yet'}")
    if interactive and not args.start:
        print("[crustify] Crustify is waiting for your instructions.")
    # One record per run, so resuming never overwrites an earlier one.
    AssistAgent(workdir, kind=kind, task=task,
                task_only=args.task_only, interactive=interactive,
                start=args.start, resume=resume, checkout=checkout,
                session_id=None if resume else session_id,
                artifact_dir=session_dir,
                log_stem=f"assistant-{run_start}").run()


def _resume_run(args: argparse.Namespace, record: dict, cfg) -> None:
    """Run a resumed session as its record says, but for what the command
    line gives again: its backend, which must be the one that ran it, its
    billing and model proxy, and its arguments, which those after `--`
    replace. A record of an earlier version names a ``cli``, ``provider``
    and ``model`` instead."""
    from crustify.core.models import from_model
    if "backend" in record:
        backend, billing = record["backend"], record.get("billing", "subscription")
        proxy, recorded_args = record.get("model_proxy"), record.get("args") or []
    else:
        try:
            r = from_model(f"{record.get('provider')}/{record.get('model')}",
                           "subscription")
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        backend, billing, proxy, recorded_args = (
            record.get("cli") or r.backend, r.billing, r.model_proxy, list(r.args))
    if args.backend and args.backend != backend:
        raise SystemExit(f"session {record['session_id']} ran on {backend}: only "
                         "the CLI that ran a session can resume it")
    cfg.BACKEND = backend
    cfg.BILLING = args.billing or billing
    cfg.MODEL_PROXY = args.model_proxy or proxy
    cfg.PROVIDER_ARGS = cfg.PROVIDER_ARGS or list(recorded_args)


def _handle_spawn_planner(args: argparse.Namespace) -> None:
    """Run one planner over the campaign checkout."""
    from crustify.plan import execute
    execute(Path(args.workdir), args.task, dry_run=args.dry_run)


def _handle_spawn_worklist(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected batch under its binder or
    translator."""
    from crustify.translate import execute
    execute(Path(args.workdir), args.task, role=args.role,
            dry_run=args.dry_run)


def _handle_spawn_reviewer(args: argparse.Namespace) -> None:
    """Execute one orchestrator-projected review batch."""
    from crustify.review import execute
    execute(Path(args.workdir), args.task, dry_run=args.dry_run)
