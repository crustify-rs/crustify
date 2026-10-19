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

The two synthetic raw-lifetime subsystems have a schedule too, under the first link unit:
`<link-unit>/raw-lifetime-void/schedule.json` and `<link-unit>/raw-lifetime-string/schedule.json`,
each one wave of one `raw-lifetime` batch.

| root field | meaning |
|---|---|
| `schema_version` | `2` |
| `waves` | the subsystem's waves, in execution order |

## waves[*]

Entry *n* runs only after entry *n-1* has landed, and the last wave of a subsystem runs
before the first wave of the next.

| field | meaning |
|---|---|
| `index` | position within the subsystem, from zero |
| `batches` | the batches of this wave, which execute in parallel |

## waves[*].batches[*]

A batch entry is a binder's or translator's `task.json` without its run fields
(`base_branch`, `model` and `billing`), which the orchestrator decides when it launches the
batch; see `docs/artifacts/task.md`.

`objective` is per batch, not per wave. A port campaign wraps a type while C still reads
its fields and ports it afterwards, so one wave holds batches of differing objectives.

The orchestrator writes each entry out as the batch's `task.json`, adding the run fields
and changing nothing else.

## Derived paths

Every index also addresses the filesystem and the branch namespace, so nothing records a
path: `docs/layout.md` spells each branch, worktree and artifact dir from
the link unit, subsystem, wave index and batch index. A batch's artifact dir holds its
`task.json` and is what its `--log-dir` names.

## Version 1

Schema-v1 schedules were one campaign-wide `crustify/artifacts/schedule.json` nesting
`link_units` → `subsystems` → `waves`, each with an `index`. Their order now lives in
`subsystems.json` and their waves in the per-subsystem schedules; a campaign still on v1
is converted by its next planner run.
