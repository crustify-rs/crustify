#!/usr/bin/env python3
"""Launch one Crustify stage run as a Claude Code process of its own.

Claude Code refuses a subagent's writes of report files ("Subagents should return
findings as text, not write report files"), and every stage files reports: a reviewer's
findings, a planner's plan corrections. A stage run therefore runs as the main agent of a
headless session, `claude -p --agent crustify:<stage>`, which no such guard reaches.

    spawn.py <stage> <worktree> <run dir> [--model M] [--effort E]
             [--permission-mode P] [--add-dir D ...] [-- <claude args>...]

The task message is `<run dir>/task.md`, given on stdin; the session runs in `<worktree>`.
The script writes, in the run dir:

- `session_id`, the session's id, before the session starts: the run's `session_id`;
- `stream.jsonl`, the session's `stream-json` output, and `stderr.log`;
- `exit_code`, once the session ends.

It then copies the session's transcript, and its subagents' if any, into Crustify's home,
`$CRUSTIFY_HOME/transcripts/<session id>.jsonl`, as `transcripts.py` does for a subagent.
It exits with the session's status. Run it in the background, one per run.

Standard library only: it runs under whatever Python the host has.
"""
import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = ("planner", "binder", "translator", "reviewer")


def _config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def _copy_transcripts(session: str) -> list[Path]:
    """Copy the session's transcript, and its subagents', into Crustify's home."""
    home = Path(os.environ.get("CRUSTIFY_HOME") or Path.home() / ".crustify")
    dest = home / "transcripts"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in (_config_dir() / "projects").glob(f"*/{session}.jsonl"):
        shutil.copyfile(src, dest / f"{session}.jsonl")
        copied.append(dest / f"{session}.jsonl")
        for sub in (src.parent / session / "subagents").glob("*.jsonl"):
            shutil.copyfile(sub, dest / sub.name)
            copied.append(dest / sub.name)
    return copied


def main(argv: list[str]) -> int:
    rest = []
    if "--" in argv:
        i = argv.index("--")
        argv, rest = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("stage", choices=STAGES)
    p.add_argument("worktree", type=Path)
    p.add_argument("run_dir", type=Path)
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--add-dir", action="append", default=[])
    a = p.parse_args(argv)

    run_dir = a.run_dir.resolve()
    task = run_dir / "task.md"
    if not task.is_file():
        print(f"spawn.py: no task message at {task}", file=sys.stderr)
        return 2
    if not a.worktree.is_dir():
        print(f"spawn.py: no worktree at {a.worktree}", file=sys.stderr)
        return 2

    session = str(uuid.uuid4())
    (run_dir / "session_id").write_text(session + "\n")
    (run_dir / "exit_code").unlink(missing_ok=True)
    cmd = ["claude", "-p", "--plugin-dir", str(ROOT), "--agent", f"crustify:{a.stage}",
           "--session-id", session, "--permission-mode", a.permission_mode,
           "--output-format", "stream-json", "--verbose"]
    if a.model:
        cmd += ["--model", a.model]
    if a.effort:
        cmd += ["--effort", a.effort]
    for d in a.add_dir:
        cmd += ["--add-dir", d]
    cmd += rest

    with task.open("rb") as stdin, \
            (run_dir / "stream.jsonl").open("wb") as out, \
            (run_dir / "stderr.log").open("wb") as err:
        status = subprocess.run(cmd, cwd=a.worktree, stdin=stdin, stdout=out,
                                stderr=err).returncode
    (run_dir / "exit_code").write_text(f"{status}\n")
    if not _copy_transcripts(session):
        print(f"spawn.py: no transcript found for session {session}", file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
