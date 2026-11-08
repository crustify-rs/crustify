# Binding workflow

How a `wrap` campaign proceeds from its setup to its landed modules. A `port` campaign
follows the same workflow, with the differences [`porting.md`](porting.md) gives. How each
item is bound is [`../rust/items/binding.md`](../rust/items/binding.md); the branches, worktrees and artifact
dirs named below, and when each is created and purged, are [`../operations/versioning.md`](../operations/versioning.md)'s
and [`../operations/layout.md`](../operations/layout.md)'s.

The workflow runs after the [setup workflow](setup.md)'s Provisioning, Artifact tree,
Builds and Baseline, and its waves start after Preflight.

## 1. Planning

The plan is produced by planner runs, one after another, as
[`../planning/decomposition.md`](../planning/decomposition.md)'s Runs section describes: as many as the settings'
`plan-agent` answer asks for, by default two, under the translation run fields. Each
run's `task.json`, `{"backend": "<backend>", "billing": "<billing>"}`, sits in its artifact dir.

The plan is complete when every run has committed and been promoted, and when the
schedule covers the approved scope: every translation unit the build compiles in scope
belongs to a module or is listed as configured out, and every unit of a module in
scope is scheduled in `schedule.json`. Before a run is promoted, its diff is checked
against the plan's rules: no frozen module, and no wave that is `wip` or `done`, changed
but for its progress; no index reused or renumbered; the `depends_on.scheduled` of
`schedule.json`'s modules, and that of its waves, acyclic; and every in-tree dependency a
module's `modules.json` record holds in its `schedule.json` record's `scheduled` or
`cut`.

A changed `scope` or `module-concurrency` answer re-plans the modules that are not frozen
and the waves that are `todo`, through further planner runs under the new answers. Landed
work is never re-planned. A changed `workload` or `review-workload` answer re-plans
nothing: it caps the batches packed from then on.

A changed `campaign` answer, from `wrap` to `port` or back, re-plans the same way under
the new kind, frozen modules included: the user's change is what lets a frozen record
change, and only in its `objective`, which each module takes anew, as
[`../planning/decomposition.md`](../planning/decomposition.md)'s Objectives section
describes, while its decomposition stays as it is. The `todo` waves are re-planned with
their items' objectives, and the waves the new objectives call for are appended. What has
landed stays: in a campaign turned `port`, the bindings that landed are the wrappers its
ports keep, as [`../rust/items/porting.md`](../rust/items/porting.md)'s Symbols section
describes; in one turned `wrap`, what has been ported stays ported, and the rest is
wrapped.

## 2. Rust tree

Once the plan is complete, the Rust tree is scaffolded on the working branch, as
[`../rust/conventions.md`](../rust/conventions.md) lays it out, for the link units in scope only:

- the safe crate at the repository's root, its `Cargo.toml` declaring the workspace, its
  shared package fields, its lints and its pinned nightly, and its `src/lib.rs` with a
  module per link unit;
- `rust-toolchain.toml` and `rustfmt.toml`, as [`../rust/toolchain.md`](../rust/toolchain.md) describes;
- the raw bindings, one module of the safe crate per link unit, laid out as
  [`../rust/bindgen.md`](../rust/bindgen.md) describes, each with its bindgen input over the
  C under `c/`, the allowlists of which the batches fill as they bind items, and its
  bindings generated from them; and
- the integration test suites the conventions' Testing section places.

The wrappers of out-of-tree libraries are repositories of their own, cloned beside the
campaign's, as [`../planning/dependencies.md`](../planning/dependencies.md) describes.

Everything below a link unit is created lazily: a module's `.rs` file, and the modules
of the directories on its path, before its first wave, and each item's home, as
`schedule.json` assigns it, before the batch holding the item launches.

## 3. Order

The modules run as the settings' `module-concurrency` answer asks, as
[`../planning/scheduling.md`](../planning/scheduling.md)'s Waves and batches section
describes:

- with concurrent modules, a module's run starts once the waves of other modules that its
  waves depend on have been integrated, on a branch of its own, and its waves that are
  `todo` run one at a time, in the order of their `depends_on.scheduled`. The runs of
  modules that do not depend on each other run at once, as many as
  [`../operations/concurrency.md`](../operations/concurrency.md) describes, and among the
  runs ready at once, the one whose first wave has the lowest index starts first;
- with merged waves, the waves that are `todo` run one at a time, in the order of their
  `depends_on.scheduled`, the lowest index first among those ready at once, as
  [`../artifacts/schedule.md`](../artifacts/schedule.md) describes.

A session may run every wave left, or the waves of the part of the scope it was given.

