# schedule.json schema

Field meaning for `<workdir>/crustify/artifacts/<link-unit>/<subsystem>/schedule.json`,
the waves of one subsystem. Layout example:
[`templates/schedule.json`](../../templates/schedule.json).

The campaign's planner agents emit one per subsystem before the first binder or
translator starts: the first run creates them, and every run re-emits those its changes
move. Waves and batches are computable in advance, so writing them down makes a
campaign's shape and cost reviewable before it spends anything.

A schedule holds only its subsystem's waves. Which subsystem it is, is its path; where
that subsystem runs in the campaign is its `index`, and its link unit's, in
`subsystems.json`, whose link units and subsystems are listed in execution order (see
`docs/artifacts/subsystems.md`). The campaign's total order is that order with
each subsystem's waves in place: every wave of link unit 0's first subsystem, then of its
second, then link unit 1's.

The foundational subsystems `void` and `string` are scheduled like any other, under the
first link unit.

| root field | meaning |
|---|---|
| `schema_version` | `2` |
| `waves` | the subsystem's waves, in execution order |

## 1. waves[*]

Entry *n* runs only after entry *n-1* has landed, and the last wave of a subsystem runs
before the first wave of the next.

| field | meaning |
|---|---|
| `index` | position within the subsystem, from zero |
| `batches` | the batches of this wave, which execute in parallel |

## 2. waves[*].batches[*]

A batch entry is a binder's or translator's `task.json` without its run fields
(`base_branch`, `model` and `billing`), which are decided when the batch launches; see `docs/artifacts/task.md`.

`objective` is per batch, not per wave. A port campaign wraps a type while C still reads
its fields and ports it afterwards, so one wave holds batches of differing objectives.

Each entry is written out as the batch's `task.json` with the run fields added and
nothing else changed.

## 3. Derived paths

Every index also addresses the filesystem and the branch namespace, so nothing records a
path: `docs/layout.md` spells each branch, worktree and artifact dir from
the link unit, subsystem, wave index and batch index. A batch's artifact dir holds its
`task.json` and is what its `--log-dir` names.

## 4. Version 1

Schema-v1 schedules were one campaign-wide `crustify/artifacts/schedule.json` nesting
`link_units` → `subsystems` → `waves`, each with an `index`. Their order now lives in
`subsystems.json` and their waves in the per-subsystem schedules; a campaign still on v1
is converted by its next planner run.
