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
                 metadata: dict | None = None,
                 index_path: Path | None = None,
                 index_facts: dict | None = None) -> None:
        self.console = console
        #: Where a copy of the record goes, so the session can be found from
        #: anywhere (the assistant's: `--resume`), with what only that copy
        #: needs, such as the directory the session runs in.
        self.index_path = index_path
        self.index_facts = dict(index_facts or {})
        self.metadata = dict(metadata or {})
        self.session_path: Path | None = None
        self.stem = stem
        # Wall clock is OURS to measure: claude's stream carries a duration and
        # codex's carries none. `monotonic` for the span, so a clock step
        # cannot produce a negative duration; wall clock for the stamps.
        self._t0 = time.monotonic()
        self._started = time.time()
        if log_dir is not None:
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

            {"backend": "claude",                # the provider CLI that ran it
             "billing": "subscription",          # how it authenticated
             "model_proxy": null,                # the gateway it went through
             "args": ["--model", "opus"],        # the CLI's own arguments
             "session_id": "1adf327a-...",       # the CLI's session id
             "exit_code": 0,
             "resumed": false,
             "agent": "binder",                  # binder, translator, reviewer,
                                                 # planner or assistant
             "started_at": "2026-10-19T19:03:10+00:00",
             "ended_at": "2026-10-19T19:03:56+00:00",
             "duration_ms": 46649}

        Without a directory of its own, the record goes to the session's
        directory in crustify's home, named by its session id."""
        if self.session_path is None and record.get("session_id"):
            from crustify.layout import crustify_home
            d = crustify_home() / "sessions" / record["session_id"]
            d.mkdir(parents=True, exist_ok=True)
            self.session_path = d / f"{self.stem}.session.json"
        if self.session_path is not None:
            full = {**record, **self.metadata,
                    "started_at": _iso(self._started),
                    "ended_at": _iso(time.time()),
                    "duration_ms": round((time.monotonic() - self._t0) * 1000)}
            self.session_path.write_text(json.dumps(full, indent=1) + "\n")
            if self.index_path is not None and full.get("session_id"):
                self.index_path.parent.mkdir(parents=True, exist_ok=True)
                self.index_path.write_text(
                    json.dumps({**full, **self.index_facts,
                                "record": str(self.session_path)},
                               indent=1) + "\n")

    def close(self) -> None:
        pass

    def __enter__(self) -> "AgentLog":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