Before a module's first wave starts, the settings are reread and their changes applied,
and its `.rs` file is scaffolded, both committed on the working branch: that commit is the
module's base, and records the settings the module runs under. A wave of no module
rereads the settings the same way before it starts. The module is frozen in
`modules.json` in the same commit, as
[`../artifacts/modules.md`](../artifacts/modules.md)'s Status section describes. With
concurrent modules, the module's branch is then forked from its base, as
[`../operations/versioning.md`](../operations/versioning.md)'s Lifecycle section
describes.

## 4. Waves and batches

A wave starts once the waves it depends on have been promoted, to its module's branch or
to the working branch. Its integration branch is created first, the wave's base recorded, and the agent memory every agent reads at
startup is curated: duplicate and overlapping notes merged, and the notes the campaign has
made stale corrected or removed. The wave's `status` becomes `wip`.

Its batches are then packed from its items, and from those of the waves it shares batches
with, as [`../planning/scheduling.md`](../planning/scheduling.md)'s Batches section
describes, and recorded in its `schedule.json` entry. Before a batch whose items depend on
units that have not landed, a wrap batch binds them, as its Wrap batches section
describes, and lands first.

Each batch then gets:

- its run dir, holding its `task.json`: its `schedule.json` entry's `kind` as `objective`
  and its `items`, the batch fields, and the run fields: the wave branch as `base_branch`,
  and the translation run fields;
- its branch and worktree, forked from the wave branch; and
- symlinks to the gitignored state its tree needs from the base checkout.

The wave's batches run concurrently, as many at once as
[`../operations/concurrency.md`](../operations/concurrency.md) describes. A `wrap` batch runs a binder, a `port`
batch a translator:

```bash
crustify spawn-binder <batch worktree> <run dir>/task.json
crustify spawn-translator <batch worktree> <run dir>/task.json
```

The spawn command validates the batch, rejects one whose objective belongs to the other
command, and writes the run's session id into its `task.json`. Each batch lands on
the wave branch as [`../operations/versioning.md`](../operations/versioning.md)'s Landing section describes, after running the gates of
[`../verification/testing.md`](../verification/testing.md)'s Regressions section on the tree it lands; those gates
are not run again for the wave. Its `status` follows its run, and once it lands, its
`commits` are derived from its branch, as [`../operations/versioning.md`](../operations/versioning.md)'s Landing
section describes.

A batch that fails keeps its branch and worktree for inspection. It is run again in a new
run dir, its items are packed again into new batches, or its failure is reported; its worklist is not translated outside an agent unless
the user asks for it. A competing landing is never discarded.

Once every batch has landed, its review batches included, the wave is promoted to the branch it forked from, as
[`../operations/versioning.md`](../operations/versioning.md)'s Promotion section
describes, and its progress and accounting are committed on the working branch, as its
Progress section times them.

With concurrent modules, once the last wave of a module's run has been promoted, the
module is integrated into the working branch, as
[`../operations/versioning.md`](../operations/versioning.md)'s Integration section
describes: the working branch merged into its branch, its additive conflicts resolved,
the merge's gates passed, and the working branch fast-forwarded to it. Its gates are
those of [`../verification/testing.md`](../verification/testing.md)'s Regressions
section, and in a port campaign the module's own integration, as
[`porting.md`](porting.md)'s Builds section describes.

## 5. Review batches

When review is enabled, each wave's landed batches are reviewed before it is promoted, by
review batches of the same wave, packed as the batches they review land, as
[`../verification/reviewing.md`](../verification/reviewing.md)'s Review batches section
describes, or one per translation batch when the settings ask for that.

Each review batch's `task.json` holds the `commits` of the batches it reviews, as they sit
on the wave branch, the approved objectives, the batch fields, the wave branch as
`base_branch`, and the review run fields. A dry run checks the objectives it resolves to
before it is spawned:

```bash
crustify spawn-reviewer <batch worktree> <run dir>/task.json
```

## 6. Shipping

The shipping branch, `main`, advances only when the user approves it: it is
fast-forwarded to the working branch's tip at the points the settings' `ship` answer names,
each once the modules it names have been integrated and passed their gates: by default,
after every integrated module. A `ship` answer left until after planning is decided once
the plan is complete, before the first wave starts, from ship points proposed with the
boundary each would leave: the in-tree items still C that the Rust before it reaches
through wrappers, and the exports the C after it still calls.

## 7. Accounting

Each run's records are collected once it lands or fails, and its dashboard cells filled,
as [`../operations/accounting.md`](../operations/accounting.md) describes: a batch's usage cells on the working
branch once its wave's landings are there, when the wave is promoted to it with merged
waves and when its module is integrated with concurrent modules; a planner run's once the
run is promoted; and a module's row once it is integrated.
