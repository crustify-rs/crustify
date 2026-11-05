"""Rates and per-request pricing, shared by both tools.

Rates are FETCHED, never written down here. A constant in this file would go
stale exactly the way a model's recollection does, only slower and with more
authority -- which is how three campaigns published figures 3x too high. An
unknown service or model is left UNPRICED by the caller: never zero, never
guessed, because a plausible wrong number is worse than a missing one.

The rates are fetched whenever a session is priced, and kept as a dated
snapshot in crustify's home when they differ from the latest: the history of
the rates the campaign's figures were computed at.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"
LITELLM_PRICES = ("https://raw.githubusercontent.com/BerriAI/litellm/main/"
                  "model_prices_and_context_window.json")

_TIER_RE = re.compile(r"_above_(\d+)k_tokens$")


def _rate_set(entry: dict) -> dict:
    """One LiteLLM entry -> base rates plus context tiers, in $/token."""
    field = {
        "input_cost_per_token": "input",
        "output_cost_per_token": "output",
        "cache_read_input_token_cost": "cache_read",
        "cache_creation_input_token_cost": "cache_write",
        "cache_creation_input_token_cost_above_1hr": "cache_write_1h",
    }
    base, tiers = {}, {}
    for key, val in entry.items():
        if not isinstance(val, (int, float)):
            continue
        m = _TIER_RE.search(key)
        stem = key[:m.start()] if m else key
        name = field.get(stem)
        if name is None:
            continue
        if m:
            tiers.setdefault(int(m.group(1)) * 1000, {})[name] = float(val)
        else:
            base[name] = float(val)
    return {"base": base, "tiers": sorted(tiers.items())}


def _fetch_openrouter() -> dict:
    with urllib.request.urlopen(OPENROUTER_MODELS, timeout=30) as r:
        data = json.load(r)["data"]
    out = {}
    for m in data:
        p = m.get("pricing") or {}
        base = {}
        for src, name in (("prompt", "input"), ("completion", "output"),
                          ("input_cache_read", "cache_read"),
                          ("input_cache_write", "cache_write")):
            try:
                v = float(p.get(src) or 0.0)
            except (TypeError, ValueError):
                continue
            if v:
                base[name] = v
        if base:
            out[m["id"]] = {"base": base, "tiers": []}
    return out


def _from_litellm(provider: str):
    def fetch():
        with urllib.request.urlopen(LITELLM_PRICES, timeout=60) as r:
            data = json.load(r)
        return {mid: _rate_set(v) for mid, v in data.items()
                if isinstance(v, dict) and v.get("litellm_provider") == provider}
    return fetch


_SOURCES = {
    "openrouter": _fetch_openrouter,
    "openai": _from_litellm("openai"),
    "anthropic": _from_litellm("anthropic"),
}


def rates_dir() -> Path:
    """Where the rate snapshots live: crustify's home, beside the sessions
    they price."""
    from crustify.layout import crustify_home
    return crustify_home() / "rates"


def _stamp(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def latest(directory: Path | None = None) -> tuple[str | None, dict]:
    """The latest rate snapshot: ``(its name, {provider: {model:
    rate_set}})``, or ``(None, {})`` when none is kept."""
    directory = directory or rates_dir()
    paths = sorted(directory.glob("*.json"))
    if not paths:
        return None, {}
    return paths[-1].stem, json.loads(paths[-1].read_text())


def kept(snapshot: str, directory: Path | None = None) -> tuple[str, dict]:
    """A kept snapshot: ``latest``, its name, ``<timestamp>``, or the path of
    its file. Raises ``ValueError`` when there is none such."""
    directory = directory or rates_dir()
    if snapshot == "latest":
        name, rates = latest(directory)
        if name is None:
            raise ValueError(f"no rate snapshot kept in {directory}")
        return name, rates
    path = Path(snapshot)
    if not path.is_file():
        path = directory / f"{snapshot.removesuffix('.json')}.json"
    if not path.is_file():
        raise ValueError(f"no rate snapshot {snapshot} in {directory}")
    return path.stem, json.loads(path.read_text())


def fetch(directory: Path | None = None, now: datetime | None = None
          ) -> tuple[str, dict]:
    """Fetch the current rates, and keep them as a new snapshot when they
    differ from the latest; return ``(the snapshot they match, the rates)``.

    A provider whose fetch fails keeps the rates of the latest snapshot, so
    a failure never reads as a change."""
    directory = directory or rates_dir()
    name, kept = latest(directory)
    current = {}
    for prov, get in _SOURCES.items():
        try:
            current[prov] = get()
        except Exception as exc:
            old = kept.get(prov) or {}
            print(f"warning: could not fetch {prov} prices ({exc}); "
                  + (f"keeping the {len(old)} {prov} rates of the latest snapshot"
                     if old else f"{prov}-billed runs will be unpriced"),
                  file=sys.stderr)
            current[prov] = old
    # Compared as stored, so a tier's tuple and its stored list agree.
    current = json.loads(json.dumps(current))
    if current != kept and any(current.values()):
        when = now or datetime.now(timezone.utc)
        directory.mkdir(parents=True, exist_ok=True)
        # Names sort as their times; two changes within a second keep both.
        while (directory / f"{_stamp(when)}.json").exists():
            when += timedelta(seconds=1)
        name = _stamp(when)
        path = directory / f"{name}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current))
        tmp.replace(path)
    return name, current


def price_request(rate_set: dict, req: dict) -> float:
    """Cost of ONE request, tier chosen by that request's own input context.

    Tiers are per request, so a session must be priced request by request and
    the costs summed. Pricing the summed tokens would push a session of many
    modest requests into a tier none of them ever reached.

    An unpublished cache rate falls back to the full input rate, not to zero:
    assuming a cache read is free understates, and does so silently.
    """
    ctx = (req.get("input_tokens", 0) + req.get("cache_read_tokens", 0)
           + req.get("cache_write_tokens", 0)
           + req.get("cache_write_1h_tokens", 0))
    r = dict(rate_set["base"])
    for threshold, over in rate_set["tiers"]:
        if ctx > threshold:
            r.update(over)
    inp = r.get("input", 0.0)
    return (req.get("input_tokens", 0) * inp
            + req.get("output_tokens", 0) * r.get("output", 0.0)
            + req.get("cache_read_tokens", 0) * r.get("cache_read", inp)
            + req.get("cache_write_tokens", 0) * r.get("cache_write", inp)
            + req.get("cache_write_1h_tokens", 0)
              * r.get("cache_write_1h", r.get("cache_write", inp)))
