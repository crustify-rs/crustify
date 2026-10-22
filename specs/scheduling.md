# Scheduling

Scheduling turns the campaign's [decomposition](decomposition.md) into the waves and
batches its agents execute, recorded in `crustify/artifacts/schedule.json`: the order the
modules run in, each wave's batches and the waves it depends on, and the kind of each
batch. Planner runs produce it with the decomposition, as the decomposition's Runs section
describes.

## 1. Order

The campaign's order is computed from the dependencies `modules.json` records, as
[`artifacts/modules.md`](artifacts/modules.md) describes: each module's in-tree
dependencies are split into those that run before it, `depends_on.scheduled`, and those
cut to break a cycle, `depends_on.cut`, so that the scheduled dependencies form a DAG.
Within each strongly connected component, the member the most other members depend on
comes first, and the edges between tied members break ties: every dependency on a member
that comes later is cut. Link units are ordered the same way. Modules run one at a time.

A frozen module keeps its place: a module added after it that it depends on is one of its
cuts, and the waves that replace the raw seams of each cut are scheduled once the
dependency it cut is planned, depending on that dependency's last wave.

The plan holds only the link units and modules the campaign's scope includes, without
those that a previous campaign completed. The foundational modules depend on no other, so
they run first.

## 2. Waves and batches

`schedule.json` follows [`artifacts/schedule.md`](artifacts/schedule.md); its layout
example is [`templates/schedule.json`](../templates/schedule.json). Each wave belongs to
one module, or to none when the campaign has no decomposition, and records the waves it
depends on, split as modules' are into `scheduled` and `cut`: within a module, the
dependency order of its units; across modules, the modules' order, so that a wave depends
on the last waves of the modules its units depend on. Waves execute one at a
time, in that order; the batches of a wave execute in parallel, up to the campaign's
parallelism, and the `workload` caps bound each batch.

When review is enabled, each translation wave is followed by a review wave, whose batches
group the reviewed wave's batches as [`reviewing.md`](reviewing.md)'s Review waves and
batches section describes, within the `review-workload` caps.

A `wrap` or `port` batch entry holds its `kind` and `items`, which its task carries as
`objective` and `items` ([`artifacts/task.md`](artifacts/task.md) gives their format and
routing). Each item's `home` follows the [conventions](conventions.md).

Type-erased and string lifecycle primitives are units of the foundational modules.
Typed lifecycle primitives stay in the schedule as free symbols, although the type
batches discover them on the fly; their binders skip them.

In a wrap campaign every batch is `wrap`. In a port campaign:

- a selected symbol is `port` from the start;
- a selected enum is `port`, where the DAG places it, and never `wrap`;
- a selected type is `port`, preceded by a `wrap` batch only while another module's
  unported C depends on its layout, as [Porting types](#3-porting-types) describes; and
- a dependency outside the selected migration set is `wrap`.

An enum is a set of constants, with no fields, layout users or lifecycle for a binding to
publish, so no batch wraps it: a wrap campaign schedules none for it and uses its
generated `-sys` definition directly, as
[`items/binding.md`](items/binding.md)'s Type route section describes, and a port campaign
ports it once.

## 3. Porting types

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

Three kinds of C are not layout users, as [`workflows/porting.md`](workflows/porting.md)'s
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
