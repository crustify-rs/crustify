---
name: evolution-record
description: "The record of the changes that landed in Crustify and its tools, `EVOLUTION.md`: its rows, their recurrence signals and statuses, when the watched rows are read, and how evolution itself evolves from the record. Read before drafting a change's row, writing or reading the record, or proposing a change to the evolution protocol."
---

# Evolution record

The record of what [`evolution`](../SKILL.md) landed, and what evolution learns from it.

## 1. Record

Every change that lands is recorded in Crustify's own repository, in
[`EVOLUTION.md`](../../../../EVOLUTION.md), whatever component it changed, so that a later
campaign can tell whether it held. A row gives the campaign and proposal the change came
from, the component and commit it landed as, the signal it answered, its recurrence signal
and its status, with a change that weakens a check marked so in its status. A change no
proposal filed names its campaign and `no proposal` in its place, with where it came from.
A proposal that lands several changes takes a row for each.

A change's row is drafted in its proposal, so that the review reads it. The record's writer
copies the row into the record when the change lands. An evolution branch never edits
`EVOLUTION.md`, so that two changes awaiting review never conflict there, and the record
has one writer per campaign. The record holds every change landed since it began, on
2026-11-12; what landed before is not recorded.

The recurrence signal is what a campaign would observe if the issue were back, in what a
campaign produces anyway: a review finding of a category, a run that fails for a cause, a
tool's error, a correction the user repeats. A change whose regression test checks all of
it has `test` in its place and is not watched. One with no signal a campaign could observe
has `none`, with why, and is not watched either.

A watched change is:

- `watched` from its landing;
- `recurred` once its signal is met again, with the evidence, which opens a proposal that
  cites the row: the change was wrong or partial, or the validation and review that passed
  it were; and
- `confirmed` once a campaign other than the one it came from has ended, having exercised
  it, without the signal.

A row's signal is looked for at two times, in every campaign:

- when a proposal is indexed, as [`evolution`](../SKILL.md)'s Proposals section describes:
  a signal that matches a row's recurrence signal marks that row `recurred`; and
- periodically, when the rows still `watched` are read against the findings, failed runs,
  proposals and corrections since the last reading. The campaign sets the period from its
  state, shorter after a change to a check lands or while findings cluster, longer while
  its modules are small: by default, after every fifth module it integrates. The rows are
  always read at each ship point and at an audit's end.

The record is committed on Crustify's working branch of the campaign and reaches `devel`
with it. Rows are appended in landing order and statuses edited in place, so that a merge
of two campaigns' working branches keeps both campaigns' rows, ordered by their landing.
Under `propose`, where no rule changes, the readings still run and their statuses are
committed all the same, since a record commit changes no rule, and they are put to the user
with the campaign's proposals. Under `off`, they do not run.

## 2. Evolving evolution

Evolution evolves from its own record, as everything else does from a campaign's. At a
campaign's end the record and the campaign's proposals are read for what repeats: changes
that recurred; changes the review rejected or the user declined, by cause; signals a run
met that no proposal answered; how long a blocking defect held its run; and what the
reviews bought for what they cost: per change, the findings each round made that held, those
its author's own validation had already caught, the rounds it took and their cost. How deep
a review reads, and how many rounds a kind of change gets, follow from that evidence, not
from a fixed rule. Each is a
signal of this guidance, as [`evolution`](../SKILL.md)'s Signals section lists them, and its proposal is on this
skill, on the agents' evolution rules or on what the review checks.

Such a proposal is validated and reviewed as any other, and is marked as one that changes
what checks the rest, so that the user reads it on its own before `devel` takes it, as
[`evolution`](../SKILL.md)'s Autonomy section describes.
