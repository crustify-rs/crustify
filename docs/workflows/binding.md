# Binding workflow

How a `wrap` campaign proceeds from its setup to its promoted subsystems. A `port` campaign
follows the same workflow, with the differences [`porting.md`](porting.md) gives. How each
item is bound is [`../binding.md`](../binding.md); the branches, worktrees and artifact
dirs named below, and when each is created and purged, are [`../layout.md`](../layout.md).

The workflow runs after the [setup workflow](setup.md)'s Provisioning, Artifact tree,
Builds and Baseline, and its waves start after Preflight.

## 1. Planning

The plan is produced by planner runs, one after another, as
[`../planning.md`](../planning.md)'s Runs section describes: as many as the settings'
`plan-agent` answer asks for, by default two, under the translation model and billing. Each
run's `task.json`, `{"model": "<model>", "billing": "<billing>"}`, sits in its artifact dir.

The plan is complete when every run has committed and been promoted, and when the
subsystems' schedules cover the approved scope: every translation unit the build compiles
in scope belongs to a subsystem or is listed as configured out, and every subsystem has its
`schedule.json`.

A changed `scope`, `workload` or `review-workload` answer re-plans the subsystems, waves
and batches that have not started, through further planner runs under the new answers.
Landed work is never re-planned.

## 2. Rust tree

Once the plan is complete, the Rust tree is scaffolded on the campaign branch, as
[`../conventions.md`](../conventions.md) lays it out, for the link units in scope only:

- the top-level virtual manifest;
- one `-sys` crate per link unit, with its `Cargo.toml`, `src/lib.rs`, `build.rs` and
  bindgen input, the allowlists of which the batches fill as they bind items;
- the safe crate, with a module per link unit; and
- the integration test suites the conventions' Testing section places.

Everything below a link unit is created lazily: a subsystem's root before its first batch,
a translation unit's or header's module before its first units are scheduled, and each
item's home, as the planner assigned it in its subsystem's `schedule.json`, before the
batch holding the item launches.

## 3. Subsystems

Subsystems run one at a time, in the order `subsystems.json` lists them. Before a subsystem
starts, the settings are reread and their changes applied, so that the subsystem's base
commit records the settings it runs under; then its branch and artifact dir are created,
and its Rust root is scaffolded and committed as its base.

The subsystem's waves run in its `schedule.json` order. Once the last has been promoted to
the subsystem branch, the subsystem is promoted to the campaign branch.

## 4. Waves and batches

A wave starts once the previous one has been promoted. Its integration branch and artifact
dir are created first, the wave's base recorded, and the agent memory every agent reads at
startup is curated: duplicate and overlapping notes merged, and the notes the campaign has
made stale corrected or removed.

Each batch then gets:

- its artifact dir, holding its `schedule.json` entry as `task.json` with the run fields
  added: the wave branch as `base_branch`, and the translation model and billing;
- its branch and worktree, forked from the wave branch; and
- symlinks to the gitignored state its tree needs from the base checkout.

The wave's batches run concurrently, up to the campaign's parallelism. A `wrap` batch runs
a binder, a `port` batch a translator:

```bash
crustify spawn-binder <batch worktree> <batch dir>/task.json --log-dir <batch dir>
crustify spawn-translator <batch worktree> <batch dir>/task.json --log-dir <batch dir>
```

The spawn command validates the batch, rejects one whose objective belongs to the other
command, and writes the agent's session record into the `--log-dir`. Each batch lands on
the wave branch as [`../landing.md`](../landing.md) describes, after running the gates of
[`../testing.md`](../testing.md)'s Regressions section on the tree it lands; those gates
are not run again for the wave.

A batch that fails keeps its branch and worktree for inspection. It is respawned, or its
failure reported; its worklist is not translated outside an agent unless the user asks for
it. A competing landing is never discarded.

## 5. Review waves

When review is enabled, every translated wave is followed by its review wave before the
next translation wave starts, as [`../reviewing.md`](../reviewing.md) describes. The
wave's translation batches are distributed into review batches by the wave's complexity,
within the review caps, or one review batch per translation batch when the settings ask for
that.

Each review batch's `task.json` holds the landed commits of its translation batches, as
they sit on the wave branch, the approved objectives, its review wave branch, and the
review model and billing. A dry run checks the objectives it resolves to before it is
spawned:

```bash
crustify spawn-reviewer <batch worktree> <batch dir>/task.json --log-dir <batch dir>
```

Once the review wave has landed, its tip is promoted to the subsystem branch. Without
review, the wave's own tip is promoted once its batches have landed.

## 6. Accounting

Each batch's records are collected once it lands or fails, and its dashboard cells filled,
as [`../accounting.md`](../accounting.md) describes: a batch's usage cells on the
subsystem branch once its wave's review is promoted, a planner run's on the campaign branch
once the run is promoted, and a subsystem's row when the subsystem is promoted.
