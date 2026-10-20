# Accounting

What a campaign records about its own work, and who records it.

## The dashboard

The dashboard, `crustify/artifacts/dashboard.md` unless the settings name another, is the
campaign's record of what each planner run, batch, wave and subsystem did and cost. It is
filled from `templates/translate/dashboard.template.md`, an audit's from
`templates/audit/dashboard.template.md`, and keeps the template's format exactly.

It is tracked in the campaign's tree, so every agent's worktree holds a copy, and it is
filled as the work lands rather than at the end, by whoever can see each figure: every
agent fills every cell it can measure on the tree it commits, and the orchestrator fills
only what no agent can see. A figure is therefore measured once, where it is produced,
and the orchestrator reruns no suite or scan to record it.

## What agents fill

An agent records its work in its last commit:

- a binder, translator or reviewer, under the kind of each of its items: its rows in the
  kind's `Batches`, tests and `Batches: safety audit` tables, and for a review batch in
  `Batches — review: PoC + reports`, each placed in subsystem, wave and batch order under
  its `pass`; those tables' `Σ` rows; and the `Coverage stats` table and the Overview's LoC
  line;
- a planner run: its row in `Planning`.

A batch's cells are measured on the tree it lands, against the integration branch tip it
was rebased onto: coverage as the testing instructions' Coverage section measures it, and
the safety audit columns as the changes in the dashboard's Safety audit metrics. A rebase
that conflicts in the dashboard keeps every row both sides added, and the batch measures
its cells again, `Σ` rows included, when it reruns its validation.

An audit's dashboard follows the same division over its own tables.

## What the orchestrator fills

An agent cannot see:

- its own cost, tokens and wall, which its usage record gives only once it has ended, nor
  the per-unit costs derived from them;
- its own commit, which the `Planning` row names; and
- what spans agents: `Subsystem stats`, the Overview's branch line and the `Settings`
  lines.

The orchestrator fills those cells and their `Σ` cells, a batch's on the subsystem branch
once its wave's review is promoted, and a planner run's on the campaign branch once the
run has committed. Each usage record is committed with the dashboard update that cites it.
