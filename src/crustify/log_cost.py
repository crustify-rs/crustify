#!/usr/bin/env python3
"""Cost + wall-clock analysis of crustify agent logs.

Reads the per-agent ``<batch-id>.usage.json`` files written by
:mod:`crustify.agentlog`: a crustify-shaped record of one agent run,
holding its per-request token counts. Each agent is its own process, so
its file covers exactly one invocation and the numbers never interleave,
even with concurrent agents. (The sibling ``<batch-id>.log`` is the provider
CLI's own human output; nothing here parses it.)

Every provider is priced the same way, from per-request counts the backend
recovers from the CLI's session transcript. Provider-reported dollars are
deliberately unused even where available (claude's ``total_cost_usd``):
under subscription auth that figure is the API-equivalent price rather
than the billed one, so mixing it with computed figures would make runs
incomparable across providers.

Rates are per-service, so a model id is only priceable together with the
service that billed it, and each service is read from its own
authoritative source:

  ``openrouter``  OpenRouter's live catalogue (``/api/v1/models``).
  ``openai``      LiteLLM's community price table. OpenAI publishes rates
                  as a docs page, not a machine-readable endpoint -
                  ``/v1/models`` carries no pricing - so there is nothing
                  first-party to query.

Cross-sourcing the two is an error rather than a shortcut: LiteLLM's
OpenRouter entries lag the live catalogue and omit models outright, while
OpenRouter cannot speak for what OpenAI charges to bill a run directly.
A model priced from the wrong service's table yields a plausible wrong
number, which is worse than none — so an unrecognised service or model is
counted and reported under ``no-price`` instead.

Both tables are fetched once and cached to ``--price-cache``.

Two views:
  * per agent KIND  (port / wrap / merge / setup) — kind from
    the usage record's stage (or historical log filename prefix); wall-clock =
    the record's ``duration_ms``,
    counted under ``no-wall`` when the record predates that stamp.
  * per WAVE        — the campaign's ``<sub-campaign>/wave-<index>/logs``
    directories; cost split by agent kind. Historical session directories are
    still mapped to their following wave commit.

Usage:  crustify <workdir> <target> cost USAGE_JSON... [--offline]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

from crustify.layout import Layout

from crustify.core.pricing import (  # noqa: F401 - re-exported
    DEFAULT_PRICE_CACHE,
    LITELLM_PRICES,
    OPENROUTER_MODELS,
    load_prices,
    price_usage,
)


# ------------------------------------------------------------- log parsing

def parse_usage(path, prices):
    """(cost_usd, tokens, model) for one agent, or None if the file is
    missing or malformed (agent died before reporting).

    Prices request by request and sums the costs — never the reverse. Tier
    thresholds apply to a single request's context, so a session of many
    modest requests must not be charged as one large one.

    ``cost_usd`` is None when the service or model is unknown to the price
    tables — distinct from 0.0, which means free.
    """
    return price_usage(path, prices)


def kind(stage):
    for p, k in (# `translate` records <objective>-<unit>_<key>, so the
                 # bucket is the pair — which is the point: it prices wrap-type
                 # against port-type directly, the calibration question a first
                 # port wave exists to answer. Longest prefixes first.
                 ("wrap-type", "wrap-type"), ("wrap-symbol", "wrap-symbol"),
                 ("port-type", "port-type"), ("port-symbol", "port-symbol"),
                 ("review-type", "review-type"),
                 ("review-symbol", "review-symbol"),
                 ("wrap-raw-lifetime", "wrap-raw-lifetime"),
                 ("review-raw-lifetime", "review-raw-lifetime"),
                 # Historical pre-`translate` log prefixes remain bucketed so
                 # existing campaign measurements stay readable.
                 ("port_", "port"), ("wrap_", "wrap"), ("merge", "merge"),
                 # Historical setup-agent prefixes share one compatibility
                 # bucket so old campaign measurements remain readable.
                 ("scaffolder", "setup"),
                 ("type_analyzer", "setup"),
                 ("symbol_analyzer", "setup"), ("buffer", "setup"),
                 ("bindgen", "setup")):
        if stage.startswith(p):
            return k
    return "other"


def usage_stage(path: str) -> str:
    """Return the recorded stage, falling back to a historical filename."""
    try:
        with open(path, errors="replace") as fh:
            stage = json.load(fh).get("stage")
    except (OSError, ValueError, AttributeError):
        stage = None
    return stage if isinstance(stage, str) and stage else os.path.basename(path)


def stat(path, fmt):  # %W birth, %Y mtime
    out = subprocess.run(["stat", "-f" if sys.platform == "darwin" else "-c",
                          fmt, path], capture_output=True, text=True).stdout
    try:
        return int(out.strip())
    except ValueError:
        return 0


def wall_seconds(usage_path):
    """This agent's wall clock in seconds, or ``None`` when unrecorded.

    ``duration_ms`` is stamped by :mod:`crustify.agentlog` around the
    subprocess. Records written before that stamp existed carry no timing and
    return ``None`` -- counted as unmeasured rather than folded in as zero,
    which would understate every total silently. (This column read ``0h00m``
    for every run in exactly that way: it used to derive the span from this
    file's own birth -> mtime, but ``usage.json`` is written once at the end,
    so the two are the same instant.)
    """
    try:
        with open(usage_path, errors="replace") as fh:
            ms = json.load(fh).get("duration_ms")
    except (OSError, ValueError, AttributeError):
        return None
    return ms / 1000.0 if isinstance(ms, (int, float)) and ms >= 0 else None


def hm(s):
    s = int(s)
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


# ------------------------------------------------------------------- views

def add_flags(parser: argparse.ArgumentParser) -> None:
    """The flags this report takes, wherever it is reached from."""
    parser.add_argument("--offline", action="store_true",
                        help="Never fetch OpenRouter prices; use the cache only.")
    parser.add_argument("--price-cache", default=DEFAULT_PRICE_CACHE)


def report(paths, *, offline: bool = False,
           price_cache: str = DEFAULT_PRICE_CACHE) -> int:
    """Price the usage records named on the command line, and nothing else.

    It takes files, not a directory to search. Discovering records by walking
    a layout is what this tool used to do, and it silently accounted for
    nothing the day the artifact tiers moved: the glob still matched, just
    never anything. A caller that knows which batch it is asking about can say
    so, and a caller that wants a wave sums the rows itself -- which is also
    the shape the batch tables want, one row per landing.
    """
    prices = load_prices(price_cache, offline=offline)

    rows, missing = [], 0
    for path in paths:
        parsed = parse_usage(str(path), prices)
        if parsed is None:
            print(f"unreadable usage record: {path}", file=sys.stderr)
            missing += 1
            continue
        cost, tokens, model = parsed
        rows.append((str(path), kind(usage_stage(str(path))), model, cost,
                     tokens, wall_seconds(str(path))))
    if not rows:
        return 1

    one = len(rows) == 1
    print(f"{'stage':<18}{'model':<30}{'$':>9}{'tokens':>12}{'wall':>9}")
    for path, k, model, cost, tokens, wall in rows:
        print(f"{k:<18}{(model or '?'):<30}"
              f"{('—' if cost is None else f'{cost:9.2f}'):>9}"
              f"{tokens:>12,}{(hm(wall) if wall else '—'):>9}")
        if one:
            print(f"  {path}")
    if not one:
        total = sum(c for _, _, _, c, _, _ in rows if c is not None)
        twall = sum(w for _, _, _, _, _, w in rows if w)
        ttok = sum(n for _, _, _, _, n, _ in rows)
        unpriced = sum(1 for _, _, _, c, _, _ in rows if c is None)
        print(f"{'Σ ' + str(len(rows)) + ' records':<48}"
              f"{total:9.2f}{ttok:>12,}{hm(twall):>9}")
        if unpriced:
            print(f"  {unpriced} record(s) had no priceable model",
                  file=sys.stderr)
    return 1 if missing else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("usage", nargs="+", help="Per-agent .usage.json records.")
    add_flags(ap)
    args = ap.parse_args()
    return report(args.usage, offline=args.offline,
                  price_cache=args.price_cache)


if __name__ == "__main__":
    sys.exit(main())
