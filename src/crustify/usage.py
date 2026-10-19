"""`crustify usage`: tokens and cost of agent sessions, as JSON.

Each input is a session's transcript, the file its CLI kept: a Claude Code
session transcript or a Codex rollout, told apart by its contents. Every
session is priced request by
request and the costs summed, never the reverse: rate tiers key off a single
request's context, so pricing the summed tokens would charge a session of
many modest requests at a tier none of them reached.

Rates are per service, so a model is priced only with the service that
billed it: OpenRouter's live catalogue for ``openrouter``, LiteLLM's table for
``openai`` and ``anthropic`` (see :mod:`crustify.core.pricing`). A model or
service the tables do not know is reported with ``cost_usd: null``, never a
guessed zero. The rates are cached, and fetched again when a session names
a model the cache does not know. Provider-reported dollars are not used:
under subscription billing they are an API-equivalent figure, as this one is.
"""
from __future__ import annotations

import json
from pathlib import Path

from crustify.core.pricing import load_prices, price_request
from crustify.core.usage import transcript_record

#: Token buckets, all exclusive of one another.
BUCKETS = ("input_tokens", "output_tokens", "cache_read_tokens",
           "cache_write_tokens", "cache_write_1h_tokens")


def _session(record: dict, source: Path, prices: dict) -> dict:
    """One session, with its token totals and its cost."""
    requests = [r for r in record.get("requests") or [] if isinstance(r, dict)]
    tokens = {b: sum(int(r.get(b, 0)) for r in requests) for b in BUCKETS}
    rate_set = (prices.get(record.get("provider") or "") or {}).get(
        record.get("model") or "")
    cost = (None if rate_set is None
            else round(sum(price_request(rate_set, r) for r in requests), 6))
    out = {k: record.get(k) for k in ("provider", "model", "started_at",
                                      "ended_at", "duration_ms")}
    return {"source": str(source), **out,
            "request_count": len(requests), "tokens": tokens,
            "cost_usd": cost, "requests": requests}


def report(paths: list[Path], *, provider: str | None = None) -> dict:
    """``{"sessions": [...], "total": {...}}`` for the transcripts named, in
    order."""
    records = [(transcript_record(p, provider=provider), p) for p in paths]
    prices = load_prices()
    if any(((prices.get(r["provider"] or "") or {}).get(r["model"] or "")) is None
           for r, _ in records):
        prices = load_prices(refresh=True)
    sessions = [_session(r, p, prices) for r, p in records]
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
    return {"sessions": sessions, "total": total}
