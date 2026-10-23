# Accounting

What a campaign records about its own work: the dashboard, the session and usage records
its figures come from, and how cost and time are derived from them.

## 1. The dashboard

The dashboard, `crustify/artifacts/dashboard.md` unless the settings name another, is the
campaign's record of what each planner run, batch, wave and module did and cost. It is
filled from `templates/translate/dashboard.template.md`, an audit's from
`templates/audit/dashboard.template.md`, and keeps the template's format exactly.

It is tracked in the campaign's tree, so every agent's worktree holds a copy, and it is
filled as the work lands rather than at the end. Each figure is measured once, where it is
produced: no suite or scan is rerun only to record one.

## 2. Cells

The dashboard's cells fall into three kinds, by when their figures can be known.

### 2.1 Landing cells

The cells measured on the tree a landing commits:

- for a batch, under the kind of each of its items: its rows in the kind's `Batches`, tests
  and `Batches: safety audit` tables, and for a review batch in
  `Batches — review: PoC + reports`, each placed in module, wave and batch order under
  its `pass`; those tables' `Σ` rows; and the `Coverage stats` table and the Overview's LoC
  line;
- for a planner run, its row in `Planning`, but for its usage cells.

They are filled in the landing's last commit, and measured against the integration branch
tip it was rebased onto: coverage as [`testing.md`](testing.md)'s Coverage section measures
it, and the safety audit columns as the changes in the dashboard's Safety audit metrics. A
rebase that conflicts in the dashboard keeps every row both sides added, and the landing's
cells, `Σ` rows included, are measured again when its validation reruns.

### 2.2 Usage cells

The cells known only once an agent has ended, from its usage record: its cost, tokens and
wall, the per-unit costs derived from them, and their `Σ` cells. A batch's are filled on
the working branch once its wave is promoted, a planner run's once the run is promoted.
A batch run more than once costs the sum of its runs. Each usage record is committed with
the dashboard update that cites it.

### 2.3 Campaign cells

The cells that span agents: the `Module stats` table, the Overview's branch line and
test baseline, and the `Settings` lines. A module's row and the branch line are filled
when the module's last wave is promoted, the baseline once it is recorded, and the `Settings` lines,
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

Every agent's `--log-dir` receives its `<role>.session.json`: the CLI that ran it, the
provider and model, its session id, which agent it was, its exit status and interval, and
where its transcript was when it ended. The transcript is the agent's full log and the
source of its accounting.

A transcript is copied into crustify's home, as `transcripts/<session id>.jsonl`, as soon
as its batch lands or fails, because the CLIs move and prune their own files. One that is
no longer where its session record says is found by its session id: Claude Code keeps each
session's transcript under its configuration directory, and Codex each session's rollout
under its `CODEX_HOME`, in a file whose name contains the session id. The usage record is
derived from the copy:

```bash
crustify usage ~/.crustify/transcripts/<session id>.jsonl -o <run dir>/<role>.usage.json
```

`crustify usage` prices every request the transcript records and reports the session's
tokens, cost and interval as JSON. A Claude Code session whose record names the
`openrouter` provider is priced with `--provider openrouter`: the transcript cannot tell it
apart from Anthropic.

The assistant's sessions leave `assistant-<timestamp>.session.json` in their directories in
crustify's home, as [`layout.md`](layout.md) describes. At the start of each session, the
records of the sessions before it are copied into `crustify/artifacts/assistant/`, and
their transcripts collected the same way. A resumed session keeps its id while its
transcript grows, so it leaves several session records with one id: its transcript is
copied again after each run, replacing the earlier copy, and its usage record derived once,
from the latest copy, into the directory of the newest of those records. The session and
usage records are committed; the transcripts stay in crustify's home.

## 4. Cost and time

A batch's cost and tokens are its usage record's `total.cost_usd` and `total.tokens`:
`binder.usage.json` for a `wrap` batch, `translator.usage.json` for a `port` batch,
`reviewer.usage.json` for a review batch and `planner.usage.json` for a planner run. The
computed cost is used, never a provider-reported dollar total; under subscription billing
it is the API-equivalent cost.

An agent's wall time is its usage record's interval. A wave's runs from its first batch's
launch through its final review and regression gates, a review wave's in an audit through
its landing, and a module's from its first launch through its final gate.
