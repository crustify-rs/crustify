"""One agent's console output and session record. Shared by both tools.

The destination is INJECTED, never inferred: the caller knows which
directory a batch's records belong in, and this class does not need to.

A run leaves one file, ``<stem>.session.json``: which CLI ran, under which
provider and model, its session id, where its transcript was when the run
ended, its exit status and its wall-clock interval. The transcript the CLI
persists is the full log of the run, and its accounting: the assistant
copies it next to the session record, and ``crustify usage`` derives the
usage record from the copy.
"""
from __future__ import annotations
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _iso(epoch: float) -> str:
    """UTC ISO-8601, seconds resolution — sortable and unambiguous."""
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


class AgentLog:
    """Owns one agent's console output and session record for the lifetime of
    its subprocess. Use as a context manager."""

    def __init__(self, log_dir: Path | None, stem: str, *, console: bool,
                 metadata: dict | None = None) -> None:
        self.console = console
        self.metadata = dict(metadata or {})
        self.session_path: Path | None = None
        # Wall clock is OURS to measure: claude's stream carries a duration and
        # codex's carries none. `monotonic` for the span, so a clock step
        # cannot produce a negative duration; wall clock for the stamps.
        self._t0 = time.monotonic()
        self._started = time.time()
        if log_dir is not None:
            # RESOLVED: an isolated agent may reach its log dir through a
            # symlink in the worktree it purges as its last act, and the
            # session record is written after that.
            log_dir = log_dir.resolve()
            log_dir.mkdir(parents=True, exist_ok=True)
            self.session_path = log_dir / f"{stem}.session.json"

    def line(self, text: str) -> None:
        """Show one rendered line of the agent's output on the console."""
        if self.console:
            print(text, flush=True)

    def stderr(self, text: str) -> None:
        """Surface subprocess stderr. Always shown, even with the console off:
        a provider error is the one thing that must not be silent."""
        text = text.rstrip("\n")
        if text:
            print(text, file=sys.stderr, flush=True)

    def session(self, record: dict) -> None:
        """Record this run's session, once, at the end::

            {"cli": "claude",                    # the provider CLI that ran it
             "provider": "anthropic",            # the service that billed it
             "model": "claude-opus-5-5",         # its id with that service
             "session_id": "1adf327a-...",       # the CLI's session id
             "transcript": "/abs/path.jsonl",    # where it was, or null
             "exit_code": 0,
             "agent": "assistant",               # binder, translator, reviewer,
                                                 # planner or assistant
             "started_at": "2026-10-19T19:03:10+00:00",
             "ended_at": "2026-10-19T19:03:56+00:00",
             "duration_ms": 46649}

        ``transcript`` is a hint, valid when the run ended: the CLIs move and
        prune their own files, so the assistant copies it promptly."""
        if self.session_path is not None:
            full = {**record, **self.metadata,
                    "started_at": _iso(self._started),
                    "ended_at": _iso(time.time()),
                    "duration_ms": round((time.monotonic() - self._t0) * 1000)}
            self.session_path.write_text(json.dumps(full, indent=1) + "\n")

    def close(self) -> None:
        pass

    def __enter__(self) -> "AgentLog":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
