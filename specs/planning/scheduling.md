# Scheduling

Scheduling turns the campaign's [decomposition](decomposition.md) into the waves and
batches its agents execute, recorded in `crustify/artifacts/schedule.json`: the order the
modules run in, each wave's batches and the waves it depends on, and the kind of each
batch. Planner runs produce it with the decomposition, as the decomposition's Runs section
describes.

## 1. Order

The campaign's order is computed over the units of every module of the decomposition, each
module holding the units it owns, as [`../artifacts/modules.md`](../artifacts/modules.md)'s
file entries select them, and recorded in `schedule.json`'s `modules`, as
[`../artifacts/schedule.md`](../artifacts/schedule.md) describes. A module depends on the
modules its units depend on, and each of its dependencies is split into those ordered
before it, `depends_on.scheduled`, and those cut to break a cycle, `depends_on.cut`, so
that the scheduled dependencies form a DAG.

A cut puts a dependency after its user, which then reaches it through a binding: one per
distinct unit it puts after the user, however many edges reach that unit. Within each
strongly connected component of the modules, the module the most distinct units of the
others depend on, net of the distinct units of the others it depends on, comes first, and
every dependency on a module that comes later is cut. The modules are then layered by the
longest path over their scheduled dependencies, each module's `layer`. Each module's units
are ordered within it the same way, every edge counting once, and layered: each layer is
one of the module's waves, in `sublayer` order. Link units are ordered the same way.

