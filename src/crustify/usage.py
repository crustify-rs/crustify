"""`crustify usage`: tokens and cost of agent sessions, as JSON.

Each input is a session's transcript, the file its CLI kept: a Claude Code
session transcript or a Codex rollout, told apart by its contents. Every
session is priced request by
request and the costs summed, never the reverse: rate tiers key off a single
request's context, so pricing the summed tokens would charge a session of
many modest requests at a tier none of them reached.

Rates are per service, so a model is priced only with the service that
billed it, the session's model proxy or its backend's own service: OpenRouter's live catalogue for ``openrouter``, LiteLLM's table for
``openai`` and ``anthropic`` (see :mod:`crustify.core.pricing`). A model or
service the tables do not know is reported with ``cost_usd: null``, never a
guessed zero. The rates are fetched on every run, and kept as a dated
snapshot in crustify's home when they changed; the report names the snapshot
its costs were computed at. Provider-reported dollars are not used:
under subscription billing they are an API-equivalent figure, as this one is.
"""
from __future__ import annotations

import json
from pathlib import Path

from crustify.core.pricing import fetch, kept, price_request
from crustify.core.usage import transcript_record

#: Token buckets, all exclusive of one another.
BUCKETS = ("input_tokens", "output_tokens", "cache_read_tokens",
           "cache_write_tokens", "cache_write_1h_tokens")


def _session(record: dict, source: Path, rates: dict) -> dict:
    """One session, with its token totals and its cost."""
    requests = [r for r in record.get("requests") or [] if isinstance(r, dict)]
    tokens = {b: sum(int(r.get(b, 0)) for r in requests) for b in BUCKETS}
    table = rates.get(record.get("provider") or "") or {}
    cost, unpriced = 0.0, 0
    for r in requests:
        rate_set = table.get(r.get("model") or record.get("model") or "")
        if rate_set is None:
            unpriced += 1
        else:
            cost += price_request(rate_set, r)
    out = {k: record.get(k) for k in ("provider", "model", "started_at",
                                      "ended_at", "duration_ms")}
    return {"source": str(source), **out,
            "request_count": len(requests), "tokens": tokens,
            "cost_usd": None if unpriced or not requests else round(cost, 6),
            "requests": requests}


def report(paths: list[Path], *, backend: str | None = None,
           model_proxy: str | None = None, snapshot: str | None = None,
           rates: Path | None = None) -> dict:
    """``{"rates": ..., "sessions": [...], "total": {...}}`` for the
    transcripts named, in order, each run on ``backend`` through
    ``model_proxy``, as its session record says. The current rates are
    fetched and kept as a new snapshot when they changed, unless
    ``snapshot`` names a kept one to price at instead, which reproduces the
    costs a report that named it gave."""
    records = [(transcript_record(p, backend=backend, model_proxy=model_proxy), p)
               for p in paths]
    snapshot, table = kept(snapshot, rates) if snapshot else fetch(rates)
    sessions = [_session(r, p, table) for r, p in records]
    total_tokens = {b: sum(s["tokens"][b] for s in sessions) for b in BUCKETS}
    priced = [s["cost_usd"] for s in sessions if s["cost_usd"] is not None]
    durations = [s["duration_ms"] for s in sessions
                 if isinstance(s.get("duration_ms"), int)]
    total = {"sessions": len(sessions),
             "request_count": sum(s["request_count"] for s in sessions),
             "tokens": total_tokens,
             "cost_usd": round(sum(priced), 6),
             "unpriced_sessions": len(sessions) - len(priced),
             "duration_ms": sum(durations)}
    # The snapshot the costs were computed at, in crustify's home.
    return {"rates": snapshot, "sessions": sessions, "total": total}


def session_record(session_id: str, home: Path | None = None) -> Path | None:
    """The newest record crustify keeps of the session ``session_id``, in
    its directory in crustify's home: a spawned agent's one, or the last of
    an assistant session's, which a resume adds to."""
    from crustify.layout import crustify_home
    sessions = (home or crustify_home()) / "sessions"
    hits = []
    for path in sessions.glob("*/*.session.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and record.get("session_id") == session_id:
            hits.append(path)
    return max(hits, key=lambda p: (p.parent.name, p.name)) if hits else None


def price_session(session_id: str, transcript: Path, *,
                  snapshot: str | None = None, backend: str | None = None,
                  model_proxy: str | None = None,
                  rates: Path | None = None, home: Path | None = None) -> dict:
    """The report of one session, from its transcript, run as its session
    record says, priced at the rate snapshot the record names.

    A session priced for the first time is priced at the rates fetched now,
    and its record names the snapshot they match; ``snapshot`` prices it at
    another kept one, which its record then names. A session crustify keeps
    no record of, such as one of an earlier version's, takes its backend
    and model proxy from the arguments, and is priced as ``snapshot`` says,
    with nothing recorded."""
    from crustify.core.models import PROXIES
    from crustify.core.usage import transcript_session

    named = transcript_session(transcript)
    if named is not None and named != session_id:
        raise ValueError(f"{transcript} is the transcript of session {named}, "
                         f"not {session_id}")
    path = session_record(session_id, home)
    record = json.loads(path.read_text()) if path else {}
    if "backend" not in record and "cli" in record:
        # An earlier version's record: its CLI, and its billing service.
        record.setdefault("backend", record["cli"])
        if record.get("provider") in PROXIES:
            record.setdefault("model_proxy", record["provider"])
    doc = report([transcript], backend=backend or record.get("backend"),
                 model_proxy=model_proxy or record.get("model_proxy"),
                 snapshot=snapshot or record.get("rates"), rates=rates)
    if path is not None and doc["rates"] and doc["rates"] != record.get("rates"):
        kept = json.loads(path.read_text())
        kept["rates"] = doc["rates"]
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(kept, indent=1) + "\n")
        tmp.replace(path)
    return {"session_id": session_id, **doc}
