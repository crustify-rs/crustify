---
name: scheduling
description: "How modules become waves and batches in schedule.json: order and cuts, waves, batch packing, wrap batches ahead of consumers, later port stages. Read before scheduling, packing a wave's batches or wrapping dependencies ahead."
---

# Scheduling

Scheduling turns the campaign's [decomposition](../decomposition/SKILL.md) into the waves and
batches its agents execute, recorded in `crustify/artifacts/schedule.json`: the order the
modules run in, each wave's items and the waves it depends on, and the objective of each
item. Planner runs produce the waves with the decomposition, as the decomposition's Runs
section describes. A wave's batches are packed when it starts, as [Batches](#3-batches)
describes, and recorded as its progress.

## 1. Order

The campaign's order is computed over the units of every module of the decomposition, each
module holding the units it owns, as [`modules-schema`](../../artifacts/modules-schema/SKILL.md)'s
file entries select them, and recorded in `schedule.json`'s `modules`, as
[`schedule-schema`](../../artifacts/schedule-schema/SKILL.md) describes. A module depends on the
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
their records, as [`schedule-schema`](../../artifacts/schedule-schema/SKILL.md)'s Re-planning section describes. A cut dependency is never
reached through raw bindings: what a module uses of one is wrapped before it, as
[Wrap batches](#4-wrap-batches) describes.

The plan holds only the link units and modules the campaign's scope includes.
The foundational modules depend on no other, so they run first.

## 2. Waves and batches

`schedule.json` follows [`schedule-schema`](../../artifacts/schedule-schema/SKILL.md); its layout
example is [`templates/schedule.json`](../../../templates/schedule.json). Each wave records
the waves it depends on, split as modules' are into `scheduled` and `cut`: its module's
previous wave, and the waves that hold its items' dependencies, in its module or in the
modules ordered before it.

Each wave belongs to one module, and each module's waves run one at a time, in
`sublayer` order, in a wrap and a port campaign alike. Modules that do not depend on each
other run at once, within the campaign's scope and as many at once as
[`concurrency`](../../operations/concurrency/SKILL.md) describes: a module's run
starts once the waves of other modules that its waves depend on have been integrated, as
[`versioning`](../../operations/versioning/SKILL.md) describes, so that each
module is finished, and can be shipped, as early as its dependencies allow.

A wave belongs to no module when the campaign has no decomposition. The batches of a wave
execute concurrently, as many at once as
[`concurrency`](../../operations/concurrency/SKILL.md) describes.

A wave lists its items, each with the objective it is translated with, `wrap` or `port`,
its route and its `home`, which follows the [conventions](../../rust/conventions/SKILL.md). The
items of one wave do not depend on one another, so how they are grouped changes neither
the order nor what any of them can rely on: a wave's batches are not planned, but packed
when it starts, as [Batches](#3-batches) describes.

Type-erased and string lifecycle primitives are units of the foundational modules.
Typed lifecycle primitives stay in the schedule as free symbols, as
[`binding`](../../rust/binding/SKILL.md)'s Type route section describes.

In a wrap campaign every item is `wrap`. In a port campaign, the items of the foundational
modules are `wrap`, and those of every other module `port`: a symbol, a callback or an
enum where the order places it, a struct or a union `wrap` there while another module's C
uses its layout, and each followed by the later stages
[Later stages](#5-later-stages) describes, each a planned item of its own.

Nothing wraps an enum, as [`binding`](../../rust/binding/SKILL.md)'s Type route section
describes: a wrap campaign schedules none for it, and a port campaign ports it once.

## 3. Batches

A wave's batches are packed when it starts, from the state of the campaign at that
moment, and packed again as its batches land or fail. Each batch holds items of one
objective and one route, as [`task-schema`](../../artifacts/task-schema/SKILL.md)'s Routes
section describes: types, or symbols and callbacks.

A batch is sized so that its agent carries every item through its analysis, its tests and
its gates within one session, without its context running out, and so that what it lands
stays within what one review can follow. That size follows from:

- the items: a type's fields, its pointer fields above all, each of whose accessors
  follows from the analysis; a symbol's lines, its pointer parameters and returns, its
  callbacks and the type-erased values it hands on; and, in a foundational module, the
  lifecycle roles its items' strategies implement;
- the agent: its model, its context window and its effort;
- the campaign so far: which of the batches before it landed in one run, and which failed
  or ran out of context; and
- the host: how many agents run at once, as
  [`concurrency`](../../operations/concurrency/SKILL.md) describes, since fewer,
  larger batches share their analysis and more, smaller ones finish sooner.

The settings' `workload` answer, when it sets one, caps every batch: its types
(`max-types`), its symbols (`max-syms`) and their lines (`max-loc`).

Consecutive waves of a module, in index order, may share batches when every dependency
chain between their items stays within one batch: a batch that holds an item of a later
wave also holds every item of the earlier waves it depends on that has not landed. The
waves are folded so when they start, and the plan's order on disk stays as planned. Waves
that share batches land on the first one's integration branch, and are promoted
together.

An item that has landed is not packed again: an item a [wrap batch](#4-wrap-batches) bound
ahead of its consumer is dropped from its own wave in a wrap campaign, and keeps only its
`port` in a port campaign. A batch that fails may be packed again, its items into new
batches of its wave.

Review batches are packed the same way, from the landed batches they review, under the
`review-workload` caps when the settings set them, and larger than translation batches, as
[`reviewing`](../../verification/reviewing/SKILL.md)'s Review batches section
describes.

## 4. Wrap batches

A binding serves the code that consumes it, so what a batch's items use is wrapped right
before the batch, and only what they use. Before a batch launches, every unit its items
depend on has landed: in an earlier wave, or in a wrap batch of the batch's own wave that
lands before it. What has not landed is wrapped by such a batch:

- a cut dependency, which the order puts after its user: it is bound before its consumer,
  by a `wrap` batch, rather than reached through raw bindings, and its own wave ports it later
  or, in a wrap campaign, finds it bound;
- a dependency of a wave run before the waves that hold it, or of a part of the scope
  run without them; and
- in a port campaign, what a `port` batch uses of a module the scope leaves out, whose C
  stays.

Wrapping an item brings in its own wrap dependencies, transitively: the types its
signature names, those of the fields its consumers access, and theirs in turn, closed
over the public-signature graph, which has no function bodies. A type none of whose
fields its consumers access is wrapped opaque, with its lifecycle primitives only, so
that the base it embeds is not brought in: its module extends it with that base when it
ports it. The closure stops at what has landed, and may reach into further modules that
run later.

A wrap batch ahead of its consumer holds only what has not landed, so that no item is
wrapped twice and an item no consumer needs is never wrapped. Its items keep their homes
in the modules that own them, and it lands on its consumer's wave branch before the
consumer's batches launch. A type that a `port` module owns and wraps first, as
[Later stages](#5-later-stages) describes, is that module's own work, in its own waves.

What a wave's items need through an out-of-tree library's wrapper is wrapped first in the
library's side campaign, before the wave starts, as [`dependencies`](../dependencies/SKILL.md)'s
Side campaigns section describes, judged from the libraries and entities its module's
`depends_on.external` records in `schedule.json` name. No entity of a library is a unit of
the campaign's own schedule.

## 5. Later stages

In a port campaign, part of an entity's work waits until the remaining C no longer needs
its C form. Each such stage is a planned item of its own, with the stage as its objective,
in a wave that depends on the last waves of the modules whose integration frees it, so
that it runs once they are integrated and the entity takes its Rust form as soon as the C
lets it. The later stages the same integrations free share a wave, whose batches are
packed when it starts, as [Batches](#3-batches) describes, a stage's
items forming batches of their own, by its objective.

### 5.1 Types

A struct's or a union's layout users are the target's C that depends on its layout:

- code that touches a field: reads or writes it, or takes its address;
- code that depends on the layout without naming a field: `sizeof`, `_Alignof` or
  `offsetof` on the type (`sizeof *p`, and macros such as `container_of`, included); a
  value of the type, as a local, a parameter or return, a global, a copy or a compound
  literal; pointer arithmetic or indexing on a pointer to it; and
- another struct, or an array, that embeds it by value and so carries its layout, whose
  own layout users are the type's too.

Its memory users are the target's C that hands its storage to C's allocator: code that
allocates it with an allocator of untyped memory, or frees or disposes of it with a
releaser of untyped memory. Its own constructors, destructors and cloners are no memory
users: the C that calls them reaches them as any other function. An enum has neither kind
of user: using its constants or values of its type is no use of a layout.

Each kind is found in every function that mentions the type, its globals and the struct
fields declared with it, macro expansions included. Three kinds of C are no users, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section describes: the
type's own module, which switches to Rust in one integration; the tests, which are tied to
the modules whose subject they are; and C outside the target, so that a definition in an
installed header is no user either. Of the users of other modules, the last are those no
other user depends on, over the order's scheduled dependencies: every other user's module
is integrated before theirs starts, so a stage waits for theirs alone. A type's release
points name them: `opaque_after` its last layout users, `memory_unmanaged_after` its last
memory users.

A type is scheduled in stages:

1. `port` where the order places it when no layout user of another module remains, and
   `wrap` otherwise, so that the type keeps its C layout behind its safe API. A consumer
   ported earlier that needs it has it wrapped ahead, as [Wrap batches](#4-wrap-batches)
   describes;
2. `port/layout`, after its `opaque_after`: the type takes a Rust-native layout; and
3. `port/memory`, after its `memory_unmanaged_after`: its storage moves from C's
   allocator, which its owners allocate and free through until then, to Rust's.

A stage with no users to wait for is not planned: its change is part of the type's `port`.
A user that stays C, in a foundational module, in a module the scope leaves out or in a
struct that embeds the type and stays C, keeps the stage it holds back from being planned
at all: the type keeps its C layout, or its storage in C's allocator, for good.

Its safe API does not change between the stages: it exposes no representation, so that a
stage changes the type, its lifecycle and the code inside the crate that reaches its C form,
and none of its consumers.

### 5.2 Functions and globals

A ported function's or global's export, through which the remaining C reaches it, is
removed with the raw binding that reaches it by a `port/unexport` item, after its
`unreferenced_after`: the integration of its last referrers, the remaining C that calls it,
takes its address or accesses it, as the [conventions](../../rust/conventions/SKILL.md)' Exports
section describes. A function or global that remaining C never references has no export,
and no `port/unexport`.
