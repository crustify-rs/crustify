---
name: accounting
description: "The dashboard, its cells, the runs' records and transcripts, and how cost and time are derived. Read before filling dashboard cells or collecting a run's records."
---

# Accounting

What a campaign records about its own work: the dashboard, the runs' records and
transcripts its figures come from, and how cost and time are derived from them.

## 1. The dashboard

The dashboard, `crustify/artifacts/dashboard.md` unless the settings name another, is the
campaign's record of what each planner run, batch, wave and module did and cost. It is
filled from `templates/translate/dashboard.template.md`, an audit's from
`templates/audit/dashboard.template.md`, and keeps the template's format exactly.
When an adopted Crustify change adds a table or a column to the template, it is
added to the dashboard on the working branch before the next batch launches: a batch
fills the rows of the tables in place, and never adds one.

It is tracked in the campaign's tree, so every agent's worktree holds a copy, and it is
filled as the work lands rather than at the end. Each figure is measured once, where it is
produced: no suite or scan is rerun only to record one.

## 2. Cells

The dashboard's cells fall into three kinds, by when their figures can be known.

### 2.1 Landing cells

The cells measured on the tree a landing commits:

- for a batch, under the route its items' `kind` selects, as
  [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Routes section gives it: its rows
  in that route's `Batches`, tests, `Batches: safety audit` and `Batches: API stability` tables, and for a review batch in
  `Batches — review: PoC + reports`, each placed in module, wave and batch order under
  its `pass`, and for a module pass, which spans both routes, in `Module passes`; those
  tables' `Σ` rows; and the `Coverage stats` table and the Overview's LoC
  line;
- for a planner run, its row in `Planning`, but for its usage cells.

They are filled in the landing's last commit, and measured against the integration branch
tip it was rebased onto: coverage as [`testing-builds`](../../verification/testing/builds/SKILL.md)'s Coverage section measures
it, the safety audit columns as the changes in the dashboard's Safety audit metrics, and
the API stability columns as the changes to the API of the landing's items are classified. A
rebase that conflicts in the dashboard keeps every row both sides added, and the landing's
cells, `Σ` rows included, are measured again where the gates its rebase reruns cover them;
the others stand as measured on the batch's base.

An integration merge, and any merge of one branch into another, keeps every row both
sides added, and settles the rest so: an additive `Σ` cell is the sum over the merged
rows, ours plus theirs less the merge base's, and so are the Overview's `Rust LoC`
figures; a usage `Σ` cell, its per-unit cells included, sums only the rows that carry
usage, so that it is filled again with theirs; a coverage `Σ` cell, and the Overview's
`C LoC`, are the later landing's; and `Coverage stats` takes the merged suites' counts,
with the later landing's percentages until a gate measures the merged tree, which the
merge commit's message says. A table or section the template holds once is kept once,
with the rows of every copy, whether or not the merge conflicts there, and the merged
dashboard is checked for repeated headings before it is committed.

### 2.2 Usage cells

The cells known only once an agent has ended, from its usage: its cost, tokens and wall,
the per-unit costs derived from them, and their `Σ` cells. A batch's are filled on the
working branch once its row is there, once its module is integrated, as
[`versioning`](../versioning/SKILL.md) describes, or, for a port's later-stage batch, which
runs after its module's switch, once its wave is promoted. A planner run's are filled once the run is
promoted. A batch run more than once costs the sum of its runs.

### 2.3 Campaign cells

The cells that span agents: the `Module stats` table, the Overview's branch line and
test baseline, and the `Settings` lines. A module's row and the branch line are filled
when the module is integrated, and a port's module row again as each of its later-stage
waves is promoted, the baseline once it is recorded, and the `Settings` lines,
with a Notes entry, whenever a settings change is applied.

### 2.4 Side campaign cells

A side campaign keeps its own dashboard, in its own repository, and its figures are
measured there. The parent's `Side campaigns` table copies them, one row per wrapper, as
they stand at the commit the parent pins, and the `side campaigns` row of `Module stats`
sums the rows, so that the parent's `Σ campaign` covers what its side campaigns cost. A
wrapper's row is filled each time the parent's pin moves, and its `shipped at` cell when
the wrapper ships the commit the parent pins. A side campaign that serves several parents
appears in each, with the figures as of each one's pin.

An audit's dashboard follows the same kinds over its own tables.

## 3. Records

Every run's `task.json` records how its agent ran: its backend, billing, model proxy and
the arguments its CLI was given, and, once it starts, its `session_id`, which ties the run
to its session. The session's transcript, which its CLI keeps by session id, is the
agent's full log and the source of its accounting. An agent spawned as a subagent of
another session has no session of its own: its session id is `agent-<agent id>`, the
name its host gives its transcript, under the spawning session's `subagents/`.

A transcript is copied into crustify's home, as `transcripts/<session id>.jsonl`, as soon
as its agent ends, because the CLIs move and prune their own files. Its usage is derived
from the copy, as [`usage`](../usage/SKILL.md) describes, with the backend and model proxy its
`task.json` names.

An evolution review is a run like any other: its `task.json` sits in its artifact dir, and
its transcript is collected and priced the same way, its cost counted with the sessions that
orchestrate the campaign and recorded, with its tokens and wall time, in its proposal's
Review section, so that what each review bought can be weighed against its cost.

The sessions that orchestrate the campaign are collected the same way: at the start of each session, the
transcripts of the sessions before it. A resumed session keeps its id while its transcript
grows: its transcript is copied again after each run, replacing the earlier copy. The
records, transcripts and rates stay in crustify's home.

## 4. Cost and time

A run's cost and tokens are its usage's `total.cost_usd` and `total.tokens`, as
[`usage`](../usage/SKILL.md) derives them from its transcript. The computed cost is used, never a provider-reported
dollar total; under subscription billing it is the API-equivalent cost.

An agent's wall time is its usage's interval. A wave's runs from its first batch's
launch through its final review and regression gates, a review wave's in an audit through
its landing, and a module's from its first launch through its final gate.
