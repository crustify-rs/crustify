# Binding workflow

How a `wrap` campaign proceeds from its setup to its landed modules. A `port` campaign
follows the same workflow, with the differences [`porting.md`](porting.md) gives. How each
item is bound is [`../items/binding.md`](../items/binding.md); the branches, worktrees and artifact
dirs named below, and when each is created and purged, are [`../versioning.md`](../versioning.md)'s
and [`../layout.md`](../layout.md)'s.

The workflow runs after the [setup workflow](setup.md)'s Provisioning, Artifact tree,
Builds and Baseline, and its waves start after Preflight.

## 1. Planning

The plan is produced by planner runs, one after another, as
[`../decomposition.md`](../decomposition.md)'s Runs section describes: as many as the settings'
`plan-agent` answer asks for, by default two, under the translation model and billing. Each
run's `task.json`, `{"model": "<model>", "billing": "<billing>"}`, sits in its artifact dir.

The plan is complete when every run has committed and been promoted, and when the
schedule covers the approved scope: every translation unit the build compiles in scope
belongs to a module or is listed as configured out, and every unit of a module in
scope is scheduled in `schedule.json`. Before a run is promoted, its diff is checked
against the plan's rules: no frozen module, and no wave that is `wip` or `done`, changed
but for its progress; no index reused or renumbered; and each `depends_on.scheduled` is
acyclic, with every dependency in `scheduled` or `cut`.

A changed `scope`, `workload` or `review-workload` answer re-plans the modules that are
not frozen and the waves that are `todo`, through further planner runs under the new
answers. Landed work is never re-planned.

## 2. Rust tree

Once the plan is complete, the Rust tree is scaffolded on the working branch, as
[`../conventions.md`](../conventions.md) lays it out, for the link units in scope only:

- the safe crate at the repository's root, its `Cargo.toml` declaring the workspace, its
  shared package fields, its lints and its pinned nightly, and its `src/lib.rs` with a
  module per link unit;
- `rust-toolchain.toml` and `rustfmt.toml`, as [`../rust.md`](../rust.md) describes;
- one `-sys` crate per link unit, with its `Cargo.toml`, `src/lib.rs`, `build.rs` and
  bindgen input over the C under `c/`, the allowlists of which the batches fill as they
  bind items; and
- the integration test suites the conventions' Testing section places.

The wrappers of out-of-tree libraries are repositories of their own, cloned beside the
campaign's, as [`../dependencies.md`](../dependencies.md) describes.

Everything below a link unit is created lazily: a module's `.rs` file, and the modules
of the directories on its path, before its first wave, and each item's home, as
`schedule.json` assigns it, before the batch holding the item launches.

## 3. Order

The waves that are `todo` run one at a time, in the order of their `depends_on.scheduled`,
the lowest index first among those ready at once, as
[`../artifacts/schedule.md`](../artifacts/schedule.md) describes. A session may run every
wave left, or the waves of the part of the scope it was given.

Before a module's first wave starts, the settings are reread and their changes applied,
the module is frozen in `modules.json`, and its `.rs` file is scaffolded, all
committed on the working branch: that commit is the module's base, and records the
settings the module runs under. A wave of no module rereads the settings the same
way before it starts.

## 4. Waves and batches

A wave starts once the waves it depends on have been promoted. Its integration branch is
created first, the wave's base recorded, and the agent memory every agent reads at
startup is curated: duplicate and overlapping notes merged, and the notes the campaign has
made stale corrected or removed. The wave's `status` becomes `wip`.

Each batch then gets:

- its run dir, holding its `task.json`: its `schedule.json` entry's `kind` as `objective`
  and its `items`, the batch fields, and the run fields: the wave branch as `base_branch`,
  and the translation model and billing;
- its branch and worktree, forked from the wave branch; and
- symlinks to the gitignored state its tree needs from the base checkout.

The wave's batches run concurrently, up to the campaign's parallelism. A `wrap` batch runs
a binder, a `port` batch a translator:

```bash
crustify spawn-binder <batch worktree> <run dir>/task.json --log-dir <run dir>
crustify spawn-translator <batch worktree> <run dir>/task.json --log-dir <run dir>
```

The spawn command validates the batch, rejects one whose objective belongs to the other
command, and writes the agent's session record into the `--log-dir`. Each batch lands on
the wave branch as [`../versioning.md`](../versioning.md)'s Landing section describes, after running the gates of
[`../testing.md`](../testing.md)'s Regressions section on the tree it lands; those gates
are not run again for the wave. Its `status` follows its run, and once it lands, its
`commits` are derived from its branch, as [`../versioning.md`](../versioning.md)'s Landing
section describes.

A batch that fails keeps its branch and worktree for inspection. It is run again in a new
run dir, or its failure reported; its worklist is not translated outside an agent unless
the user asks for it. A competing landing is never discarded.

Once every batch has landed, the working branch is fast-forwarded to the wave's tip, and
the wave's progress and accounting are committed on it.

## 5. Review waves

When review is enabled, every translated wave is followed by its review wave, as
[`../reviewing.md`](../reviewing.md) describes. It is prepared and promoted as a wave, and
each of its batches reviews the batches of the reviewed wave its entry `reviews`, or
reviews each translation batch alone when the settings ask for that.

Each review batch's `task.json` holds the `commits` of the batches it reviews, as they sit
on the working branch, the approved objectives, the batch fields, its review wave branch,
and the review model and billing. A dry run checks the objectives it resolves to before
it is spawned:

```bash
crustify spawn-reviewer <batch worktree> <run dir>/task.json --log-dir <run dir>
```

## 6. Shipping

The shipping branch, `main`, advances only when the user approves it: it is
fast-forwarded to the working branch's tip, typically once a module has landed and
passed its gates.

## 7. Accounting

Each run's records are collected once it lands or fails, and its dashboard cells filled,
as [`../accounting.md`](../accounting.md) describes: a batch's usage cells on the working
branch once its wave is promoted, a planner run's once the run is promoted, and a
module's row once its last wave is promoted.