Every unit the plan schedules belongs to a module: a unit no module owns is a gap in the
decomposition. Each planner run computes the order anew; the waves that have started keep
their records, as `schedule.md`'s Re-planning section describes. A cut dependency is never
reached through raw bindings: what a module uses of one is wrapped before it, as
[Wrap waves](#3-wrap-waves) describes.

The plan holds only the link units and modules the campaign's scope includes, without
those that a previous campaign completed. The foundational modules depend on no other, so
they run first.

## 2. Waves and batches

`schedule.json` follows [`../artifacts/schedule.md`](../artifacts/schedule.md); its layout
example is [`templates/schedule.json`](../../templates/schedule.json). Each wave records
the waves it depends on, split as modules' are into `scheduled` and `cut`: its module's
previous wave, and the waves that hold its items' dependencies, in its module or in the
modules ordered before it.

How the modules run is the settings' `module-concurrency` answer, in a wrap and a port
campaign alike:

- concurrent modules, the default: each wave belongs to one module, and each module's
  waves run one at a time, in `sublayer` order. Modules that do not depend on each other
  run at once, within the campaign's scope and as many at once as
  [`../operations/concurrency.md`](../operations/concurrency.md) describes: a module's
  run starts once the waves of other modules that its waves depend on have been
  integrated, as [`../operations/versioning.md`](../operations/versioning.md) describes,
  so that each module is finished, and can be shipped, as early as its dependencies
  allow; and
- merged waves: the waves of every module at the same `layer` and `sublayer` merge into
  one wave, each of its batches holding one module's units, and the waves run one at a
  time, in the order of their `layer` and `sublayer`. The modules then finish together,
  layer by layer.

A wave belongs to no module when the campaign has no decomposition. The batches of a wave
execute concurrently, as many at once as
[`../operations/concurrency.md`](../operations/concurrency.md) describes.

A wave's units are packed into batches under the campaign's `workload` caps, each batch
holding types or symbols: a type batch is bounded by its types and their fields, a symbol
batch by its symbols and their lines of code. Adjacent waves of a module fold into one
while their units fit one batch.

TODO: review waves, which follow each translation wave when review is enabled, as
[`../verification/reviewing.md`](../verification/reviewing.md)'s Review waves and batches
section describes, are not scheduled for now.

A `wrap` or `port` batch entry holds its `kind` and `items`, which its task carries as
`objective` and `items` ([`../artifacts/task.md`](../artifacts/task.md) gives their format and
routing). Each item's `home` follows the [conventions](../rust/conventions.md).

Type-erased and string lifecycle primitives are units of the foundational modules.
Typed lifecycle primitives stay in the schedule as free symbols, although the type
batches discover them on the fly; their binders skip them.

In a wrap campaign every batch is `wrap`.

TODO (porting): the scheduling of a port campaign, which this section and
[Porting types](#4-porting-types) describe, is to be reworked over the order above. In a
port campaign:

- a selected symbol is `port` from the start;
- a selected enum is `port`, where the DAG places it, and never `wrap`;
- a selected type is `port`, preceded by a `wrap` batch only while another module's
  unported C depends on its layout, as [Porting types](#4-porting-types) describes; and
- a dependency outside the selected migration set, or that has not been ported yet,
  is `wrap`.

An enum is a set of constants, with no fields, layout users or lifecycle for a binding to
publish, so no batch wraps it: a wrap campaign schedules none for it and uses its
generated `-sys` definition directly, as
[`../rust/items/binding.md`](../rust/items/binding.md)'s Type route section describes, and a port campaign
ports it once.

## 3. Wrap waves

A binding serves the code that consumes it, so wrap batches are scheduled lazily: right
before their first consumer, and only for what consumers use.

- TODO (porting): in a port campaign, each `port` wave is preceded by the `wrap` waves of
  the in-tree `wrap` modules it needs, the foundational ones included: an in-tree `wrap`
  module's waves are those that precede its consumers.
- In either campaign, a wave is preceded by `wrap` waves holding what its items use of
  the modules its module's cuts name, which run after it: a cut dependency is bound
  before its consumer, by a binder, rather than reached through raw bindings, and its
  module ports it later.
- In either campaign, the out-of-tree libraries a wave's items use are wrapped first in
  their side campaigns, as [`dependencies.md`](dependencies.md) describes: its module's
  `depends_on.external` records in `schedule.json` name each library and the entities
  the wave's items use of it. No entity of a library is a unit of the campaign's own
  schedule.

Wrapping an item brings in its own wrap dependencies, transitively: the types its
signature names, those of the fields its consumers access, and theirs in turn, closed
over the public-signature graph, which has no function bodies. A type none of whose
fields its consumers access is wrapped opaque, with its lifecycle primitives only, so
that the base it embeds is not brought in: its module extends it with that base when it
ports it. The closure stops at what an earlier wave has wrapped or ported, and may reach
into further modules that run later, whose items join wrap waves of their own modules.

A preceding wrap wave holds only what the waves after it need and no earlier wave
wrapped, so that no item is wrapped twice and an item no consumer needs is never wrapped.
It belongs to the module that owns its items, one wrap wave per module: a module's waves
may be preceded by waves of the modules they depend on, whose items keep their homes in
those modules. A type that a `port`
module owns and wraps first, as [Porting types](#4-porting-types) describes, is that
module's own work, not a preceding wrap wave's.

## 4. Porting types

TODO (porting): to be reworked with the scheduling of a port campaign.

A selected type's layout users are the target's C that depends on its layout. An enum
has none: using its constants or values of its type is no layout use, and it is ported as
[Waves and batches](#2-waves-and-batches) describes. A struct or a union has:

- code that touches a field: reads or writes it, or takes its address;
- code that depends on the layout without naming a field: `sizeof`, `_Alignof` or
  `offsetof` on the type (`sizeof *p`, and macros such as `container_of`, included); a
  value of the type, as a local, a parameter or return, a global, a copy or a compound
  literal; pointer arithmetic or indexing on a pointer to it; and
- another struct, or an array, that embeds it by value and so carries its layout.

No tool lists the second and third kinds: they are found in the source, in every
function that mentions the type, its globals and the struct fields declared with it,
macro expansions included.

Three kinds of C are not layout users, as [`../workflows/porting.md`](../workflows/porting.md)'s
Principles section describes: the type's own module, which switches to Rust in one
integration; the tests, which are gated with the modules whose internals they use; and C
outside the target, so that a definition in an installed header is no user either. A type
is then scheduled by its remaining users:

- with none, as when only pointers to it cross into other modules, it is `port` only, where
  the DAG places it;
- with layout users in other modules that are ported later, it is `wrap` where the DAG
  places it, and `port` in the first wave after the integration of the last of those
  modules; and
- with a layout user that stays C, in a `wrap` module or a struct that embeds it and stays
  C, it is `wrap` only, and keeps its C layout.
