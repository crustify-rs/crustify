# Planning

Planning turns a campaign's settings and the target's build into the plan its agents
execute: the subsystem decomposition, `crustify/artifacts/subsystems.json`, whose
dependencies order the campaign's link units and subsystems, the campaign's waves and
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

A campaign may be planned in several sessions, each for part of its scope: a whole
subsystem, a few of its waves, or a few named items. Each session's runs add what its
scope adds to the same plan: subsystems and link units with the next free indices, and
waves after the highest wave index. What is frozen, or has started, is kept as
[`artifacts/subsystems.md`](artifacts/subsystems.md) and
[`artifacts/schedule.md`](artifacts/schedule.md) describe. A run that corrects an earlier decision files a report on it, as
[`reviewing.md`](reviewing.md#9-plan-corrections) describes.

## 2. Subsystem decomposition

`subsystems.json` follows [`artifacts/subsystems.md`](artifacts/subsystems.md); its layout
example is [`templates/subsystems.json`](../templates/subsystems.json).

Link units are identified from the actual linker outputs. The decomposition covers the
selected target and its complete imported producer closure. Every translation unit
belongs to exactly one subsystem, unless an item-granular subsystem takes some of its
items; a header may be shared by several. A subsystem's
`api_headers` are the headers the build installs, listed with the subsystem that
implements them.

Each subsystem carries one objective:

- `port`: project-specific behaviour or invariants, implemented in Rust;
- `wrap`: generic facilities, kept behind a safe Rust API over the C.

A mixed subsystem is split, so that its project-specific code and its generic facilities
carry separate objectives. In a wrap campaign every subsystem is `wrap`. In a port
campaign the project-specific subsystems are `port`, and those with Rust-native
alternatives stay `wrap`, so that their Rust consumers stay interoperable with the
remaining C during an incremental translation, until they can be nativized. A subsystem's
`rust_native_equivalent` lists the established Rust crates or `std` facilities that could
replace it outright, in descending order of fit, each checked for its semantics,
platform support, performance and licensing.

Each consumer-to-producer relation is one `imported_deps` record, with its
`outgoing_edges`, its `incoming_edges` and the item kinds consumed across them, in-tree
destinations apart from out-of-tree libraries. The record keeps the graph as it is,
cycles included.

### 2.1 Foundational subsystems

The decomposition opens with two foundational subsystems, `void` and `string`, that every
other subsystem may depend on:

- `void` holds the allocators, releasers, disposers and cloners of type-erased memory,
  with the units that share their definitions; and
- `string` holds the units whose text pointers, the pointers that refer to
  NUL-terminated strings, depend on nothing but `void`.

Their members are selected from the dependency graph with each type-erased value
resolved to the types it is read as, so that a `void *` read as a named type is a
dependency on that type, not an erased value. What
stays erased is a candidate, admitted only once its body has been read. A foundational subsystem may keep a few dependencies of its own, such as
logging or assertions on its failure paths, which the order cuts; otherwise nothing it
holds depends on another subsystem.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
established while planning, so that these subsystems' members are bound as strategies, as [Lifecycle strategies](binding.md#54-lifecycle-strategies) describes.

A foundational subsystem owns whole files where its members make up their files, and
narrows to its `items` where they share a file with another subsystem, as
[`artifacts/subsystems.md`](artifacts/subsystems.md) describes. The foundational
subsystems are planned and scheduled like any other: waves of batches of units. As
generic facilities, they are `wrap` in every campaign.

## 3. Order

The campaign's order is computed from the dependencies `subsystems.json` records, as
[`artifacts/subsystems.md`](artifacts/subsystems.md) describes: each subsystem's in-tree
dependencies are split into those that run before it, `depends_on.scheduled`, and those
cut to break a cycle, `depends_on.cut`, so that the scheduled dependencies form a DAG.
Within each strongly connected component, the member the most other members depend on
comes first, and the edges between tied members break ties: every dependency on a member
that comes later is cut. Link units are ordered the same way.

A frozen subsystem keeps its place: a subsystem added after it that it depends on is one of
its cuts, and the waves that replace the raw seams of each cut are scheduled once the
dependency it cut is planned, depending on that dependency's last wave.

The plan holds only the link units and subsystems the campaign's scope includes, without
those that a previous campaign completed. The foundational subsystems are the first link
unit's first two, `void` then `string`, and depend on no other, so they run first.

## 4. Waves and batches

`schedule.json` follows [`artifacts/schedule.md`](artifacts/schedule.md); its layout
example is [`templates/schedule.json`](../templates/schedule.json). Each wave belongs to
one subsystem, or to none when the campaign has no decomposition, and records the waves it
depends on, split as subsystems' are into `scheduled` and `cut`: within a subsystem, the
dependency order of its units; across subsystems, the subsystems' order, so that a wave
depends on the last waves of the subsystems its units depend on. Waves execute one at a
time, in that order; the batches of a wave execute in parallel, up to the campaign's
parallelism, and the `workload` caps bound each batch.

When review is enabled, each translation wave is followed by a review wave, whose batches
group the reviewed wave's batches as [`reviewing.md`](reviewing.md)'s Review waves and
batches section describes, within the `review-workload` caps.

A `wrap` or `port` batch entry holds its `kind` and `items`, which its task carries as
`objective` and `items` ([`artifacts/task.md`](artifacts/task.md) gives their format and
routing). Each item's `home` follows the [conventions](conventions.md).

Type-erased and string lifecycle primitives are units of the foundational subsystems.
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
