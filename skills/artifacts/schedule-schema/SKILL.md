---
name: schedule-schema
description: "The fields of schedule.json: modules, waves, items, batches, progress, indices and re-planning. Read before writing or reading schedule.json."
---

# schedule.json schema

Field meaning for `<workdir>/crustify/artifacts/schedule.json`, the campaign's module
order, waves and batches. Layout examples: [`templates/schedule.json`](../../../templates/schedule.json), and a port
campaign's, [`templates/schedule.port.json`](../../../templates/schedule.port.json).

The campaign has one schedule, which every planner run extends: the first run creates it,
and each later one appends the waves its scope adds and re-plans the waves that have not
started. Waves are computable in advance, so writing them down makes a campaign's shape
reviewable before it spends anything; their batches are not, since they are packed when
each wave starts, as `scheduling`'s Batches section describes.

An audit's review waves are not recorded in it.

The schedule holds two kinds of field:

- the plan: the order of the modules, the waves, their dependencies and their items,
  decided by planning; and
- the progress: each wave's `status` and `packed_with`, and its `batches`, each with its
  worklist, `status` and `commits`, recorded as the work launches and lands.

| root field | meaning |
|---|---|
| `schema_version` | `6` |
| `modules` | the order of the campaign's modules, one record per module the schedule holds waves of, by `layer` |
| `waves` | the campaign's waves, in `index` order |

## 1. modules[*]

The order of the modules is computed over every module of the decomposition, as
`scheduling`'s Order section describes, and recorded here, with the
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
| `items` | on a cut record: each edge it cuts, as `from` (this module's unit), `to` (the other module's unit), each `{name, defined_in}`, and the `kind` of `to`, as an item's |

An out-of-tree record names the library its units use, by its `library`, a
`libraries[*].name` of `dependencies.json`, and counts what they use of it, with the
`unique_edges` and `total_edges` of a dependency record and every edge in its `items`, as
on a cut record: `to` is the library's entity, by the name and the defining header its
users reference. No entity of the library is a unit of this schedule: its side campaign
wraps it, before the first wave that holds a `from` of the record, as
`dependencies`'s Side campaigns section describes.

