# schedule.json schema

Field meaning for `<workdir>/crustify/artifacts/schedule.json`, the campaign's waves and
batches. Layout example: [`templates/schedule.json`](../../templates/schedule.json).

The campaign has one schedule, which every planner run extends: the first run creates it,
and each later one appends the waves its scope adds and re-plans the waves that have not
started. Waves and batches are computable in advance, so writing them down makes a
campaign's shape and cost reviewable before it spends anything. An audit's waves, planned
without a planner, are recorded in the same schedule.

The schedule holds two kinds of field:

- the plan: its waves, their dependencies, budgets and batches, and each batch's worklist,
  decided by planning; and
- the progress: each wave's and batch's `status`, and each batch's `commits`, recorded as
  the work launches and lands.

| root field | meaning |
|---|---|
| `schema_version` | `3` |
| `waves` | the campaign's waves, in `index` order |

## 1. waves[*]

| field | meaning |
|---|---|
| `index` | the wave's id, from zero; see [Indices](#3-indices) |
| `link_unit` | the `link_units[*].name` of `modules.json` its units belong to; `null` when the campaign has no decomposition |
| `module` | the module's `name` within that link unit; `null` when the wave belongs to no module |
| `foundational` | the module's `foundational`; `false` when the wave belongs to no module |
| `reviews` | a review wave's reviewed wave, by `index`; absent on any other wave |
| `status` | `todo`, `wip` or `done` |
| `depends_on` | the waves this one depends on: `scheduled` and `cut`, each an array of wave indices |
| `budgets` | the batch limits the wave was packed under, as wavefront records them |
| `batches` | the wave's batches, which execute in parallel |

`depends_on.scheduled` lists the waves that run before this one, and `depends_on.cut` the
waves it depends on that run after it, its dependency on them cut to break a cycle; it
reaches what they hold through narrow raw seams until a later wave replaces them. Their
union is every wave this one depends on, and `scheduled` alone is acyclic across the
schedule.

A wave is `todo` until its first batch launches, `wip` while any of its batches is
running or has failed, and `done` once every batch has landed and the wave has been
promoted.

A review wave depends on the wave it reviews, which is listed both in `reviews` and in
`depends_on.scheduled`. Since every translated wave is followed by its review wave
before the next translation wave starts, each wave that follows a reviewed wave lists that
wave's review wave in its `depends_on.scheduled`.

## 2. waves[*].batches[*]

| field | meaning |
|---|---|
| `index` | the batch's id within its wave, from zero |
| `kind` | `wrap`, `port` or `review` |
| `status` | `todo`, `wip`, `done` or `failed` |
| `items` | a `wrap` or `port` batch's worklist, as `specs/artifacts/task.md` describes its `items` |
| `reviews` | a translation campaign's review batch: the indices of the batches of the reviewed wave it reviews |
| `paths`, `reports` | an audit's review batch: its worklist, as `specs/artifacts/task.md` describes them |
| `commits` | the commits the batch landed, in order; empty until it lands |

`kind` is per batch, not per wave. A port campaign wraps a type while C still reads its
fields and ports it afterwards, so one wave holds batches of either kind.

A batch is `todo` until its agent launches, `wip` while an agent runs it, `done` once it
has landed every item of its worklist, and `failed` when its last agent ended without
landing. An item's status is its batch's: a scheduled item is translated once its batch is
`done`.

A batch's `commits` are its landing's commits as they sit on its wave branch, which a
promotion fast-forwards without rewriting them. A review batch's task carries the commits
of the batches it reviews.

## 3. Indices

A wave's `index` is its permanent id. Each planner run numbers the waves it appends after
the highest index the schedule holds, so an index is never reused, renumbered or moved,
and the batch id `wave-<index>/batch-<index>` and every branch named from it keep
identifying the same work.

An index is not a position: the waves that are `todo` run in the order of
`depends_on.scheduled`, and among the waves ready at once, the lowest index runs first. A
later run may therefore schedule a wave that runs before one an earlier run appended.

## 4. Re-planning

Only waves that are `todo` are re-planned: a re-plan may change, split or remove them,
and the waves that replace them take new indices. A wave that is `wip` or `done`, and
every wave of a frozen module, keeps its record, apart from the progress fields. A
planner may append waves to a frozen module, such as those that replace its raw seams
once a cut dependency has landed.

Each wave's batches are those wavefront packs from the units it schedules, under the
campaign's `workload` caps; a review wave's batches group the reviewed wave's batches
within the `review-workload` caps.

## 5. Derived paths

A batch's id, `wave-<index>/batch-<index>`, names its branch and worktree, and its wave
index the wave branch, as `specs/versioning.md` spells them. Its artifact dirs are those of the
agents that ran it, each holding a `task.json` that names the batch's wave and index.

## 6. Earlier versions

Schema-v2 schedules were one `crustify/artifacts/<link-unit>/<subsystem>/schedule.json`
per subsystem, whose wave indices counted within the subsystem and whose batches carried
an `objective` in place of `kind`. Schema-v1 was one campaign-wide schedule nesting
`link_units` → `subsystems` → `waves`. A campaign on either is converted by its next
planner run: its waves are numbered in the order they ran or were to run, every v2
`objective` becomes the batch's `kind`, and every wave's `subsystem` becomes the `module`
its units are re-decomposed into, as `specs/decomposition.md` describes.
