# schedule.json schema

Field meaning for `<workdir>/crustify/artifacts/schedule.json`, the campaign's module
order, waves and batches. Layout example: [`templates/schedule.json`](../../templates/schedule.json).

The campaign has one schedule, which every planner run extends: the first run creates it,
and each later one appends the waves its scope adds and re-plans the waves that have not
started. Waves and batches are computable in advance, so writing them down makes a
campaign's shape and cost reviewable before it spends anything.

TODO: review waves, which follow each translated wave when review is enabled, and an
audit's review waves, are left out of this schema for now.

The schedule holds two kinds of field:

- the plan: the order of the modules, the waves, their dependencies, budgets and batches,
  and each batch's worklist, decided by planning; and
- the progress: each wave's and batch's `status`, and each batch's `commits`, recorded as
  the work launches and lands.

| root field | meaning |
|---|---|
| `schema_version` | `4` |
| `modules` | the order of the campaign's modules, one record per module the schedule holds waves of, by `layer` |
| `waves` | the campaign's waves, in `index` order |

## 1. modules[*]

The order of the modules is computed over every module of the decomposition, as
`specs/planning/scheduling.md`'s Order section describes, and recorded here, with the
dependencies it keeps and those it cuts.

| field | meaning |
|---|---|
| `link_unit`, `module`, `foundational` | the module's identity in `modules.json`, as its `link_units[*].name`, its `name` and its `foundational` |
| `layer` | its place in the order of the modules: 0 for one that depends on no module ordered before it, else one more than the highest of those it depends on |
| `waves` | the indices of its waves |
| `depends_on.scheduled` | the modules it depends on that are ordered before it, each a dependency record below |
| `depends_on.cut` | the modules it depends on that are ordered after it, its dependency on them cut to break a cycle, each a dependency record with its `items` |
| `depends_on.external` | the out-of-tree libraries its units use, each an out-of-tree record below |

A dependency record names the module depended on, by `link_unit`, `module` and
`foundational`, and counts what this module's units use of it:

| field | meaning |
|---|---|
| `unique_edges` | the distinct units of that module they use: one binding each, when the dependency is cut |
| `total_edges` | every unit edge from this module's units to that module's |
| `items` | on a cut record: each edge it cuts, as `from` (this module's unit), `to` (the other module's unit), each `{name, defined_in}`, and the `kind` of `to` |

An out-of-tree record names the library its units use, by its `library`, a
`libraries[*].name` of `dependencies.json`, and counts what they use of it, with the
`unique_edges` and `total_edges` of a dependency record and every edge in its `items`, as
on a cut record: `to` is the library's entity, by the name and the defining header its
users reference. No entity of the library is a unit of this schedule: its side campaign
wraps it, before the first wave that holds a `from` of the record, as
`specs/planning/dependencies.md`'s Side campaigns section describes.

