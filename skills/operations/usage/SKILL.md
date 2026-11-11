---
name: usage
description: "How an agent session's tokens, cost and interval are derived from its transcript with crustify-usage, the script beside this skill, and how its rates are kept so figures never move. Read before pricing a run or filling a usage cell."
---

# Usage

How a session's usage is derived: its tokens, its cost and its interval, from the
transcript its CLI kept. What the figures fill is [`accounting`](../accounting/SKILL.md)'s.

## 1. The script

`crustify-usage`, beside this skill's `SKILL.md`, reports one session's usage as JSON,
from its transcript, a Claude Code session transcript or a Codex rollout, priced with the
backend and model proxy its run's `task.json` names, or at a kept snapshot, as
[Rates](#3-rates) describes. It runs on any Python 3.13, with the standard library alone,
and its `--help` gives its arguments. Its tests, `test_crustify_usage.py`, sit beside it.

## 2. Pricing

Every request the transcript records is priced on its own and the costs summed, never the
reverse: rate tiers key off a single request's context, so pricing the summed tokens
would charge a session of many modest requests at a tier none of them reached.

Rates are per service, so a request is priced at the rates of the service that billed it:
the model proxy's, or, without one, the backend's own service's. The transcript names the
model of each request, but not the service that billed it. A model or service the rates do
not know is reported with `cost_usd: null`, never a guessed zero. A provider-reported
dollar total is never used: under subscription billing, the cost is the API-equivalent
cost, as it is here.

The report gives, for the session, its requests, its tokens in exclusive buckets (input,
output, cache reads, cache writes and one-hour cache writes), its cost and its interval,
and under `total` the figures the dashboard takes: `cost_usd`, `tokens` and
`duration_ms`.

## 3. Rates

A session priced for the first time is priced at the rates fetched then, which are kept in
crustify's home as `rates/<timestamp>.json` whenever they differ from the latest kept.
Its record there, `sessions/<session id>/usage.session.json`, names its backend, its model
proxy and that snapshot; every later pricing of it uses the same, unless another snapshot
is named, which its record then names, so its figures never move. Its usage is not
kept: the dashboard holds its figures, and the script gives them again.
