# Planning

Planning turns a campaign's settings and the target's build into the plan its agents
execute: the module decomposition, `crustify/artifacts/modules.json`, whose
dependencies order the campaign's link units and modules, the campaign's waves and
batches in `crustify/artifacts/schedule.json`, and the planning artifacts of the enabled
skills.

A plan is bounded by the campaign's settings in `crustify/CRUSTIFY.md`: its `campaign`
(port or wrap), `scope`, `target-config` and `workload` answers. A feature the target is
configured without is out of scope. The plan derives from the builds recorded in
`crustify/artifacts/build.json` and the linker outputs of those builds; planning changes
neither the build nor the Rust tree.

## 1. Runs

A campaign is planned by one or more planner runs, one after another, each in one commit
on its own branch, `crustify/planner/run-<n>`, forked from the working branch's tip and
checked out in the repository's base dir. Once the run has committed, the working branch
is fast-forwarded to it, and the next run forks from there. Each run brings the committed
plan up to date, so a later run checks what the earlier ones decided, and the branch
history records every planning decision and its revisions.

A campaign may be planned in several sessions, each for part of its scope: a few modules,
a few of their waves, or a few named items. Each session's runs add what its scope adds to
the same plan: modules and link units with the next free indices, and
waves after the highest wave index. What is frozen, or has started, is kept as
[`artifacts/modules.md`](artifacts/modules.md) and
[`artifacts/schedule.md`](artifacts/schedule.md) describe. A run that corrects an earlier decision files a report on it, as
[`reviewing.md`](reviewing.md#9-plan-corrections) describes.

## 2. Module decomposition

`modules.json` follows [`artifacts/modules.md`](artifacts/modules.md); its layout example
is [`templates/modules.json`](../templates/modules.json).

The C codebase is the decomposition's spec. A module is one translation unit with the
headers it defines its items in, so that the plan follows how the codebase is organized
rather than a judgement of how it should be, and the Rust tree mirrors it, as the
[conventions](conventions.md)' Crates, modules, and TUs section describes. Dependencies
between modules are what the C has: the decomposition does not group files to hide them.

Link units are identified from the actual linker outputs. The decomposition covers the
selected target and its complete imported producer closure: every translation unit the
build compiles in scope is a module's, or is listed as configured out.

### 2.1 Bundling

Each translation unit is bundled with the headers that carry its name, internal or
installed: `src/libgit2/repository.c` with `src/libgit2/repository.h`,
`include/git2/repository.h` and
`include/git2/sys/repository.h`. An item of such a header that belongs to another TU, in
the rare case one does, is homed with that TU.

A shared header, one that carries no single TU's name, is split item by item:

- a type goes to the TU that implements its lifecycle and its functionality;
- a global goes to the TU that implements its logic; and
- a `static inline` function goes to the module whose logic it implements, as the
  functions it calls and the types it accesses show.

A header that implements what no TU does, and so has no TU to go to, is a header module of
its own. Each split is recorded with the file entries' `items` lists, which stay empty for
a file a module owns whole. Macros are not homed: they are not translated, and a binding
that needs one reaches it as [`binding.md`](binding.md)'s Macros section describes.

### 2.2 Dependencies

Each module's dependency edges are found with a wavefront configuration of its own, which
names its files and the items it owns. The edges from a module to another are one record
of its `depends_on`, with its `outgoing_edges`, its `incoming_edges` and the item kinds
consumed across them, and each out-of-tree library it uses is one record of its own. An
out-of-tree library's record also names the crates that port it to Rust and the crates that
bind it safely, with their feature parity, so that a port reaches it through one of them
rather than through raw bindings when they exist. The records keep the graph as it is,
cycles included, split as [Order](#3-order) describes.

### 2.3 Objectives

A module's `rust_equivalent` records what the Rust standard library provides in place of
the module as a whole, and the established crates that could replace it outright, each
with its feature parity, in descending order of it, and each checked for its semantics,
platform support, performance and licensing.

Each module carries one objective, which follows from its `rust_equivalent` rather than
from a judgement of what the module is:

- `wrap` when the standard library or a crate has `full` feature parity with it: the C is
  kept behind a safe Rust API, so that its Rust consumers stay interoperable with the
  remaining C during an incremental translation, until the module is replaced by that
  equivalent; and
- `port` otherwise, when the best equivalent is `partial` or there is none: the module is
  reimplemented in safe Rust, using its partial equivalents where they serve.

The foundational modules are `wrap` whatever their equivalents, as
[Foundational modules](#24-foundational-modules) describes. In a wrap campaign every module
is `wrap`. A TU is not split for its objective.

### 2.4 Foundational modules

The foundational modules are those whose items every other module may depend on: the
TUs that define the allocators, releasers, disposers and cloners of type-erased memory,
and those whose text pointers, the pointers that refer to NUL-terminated strings, depend
on nothing but the type-erased ones. A codebase may have several of each, wherever its
lifecycle routines are defined.

Their members are selected from the dependency graph with each type-erased value resolved
to the types it is read as, so that a `void *` read as a named type is a dependency on that
type, not an erased value. What stays erased is a candidate, admitted only once its body
has been read. A foundational module depends only on other foundational modules, apart
from a few dependencies such as logging or assertions on its failure paths, which the
order cuts. The order then runs them first, and among them the type-erased ones before the
string ones that call them.

A TU whose items all meet that test is foundational whole. One that also holds items that
depend on other modules is split in two: its foundational module lists the TU with the
lifecycle routines and what they need within it as `included`, and the other module
lists the same items as `excluded`. The two share the TU's path as their name, and are
told apart by their `index` and `foundational`. Both home in the TU's Rust file.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
established while planning, so that the foundational modules' members are bound as
strategies, as [Lifecycle strategies](binding.md#54-lifecycle-strategies) describes. The
foundational modules are planned and scheduled like any other: waves of batches of units.
They are `wrap` in every campaign: their members become the lifecycle strategies that the
other modules' bindings release through, and while any C remains it allocates and frees
through them.

## 3. Order

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

## 4. Waves and batches

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
- a selected type is `wrap` while C depends on its layout, then `port` once nothing in C
  does, as [Porting types](#41-porting-types) describes; and
- a dependency outside the selected migration set is `wrap`.

### 4.1 Porting types

A selected type is scheduled twice: a `wrap` batch where the DAG places it, and a `port`
batch once its layout leaves C, when no C code that remains after a wave depends on it.
Its C users are:

- code that touches a field: reads or writes it, or takes its address;
- code that depends on the layout without naming a field: `sizeof`, `_Alignof` or
  `offsetof` on the type (`sizeof *p`, and macros such as `container_of`, included); a
  value of the type, as a local, a parameter or return, a global, a copy or a compound
  literal; pointer arithmetic or indexing on a pointer to it; and
- another struct, or an array, that embeds it by value and so carries its layout.

No tool lists the second and third kinds: they are found in the source, in every
function that mentions the type, its globals and the struct fields declared with it,
macro expansions included.

The `port` batch goes in the first wave after the one that ports the type's last C user.
A type keeps only its `wrap` batch, and its C layout, while a C user stays: one outside
the selected migration set, an embedding struct that stays C, or a definition in an
installed header, whose concrete body every public C consumer receives.
