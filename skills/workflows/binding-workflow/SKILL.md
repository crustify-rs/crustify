---
name: binding-workflow
description: "How a wrap or port campaign proceeds from setup to landed modules: planner runs, the Rust tree, module order, waves and batches, review batches, shipping and accounting. Read before running a translation campaign's planning, waves or shipping."
---

# Binding workflow

How a `wrap` campaign proceeds from its setup to its landed modules. A `port` campaign
follows the same workflow, with the differences [`porting-workflow`](../porting-workflow/SKILL.md) gives. How each
item is bound is [`binding`](../../rust/binding/SKILL.md); the branches, worktrees and artifact
dirs named below, and when each is created and purged, are [`versioning`](../../operations/versioning/SKILL.md)'s
and [`layout`](../../operations/layout/SKILL.md)'s.

The workflow runs after the [setup workflow](../setup/SKILL.md)'s Provisioning, Artifact tree,
Builds and Baseline, and its waves start after Preflight.

## 1. Planning

The plan is produced by planner runs, one after another, as
[`decomposition`](../../planning/decomposition/SKILL.md)'s Runs section describes: as many as the settings'
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

A changed `scope` answer re-plans the modules that are not frozen
and the waves that are `todo`, through further planner runs under the new answers. Landed
work is never re-planned. A changed `workload` or `review-workload` answer re-plans
nothing: it caps the batches packed from then on.

A changed `campaign` answer, from `wrap` to `port` or back, unfreezes every module, as
[`modules-schema`](../../artifacts/modules-schema/SKILL.md)'s Status section describes, and
re-plans the decomposition and the schedule under the new kind: each module takes its
objective anew, as [`decomposition`](../../planning/decomposition/SKILL.md)'s
Objectives section describes, its decomposition may change, and every `todo` wave is
re-planned. An item that has landed keeps its code, which moves to the home the new
decomposition gives it before the next wave starts. What has landed stays: in a campaign turned `port`, the bindings that landed are the wrappers its
ports keep, as [`porting`](../../rust/porting/SKILL.md)'s FFI boundary section
describes; in one turned `wrap`, what has been ported stays ported, and the rest is
wrapped.

## 2. Rust tree

Once the plan is complete, the Rust tree is scaffolded on the working branch, as
[`conventions`](../../rust/conventions/SKILL.md) lays it out, for the link units in scope only:

- the safe crate at the repository's root, its `Cargo.toml` declaring the workspace, its
  shared package fields, its lints and its pinned nightly, and its `src/lib.rs` with a
  module per link unit;
- `rust-toolchain.toml` and `rustfmt.toml`, as [`toolchain`](../../rust/toolchain/SKILL.md) describes;
- the raw bindings, one module of the safe crate per link unit, laid out as
  [`bindgen`](../../rust/bindgen/SKILL.md) describes, each with its bindgen input over the
  C under `c/`, the allowlists of which the batches fill as they bind items, and its
  bindings generated from them; and
- the integration test suites the conventions' Testing section places.

The wrappers of out-of-tree libraries are repositories of their own, cloned beside the
campaign's, as [`dependencies`](../../planning/dependencies/SKILL.md) describes.

Everything below a link unit is created lazily: a module's `.rs` file, and the modules
of the directories on its path, before its first wave, and each item's home, as
`schedule.json` assigns it, before the batch holding the item launches.

## 3. Order

The modules run as [`scheduling`](../../planning/scheduling/SKILL.md)'s Waves and
batches section describes, each run on a branch of its own, its `todo` waves in the order
of their `depends_on.scheduled`; among the runs ready at once, the one whose first wave
has the lowest index starts first.

A session may run every wave left, or the waves of the part of the scope it was given.

Before a module's first wave starts, the settings are reread and their changes applied,
and its `.rs` file is scaffolded, both committed on the working branch: that commit is the
module's base, and records the settings the module runs under. A wave of no module
rereads the settings the same way before it starts. The module is frozen in
`modules.json` in the same commit, as
[`modules-schema`](../../artifacts/modules-schema/SKILL.md)'s Status section describes. The
module's branch is then forked from its base, as
[`versioning`](../../operations/versioning/SKILL.md)'s Lifecycle section
describes.

## 4. Waves and batches

A wave starts once the waves it depends on have been promoted, to its module's branch or
to the working branch. Its integration branch is created first, the wave's base recorded, and the agent memory every agent reads at
startup is curated: duplicate and overlapping notes merged, and the notes the campaign has
made stale corrected or removed. The wave's `status` becomes `wip`.

Its batches are then packed from its items, and from those of the waves it shares batches
with, as [`scheduling`](../../planning/scheduling/SKILL.md)'s Batches section
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
[`concurrency`](../../operations/concurrency/SKILL.md) describes, each from its `task.json`, in which the
run's session id is recorded once it starts. Each batch lands on
the wave branch as [`versioning`](../../operations/versioning/SKILL.md)'s Landing section describes, after running the gates of
[`testing-gates`](../../verification/testing/gates/SKILL.md)'s Regressions section on the tree it lands; those gates
are not run again for the wave. Its `status` follows its run, and once it lands, its
`commits` are derived from its branch, as [`versioning`](../../operations/versioning/SKILL.md)'s Landing
section describes.

A batch that fails keeps its branch and worktree for inspection. It is run again in a new
run dir, its items are packed again into new batches, or its failure is reported; its worklist is not translated outside an agent unless
the user asks for it. A competing landing is never discarded.

Once every batch has landed, its review batches included, the wave is promoted to the branch it forked from, as
[`versioning`](../../operations/versioning/SKILL.md)'s Promotion section
describes, and its progress and accounting are committed on the working branch, as its
Progress section times them.

Once the last wave of a module's run has been promoted, the module is integrated into the
working branch, as [`versioning`](../../operations/versioning/SKILL.md)'s Integration section
describes. In a port campaign a module is integrated from C once, and its later-stage waves
run after that, as [`porting-workflow`](../porting-workflow/SKILL.md)'s Later stages section
describes.

## 5. Review batches

When review is enabled, each wave's landed batches are reviewed before it is promoted, by
review batches of the same wave, packed as the batches they review land, as
[`reviewing`](../../verification/reviewing/SKILL.md)'s Review batches section
describes, or one per translation batch when the settings ask for that, and a module pass
reviews each module whole before its integration, or at its end in a wrap campaign.

Each review batch's `task.json` holds the `commits` of the batches it reviews and the
approved objectives, as [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Review batches
section describes.

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
as [`accounting`](../../operations/accounting/SKILL.md) describes: a batch's usage cells on the working
branch once its module is integrated; a planner run's once the
run is promoted; and a module's row once it is integrated.