`scheduled` alone is acyclic across the schedule, and with `cut` it is every module this
one depends on. A planner run rewrites `modules` from its order; the waves that have
started keep their records, as [Re-planning](#5-re-planning) describes.

## 2. waves[*]

| field | meaning |
|---|---|
| `index` | the wave's id, from zero; see [Indices](#4-indices) |
| `link_unit` | the `link_units[*].name` of `modules.json` its units belong to |
| `module` | the module's `name` within that link unit |
| `foundational` | the module's `foundational` |
| `layer` | its module's `layer`; `null` when the campaign has no decomposition |
| `sublayer` | its place among its module's waves, from 0; `null` when the campaign has no decomposition |
| `status` | `todo`, `wip` or `done` |
| `depends_on` | the waves this one depends on: `scheduled` and `cut`, each an array of wave indices |
| `items` | the wave's items, each a planned item below |
| `packed_with` | the index of the earlier wave whose batches hold this wave's items, when the two share batches; `null` otherwise |
| `batches` | the wave's batches, which execute in parallel; empty until the wave starts |

A planned item is a batch item, as `task-schema` describes its `items`, with
the objective it is translated with and its entity's release points:

| field | meaning |
|---|---|
| `name`, `defined_in`, `kind`, `field_users`, `typedefs`, `home` | as on a batch item |
| `objective` | `wrap` or `port`, or one of the later stages of `scheduling`'s Later stages section: `port/layout` or `port/memory` for a struct or a union, `port/layout` for a closed enum, `port/unexport` for a function, a global or a function pointer |
| `opaque_after` | on a struct, a union or an enum, the release point after which none of its layout users is left, as the scheduling spec's Later stages section defines them; `null` on any other item |
| `memory_unmanaged_after` | on a struct or a union, the release point after which none of its memory users is left; `null` on any other item |
| `unreferenced_after` | on a function, a global, a macro, a function pointer or a typedef, the release point after which none of its referrers is left, and for a function pointer written inline none of what reaches the sites that write it; `null` on any other item |
| `carries_over` | on a `port/unexport` item, the C test cases and harness code still referencing its export when its wave runs, in the plan's order, below; absent on every other objective |

A release point has two records, `closure` over every user and `scheduled` over those the
schedule holds, each naming the last users, their waves and their `modules`, as the
planning tools compute them. An entity's planned items carry the same release points. The
wave of a later stage lists, among its `depends_on.scheduled`, the last wave of each module
its release point's `closure.modules` names but the item's own, so that it runs once those
modules have switched: `opaque_after` for `port/layout`, `memory_unmanaged_after` for
`port/memory`, and `unreferenced_after` for `port/unexport`.

A `port/unexport` item's `carries_over` records what of the target's C tests its stage
carries over and removes from `c/`, as `scheduling`'s Later stages section describes:

| `carries_over` field | meaning |
|---|---|
| `cases` | the test cases still referencing the export when the wave runs, each `{path, tests}`: the test file and its test case names |
| `if_still_in_c` | the cases, shaped as `cases`, that reference the export but that the plan's order removes before the wave, by a module's switch or another wave's carry-over it does not depend on: the stage carries over those still in `c/` when it runs |
| `harness` | the functions of the test harness, as `file:function`, that reference the export, which the stage adapts |

The plan's order on disk decides which wave carries over a case several of them
reference: the first by index that runs after the case's last chance to leave otherwise.
A wave whose dependencies let it run earlier carries over what is still in `c/` when it
runs, which its batch checks against the record.

`depends_on.scheduled` lists the waves that complete before this one: its module's
previous wave, and the waves that hold its items' dependencies. `depends_on.cut` lists the
waves that hold its items' cut dependencies, which run after it; it reaches what they hold
through the safe wrappers a wrap batch before it adds, as `scheduling`'s
Wrap batches section describes. Their union is every wave this one depends on, and
`scheduled` alone is acyclic across the schedule.

Every wave belongs to one module, as `scheduling` describes.

A wave is `todo` until its first batch launches, `wip` while any of its batches is
running or has failed, and `done` once every batch has landed and the wave has been
promoted. A wave `packed_with` another has no batches of its own: its `status` follows
that wave's, and it lands on that wave's integration branch.

## 3. waves[*].batches[*]

| field | meaning |
|---|---|
| `index` | the batch's id within its wave, from zero |
| `link_unit`, `module`, `foundational` | the module whose units it holds, as for its wave; `null`, `null` and `false` when the campaign has no decomposition |
| `kind` | an objective of its items, as a planned item's, or `review` |
| `status` | `todo`, `wip`, `done` or `failed` |
| `items` | a translation batch's worklist, as `task-schema` describes its `items` |
| `reviews` | a `review` batch's worklist: the indices of the batches of its wave it reviews; empty in a module pass |
| `module_pass` | optional, `false` when absent: `true` on the `review` batch that reviews its module whole, the last batch of the last wave of its `wrap` and `port` items, as `reviewing`'s Review batches section describes |
| `commits` | the commits the batch landed, in order; empty until it lands |

The batches are packed when the wave starts, and added as it runs: a batch that fails may
be packed again into new batches, which take the next free indices, and review batches are
added as the batches they review land, as `reviewing` describes. A
batch's items are those of its wave, of the waves `packed_with` it, or, in a wrap batch
that binds what its consumers need ahead of them, items of other modules, which keep
their homes there, as `scheduling`'s Wrap batches section describes.
Its `link_unit`, `module` and `foundational` are always its wave's.

A batch is `todo` until its agent launches, `wip` while an agent runs it, `done` once it
has landed every item of its worklist, and `failed` when its last agent ended without
landing. An item's status is that of the batch that holds it: a planned item is translated
once a batch holding it with its objective is `done`.

A batch's `commits` are its landing's commits as they sit on its wave branch, which a
promotion fast-forwards without rewriting them.

## 4. Indices

A started wave's `index` is its permanent id: its branch, the batch ids
`wave-<index>/batch-<index>` and the run dirs are named from it, so it is never reused,
renumbered or moved, and they keep identifying the same work.

A `todo` wave's index names nothing yet. Each planner run numbers the `todo` waves after
the highest index of a started wave, from the next integer, in one topological order of
their `depends_on.scheduled`, with no gaps, renumbering their `depends_on` with them. The
indices of the `todo` waves are therefore their order: the plan is one total order on
disk, which the waves follow as they start, as many at once as their dependencies and the
host allow, and which folding waves into shared batches when they start, as
`scheduling`'s Batches section describes, leaves as it is.

## 5. Re-planning

Only waves that are `todo` are re-planned: a re-plan may change, split or remove them,
and the waves that replace them are numbered with the other `todo` waves, as
[Indices](#4-indices) describes. A wave that is `wip` or `done` keeps
its record, apart from the progress fields, and is never revisited, and its items are not
scheduled again. An item a batch has landed with its objective, such as one bound ahead of
its consumer, is not scheduled again with that objective. A frozen module's waves that are
`todo` are re-planned like any other, within its frozen decomposition, and waves may be
appended to it, such as those a module added after it calls for. A change of the
settings' `campaign` answer unfreezes every module, as `modules-schema`'s
Status section describes, and every `todo` wave is re-planned under the new kind.

## 6. Derived paths

A batch's id, `wave-<index>/batch-<index>`, names its branch and worktree, and its wave
index the wave branch, as `versioning` spells them, and with its module its run dirs and
reviews dir, as `layout` spells them, each run's `task.json` naming the batch's wave and
index.
