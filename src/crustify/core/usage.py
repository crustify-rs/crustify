"""Recover per-request usage from a provider CLI's own session record.

Read from DISK rather than scraped from stdout, for three reasons that are
not robustness hand-waving:

* per REQUEST, not per session. Rates are tiered, so one aggregate record
  for a whole run is priced at a tier no single request reached.
* deduplicated by message id. The transcript repeats records; summing what
  a stream emits double-counts them.
* it survives a lost stdout -- a killed terminal, a truncated pipe, an OOM
  that takes the session but not the container.

This is NOT format-independent: it trades the stream's schema for the
transcript's, which is no more public. It is simply the better of the two,
and it is per-provider -- a codex transcript needs its own reader.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

def claude_config_dir() -> Path:
    """The operator's own Claude Code config dir."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def _read_usage(transcript: Path) -> tuple[list[dict], str]:
    """Extract one usage record per API request from a session transcript.

    Returns ``(requests, model)``. Per-request rather than summed because
    rate tiers key off a single request's context (see
    :meth:`crustify.agentlog.AgentLog.usage`).

    Buckets are exclusive as recorded - the CLI reports ``input_tokens``
    already net of cached reads - and the 5m/1h cache-write split is kept
    because the two bill at different rates. Records are deduplicated by
    message id: the transcript repeats them, and summing naively
    double-counts.
    """
    requests: list[dict] = []
    model = ""
    seen: set[str] = set()
    with open(transcript, errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") != "assistant":
                continue
            msg = e.get("message") or {}
            mid = msg.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            # `<synthetic>` marks a CLI-generated message, not a model that
            # billed anything. Letting it win makes the whole file price as
            # UNKNOWN -- silently dropping a real run from the total.
            named = msg.get("model") or ""
            if named and not named.startswith("<"):
                model = named
            u = msg.get("usage") or {}
            cc = u.get("cache_creation") or {}
            requests.append({
                "model": named if named and not named.startswith("<") else model,
                "input_tokens": int(u.get("input_tokens") or 0),
                "output_tokens": int(u.get("output_tokens") or 0),
                "cache_read_tokens": int(u.get("cache_read_input_tokens") or 0),
                "cache_write_tokens": int(cc.get("ephemeral_5m_input_tokens") or 0),
                "cache_write_1h_tokens": int(cc.get("ephemeral_1h_input_tokens") or 0),
            })
    return requests, model


def read_rollout_usage(rollout: Path) -> list[dict]:
    """One usage record per turn, from the rollout's ``token_count`` events.

    Each event reports both a running ``total_token_usage`` and that turn's
    ``last_token_usage``. The per-turn figure is taken, but only when the
    running total has actually moved: codex re-emits ``token_count``
    without a new request, and counting those would inflate every session.

    Counts are converted to crustify's exclusive buckets - codex's
    ``input_tokens`` includes ``cached_input_tokens``, so cached reads
    would otherwise be billed twice, once at the input rate and once at
    the cache rate.
    """
    requests: list[dict] = []
    prev_total = None
    model = ""
    with open(rollout, errors="replace") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            payload = d.get("payload") or {}
            # Each turn names its model before its requests.
            if d.get("type") == "turn_context" and payload.get("model"):
                model = payload["model"]
            if payload.get("type") != "token_count":
                continue
            info = payload.get("info") or {}
            total = info.get("total_token_usage") or {}
            last = info.get("last_token_usage") or {}
            marker = total.get("total_tokens")
            if marker is None or marker == prev_total:
                continue
            prev_total = marker
            cached = int(last.get("cached_input_tokens") or 0)
            inp = int(last.get("input_tokens") or 0)
            requests.append({
                "model": model,
                "input_tokens": max(inp - cached, 0),
                "output_tokens": int(last.get("output_tokens") or 0),
                "cache_read_tokens": cached,
                "cache_write_tokens": int(last.get("cache_write_input_tokens") or 0),
                "cache_write_1h_tokens": 0,
            })
    return requests


# ---------------------------------------------------------- crustify usage

def transcript_format(path: Path) -> str:
    """``claude`` or ``codex``: which CLI wrote the transcript at ``path``,
    read off its events rather than its name or location."""
    with open(path, errors="replace") as fh:
        for n, line in enumerate(fh):
            if n > 200:
                break
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "session_meta":
                return "codex"
            if "sessionId" in e or e.get("type") in ("assistant", "user"):
                return "claude"
    raise ValueError(f"{path}: not a Claude Code transcript or a Codex rollout")


def transcript_session(path: Path) -> str | None:
    """The session id a transcript names: a Claude Code transcript's
    ``sessionId``, a Codex rollout's ``session_meta`` id."""
    with open(path, errors="replace") as fh:
        for n, line in enumerate(fh):
            if n > 200:
                break
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("type") == "session_meta":
                return (e.get("payload") or {}).get("id")
            if e.get("sessionId"):
                return e["sessionId"]
    return None


def _codex_identity(rollout: Path) -> tuple[str, str]:
    """``(provider, model)`` a rollout records: its session's provider, and
    the model of its last turn."""
    provider = model = ""
    with open(rollout, errors="replace") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            p = e.get("payload") or {}
            if e.get("type") == "session_meta":
                provider = p.get("model_provider") or provider
            elif e.get("type") == "turn_context" and p.get("model"):
                model = p["model"]
    return provider, model


def _interval(path: Path) -> tuple[str | None, str | None, int | None]:
    """First and last event timestamps, and the span between them in ms."""
    from datetime import datetime
    stamps = []
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                ts = json.loads(line).get("timestamp")
            except (ValueError, AttributeError):
                continue
            if isinstance(ts, str):
                try:
                    stamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except ValueError:
                    pass
    if not stamps:
        return None, None, None
    first, last = min(stamps), max(stamps)
    iso = lambda d: d.isoformat(timespec="seconds")  # noqa: E731
    return iso(first), iso(last), round((last - first).total_seconds() * 1000)


def transcript_record(path: Path, *, backend: str | None = None,
                      model_proxy: str | None = None) -> dict:
    """The usage record of one session, from its transcript: one entry per
    API request, in crustify's exclusive buckets, with the session's
    interval and the service whose rates price it.

    That service is the model proxy, when the run went through one: a Claude
    Code transcript reads the same whether its requests went to Anthropic or
    through a gateway. Without one, it is the backend's own service. The
    transcript's format names the backend when ``backend`` does not, and must
    agree with it when it does."""
    from crustify.core.models import NATIVE

    fmt = transcript_format(path)
    if backend is not None and backend != fmt:
        raise ValueError(f"{path} is a {fmt} transcript, not a {backend} one")
    from crustify.core.models import PROXIES

    provider = model_proxy or NATIVE[fmt]
    if fmt == "claude":
        requests, model = _read_usage(path)
    else:
        requests = read_rollout_usage(path)
        seen_provider, model = _codex_identity(path)
        # A rollout names the provider block crustify gave codex, which for a
        # proxy is the proxy's own name.
        if model_proxy is None and seen_provider in PROXIES:
            provider = seen_provider
    started, ended, duration = _interval(path)
    return {"provider": provider, "model": model,
            "requests": requests, "started_at": started, "ended_at": ended,
            "duration_ms": duration}