`scheduled` alone is acyclic across the schedule, and with `cut` it is every module this
one depends on. A planner run rewrites `modules` from its order; the waves that have
started keep their records, as [Re-planning](#5-re-planning) describes.

## 2. waves[*]

| field | meaning |
|---|---|
| `index` | the wave's id, from zero; see [Indices](#4-indices) |
| `link_unit` | the `link_units[*].name` of `modules.json` its units belong to; `null` when the wave belongs to no module |
| `module` | the module's `name` within that link unit; `null` when the wave belongs to no module: a merged wave, or one of a campaign with no decomposition |
| `foundational` | the module's `foundational`; `false` when the wave belongs to no module |
| `layer` | its module's `layer`, or the `layer` of the modules whose waves a merged wave holds; `null` when the campaign has no decomposition |
| `sublayer` | its place among its module's waves, from 0, or, for a merged wave, that of each of the waves it holds; `null` when the campaign has no decomposition |
| `status` | `todo`, `wip` or `done` |
| `depends_on` | the waves this one depends on: `scheduled` and `cut`, each an array of wave indices |
| `budgets` | the batch limits the wave was packed under, the campaign's `workload` caps |
| `batches` | the wave's batches, which execute in parallel |

`depends_on.scheduled` lists the waves that complete before this one: its module's
previous wave, and the waves that hold its items' dependencies. `depends_on.cut` lists the
waves that hold its items' cut dependencies, which run after it; it reaches what they hold
through the safe wrappers a wrap wave before it adds, as `specs/planning/scheduling.md`'s
Wrap waves section describes. Their union is every wave this one depends on, and
`scheduled` alone is acyclic across the schedule.

With concurrent modules, the settings' default, every wave belongs to one module; with
merged waves, a wave holds the waves of every module at the same `layer` and `sublayer`,
each batch one module's, as `specs/planning/scheduling.md` describes.

A wave is `todo` until its first batch launches, `wip` while any of its batches is
running or has failed, and `done` once every batch has landed and the wave has been
promoted.

## 3. waves[*].batches[*]

| field | meaning |
|---|---|
| `index` | the batch's id within its wave, from zero |
| `link_unit`, `module`, `foundational` | the module whose units it holds, as for its wave; `null`, `null` and `false` when the campaign has no decomposition |
| `kind` | `wrap` |
| `status` | `todo`, `wip`, `done` or `failed` |
| `items` | the batch's worklist, as `specs/artifacts/task.md` describes its `items` |
| `commits` | the commits the batch landed, in order; empty until it lands |

TODO (porting): `port` batches, and waves that hold batches of either kind.

A batch is `todo` until its agent launches, `wip` while an agent runs it, `done` once it
has landed every item of its worklist, and `failed` when its last agent ended without
landing. An item's status is its batch's: a scheduled item is translated once its batch is
`done`.

A batch's `commits` are its landing's commits as they sit on its wave branch, which a
promotion fast-forwards without rewriting them.

## 4. Indices

A wave's `index` is its permanent id. Each planner run numbers the waves it appends after
the highest index the schedule holds, so an index is never reused, renumbered or moved,
and the batch id `wave-<index>/batch-<index>` and every branch named from it keep
identifying the same work.

An index is not a position: the waves that are `todo` run in the order of
`depends_on.scheduled`, and among the waves ready at once, the lowest index runs first. A
later run may therefore schedule a wave that runs before one an earlier run appended.

## 5. Re-planning

Only waves that are `todo` are re-planned: a re-plan may change, split or remove them,
and the waves that replace them take new indices. A wave that is `wip` or `done` keeps
its record, apart from the progress fields, and is never revisited, and its items are not
scheduled again. A frozen module's waves that are `todo` are re-planned like any other,
within its frozen decomposition, and waves may be appended to it, such as those a module
added after it calls for.

Each wave's batches are packed from the units it schedules, under the campaign's
`workload` caps.

## 6. Derived paths

A batch's id, `wave-<index>/batch-<index>`, names its branch and worktree, and its wave
index the wave branch, as `specs/operations/versioning.md` spells them. Its artifact dirs are those of the
agents that ran it, each holding a `task.json` that names the batch's wave and index.

## 7. Earlier versions

Schema-v3 schedules had no `modules`, the order of the modules being `modules.json`'s
`depends_on`, no `sublayer`, and could hold review waves. A campaign on v3 is converted by
its next planner run: `modules` is written from its order, each wave's `sublayer` numbered
among its module's waves in index order, and its review waves kept as they are until
review waves return to this schema.

Schema-v2 schedules were one `crustify/artifacts/<link-unit>/<subsystem>/schedule.json`
per subsystem, whose wave indices counted within the subsystem and whose batches carried
an `objective` in place of `kind`. Schema-v1 was one campaign-wide schedule nesting
`link_units` → `subsystems` → `waves`. A campaign on either is converted by its next
planner run: its waves are numbered in the order they ran or were to run, every v2
`objective` becomes the batch's `kind`, and every wave's `subsystem` becomes the `module`
its units are re-decomposed into, as `specs/planning/decomposition.md` describes.
