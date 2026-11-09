---
name: modules-schema
description: "The fields of modules.json. Read before writing or reading modules.json."
---

# modules.json schema

Field meaning for `<workdir>/crustify/artifacts/modules.json`, the campaign's
decomposition. Layout example: [`templates/modules.json`](../../../templates/modules.json).

Planning emits this repo-tier artifact: the first run creates it, and every run adds what
it lacks and corrects what earlier runs decided, apart from what a frozen module records.
It describes the modules the user's scope selects and every module in their producer
closure.

A module is one translation unit with the headers it defines its items in, as
`decomposition` describes. The decomposition follows the
C codebase rather than a judgement of how it is organized: a module exists because a TU,
or a header that implements what no TU does, exists. It is also the shape the Rust tree
mirrors, as `conventions` describes: there is no second placement document.

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision — a commit, not a counter. What this decomposition describes, pinned |
| `link_units` | the campaign's link units, in `index` order |

## 1. Indices and order

`index` identifies a link unit, and a module within its link unit; it is not a position.
Each run numbers the link units and modules it adds after the highest index already used,
so an index is never reused or renumbered.

A module's `depends_on` records every dependency it has, as
[Dependencies](#8-link_unitsmodulesdepends_on) describes. The order of the modules is not
recorded here: it is computed from their units' dependencies and recorded in
[`schedule.json`](../schedule-schema/SKILL.md)'s `modules`, with the dependencies it keeps and those it
cuts, as `scheduling`'s Order section describes.

A foundational module depends on foundational modules only, so every foundational module
is ordered before any other, and those whose items depend on others' after them: the
modules of string lifecycle routines after those of the type-erased allocators they call.

## 2. Status

A module's `status` is its decomposition's: `todo` while it may still change, and
`frozen` from the launch of its first wave, of any kind, or earlier when the user freezes
it, since that wave homes items in the module's file. A frozen module's decomposition, its
file entries and the homes of its items, and its place in the order, change only when the
user asks: a re-plan neither re-decomposes nor re-homes it, and moves no item into or out
of it. What is derived from the code and the current rules, its `tests`, `depends_on`,
`counters` and `objective`, follows them in every run, frozen or not.

A change of the settings' `campaign` answer, from `wrap` to `port` or back, unfreezes every
module: each is `todo` again, and the next planner run may re-decompose, re-home and
re-order the modules under the new kind. What has landed stays landed: an item whose home
the new decomposition changes keeps its code, which moves to the new home before the next
wave starts.

Freezing a module does not freeze its schedule: its waves that are `todo` may still be
re-planned, and waves appended to it whenever a consumer needs more of it, as
[`schedule-schema`](../schedule-schema/SKILL.md)'s Re-planning section describes. A module's progress is not
recorded here: it is its waves' `status` in `schedule.json`.

## 3. link_units[*]

Each entry's `name` is its identifier; clients may build a name index without losing the
order.

| field | meaning |
|---|---|
| `index` | the link unit's id in the campaign, from zero |
| `name` | unique link-unit identifier, normally the linked artifact's filename stem |
| `kind` | `library` or `executable` |
| `linkage` | `shared` or `static` for a library; `null` for an executable |
| `depends_on` | the link units it depends on, by `name` |
| `rust_equivalent` | what Rust already provides in the link unit's place, taken as a whole: `std` and `crates`, as a module's are recorded in [rust_equivalent.std](#61-rust_equivalentstd) and [rust_equivalent.crates](#62-rust_equivalentcrates) |
| `modules` | the link unit's covered modules, in `index` order |

## 4. link_units[*].modules[*]

A module is named by its `name` and `foundational` within its containing link unit: its
globally addressable identity is `(link_unit.name, module.name, module.foundational)`,
written `<link-unit>/<name>`, with ` (foundational)` after it for a foundational module.
The name alone suffices but for a split foundational TU, whose two modules share the TU's
path as their name and differ in `foundational`. Every reference to a module, in a
dependency record, a wave or a batch's task, carries both. Its `index` is its permanent
number within the link unit, which orders and numbers the modules a run adds.

| field | meaning |
|---|---|
| `index` | the module's id within its link unit, from zero |
| `name` | the path below the C root of its translation unit, or of its header for a header module |
| `status` | `todo` or `frozen`; see [Status](#2-status) |
| `foundational` | `true` for a foundational module, `false` otherwise; see `decomposition`'s Foundational modules section |
| `depends_on` | an array of dependency records; see [Dependencies](#8-link_unitsmodulesdepends_on) |
| `translation_unit` | the module's TU, as a [file entry](#5-file-entries); `null` for a header module |
| `internal_headers` | the headers the build does not install that the module defines items in, as file entries |
| `api_headers` | the headers the build installs that the module defines or declares items in, as file entries |
| `tests` | the test files tied to the module, those whose subject it is, as file entries whose `items` select test functions; see [File entries](#5-file-entries) |
| `objective` | the translation intent recorded for this module |
| `counters` | what the module contains |

A header module, one with a `null` `translation_unit`, holds a header that implements what
no TU does, such as `static inline` functions or globals of its own, and lists it in
`internal_headers` or `api_headers` as the build installs it or not.

## 5. File entries

Every file a module lists is an entry:

| field | meaning |
|---|---|
| `path` | the file's path below the C root |
| `items` | `included` and `excluded`, each an array of the C entity names the file defines or declares |

With both lists empty, the module owns every entity the file defines or declares. With
`included`, it owns only those; with `excluded`, every other one. A file entry sets one
list at most. A typedef follows the type it names, so naming a struct or its typedef
selects both. A macro is owned as any entity is when it is API, as
[`decomposition`](../../planning/decomposition/SKILL.md)'s Bundling section describes.

Every entity is owned by exactly one module, and every translation unit is listed by
exactly one module, apart from a foundational split, whose two modules list it with the
same names, one as `included` and the other as `excluded`. A header may be listed by
several modules, each owning the entities its lists select: the module bundled with the
header usually owns it whole, or with `excluded` the entities other modules take, and each
of those lists it with them as `included`.

The owner counts, homes and translates an entity; every other module reaches it through
an ordinary dependency record.

Test files are not owned: a test file is listed in the `tests` of every module it is
tied to, as `decomposition`'s Bundling section describes, and its entry's
`items` name the test functions tied to that module, empty when the whole file is.

## 6. link_units[*].modules[*].objective

| field | meaning |
|---|---|
| `objective` | `wrap` to preserve the C implementation behind a safe Rust API, or `port` to reimplement it in safe Rust |
| `rust_equivalent` | what Rust already provides in its place: `std` and `crates`, below |

A module carries one objective, which the settings' `campaign` answer sets, as
`decomposition`'s Objectives section describes: `port` in a port
campaign and `wrap` in a wrap campaign, and `wrap` for every foundational module in either.
A TU is not split for its objective.

### 6.1 rust_equivalent.std

The closest the Rust standard library (`core`, `alloc` and `std`) comes to providing the
module in its place, taken as a whole: every item it owns. `null` when the standard
library provides none of it.

| field | meaning |
|---|---|
| `library` | the standard-library paths that come closest to providing it, modules or types such as `alloc::vec::Vec` or `core::str` |
| `feature_parity` | `full` when replacing the module with them gains exactly the module's functionality, `partial` otherwise |
| `notes` | for `partial`, what is missing or differs; empty for `full` |

### 6.2 rust_equivalent.crates

Established crates that could replace the module outright, in descending order of
feature parity; empty when none applies.

| `crates[*]` field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `feature_parity` | `full` or `partial`, as for `std` |
| `license` | its SPDX license expression |
| `notes` | what is missing or differs: semantics, platform support or performance; empty when nothing |

Each candidate is checked for its semantics, platform support, performance and licensing
before it is listed.

A crate that reimplements or binds the target itself, the repository or one of its link
units, is not listed, nor is one of its components: replacing the target is what the
campaign does, so such a crate is no equivalent of a module or a link unit but an
alternative to the campaign. A general-purpose crate that also serves such a
reimplementation is listed on its own merits.

## 7. link_units[*].modules[*].counters

Two blocks with the same fields: `implementation` counts what the module's
`translation_unit` and `internal_headers` define, and `api` counts what its `api_headers`
publish. Only entities the module owns are counted, so a shared header's entities count
once across the decomposition.

| `implementation` field | meaning |
|---|---|
| `files` | number of file entries in `translation_unit` and `internal_headers` |
| `loc` | physical nonblank, noncomment lines across the entities it owns |
| `structs` | struct definitions |
| `functions` | function definitions |
| `global_variables` | file- and program-scope variables |
| `unions` | union definitions |
| `callbacks` | function-pointer types the module defines |

| `api` field | meaning |
|---|---|
| `files` | number of entries in `api_headers` |
| `loc` | physical nonblank, noncomment lines across the entities it owns |
| `structs` | structs whose body the API headers publish |
| `opaque_structs` | structs the API headers only forward-declare |
| `functions` | functions the API headers declare, prototypes and `static inline` alike |
| `global_variables` | variables the API headers declare |
| `unions` | unions the API headers define |
| `callbacks` | function-pointer types the API headers define |

The blocks overlap: a function defined in a translation unit and declared in an API
header counts in both, once as a definition and once as published. Never add them.

Enums and macros are not counted yet, here or in a dependency record.
<!-- TODO: count them once wavefront schedules them, as its skill's TODO says. -->

## 8. link_units[*].modules[*].depends_on

Every record is directed from this module, the consumer, to something it depends on: a
module of the decomposition, or an out-of-tree library, which depends on none of the
modules and so forms no cycle with them. Which in-tree dependencies the order keeps and
which it cuts is `schedule.json`'s. Imported producer modules are emitted as modules too,
so every in-tree record resolves through `link_units`.

| in-tree record field | meaning |
|---|---|
| `link_unit` | destination `link_units[*].name` |
| `module` | destination module's `name` within that link unit |
| `foundational` | the destination module's `foundational`, which tells the two modules of a split TU apart |
| `outgoing_edges` | dependency edges from this module to the destination |
| `incoming_edges` | dependency edges from the destination back to this module |
| `counters` | distinct entities consumed from that destination, by kind |

`outgoing_edges` is what this module needs from the destination; `incoming_edges` is what
the destination needs from it, and is non-zero exactly when the two form a cycle. The pair
is mirrored: the destination's own record for this module, when the two form a cycle,
carries the same two numbers swapped.

| out-of-tree record field | meaning |
|---|---|
| `library` | external library depended on, as linked: a `libraries[*].name` of `dependencies.json` |
| `counters` | distinct entities consumed from it, by kind |

What the campaign knows of the library itself, the release the target links, its source,
its wrapper and the crates that port or bind it, is recorded once, in `dependencies.json`,
as `dependencies-schema` describes, not in each record that imports it.

A record's `counters` carries the same item kinds a module's own does — `structs`,
`functions`, `global_variables`, `unions`, `callbacks` — counting what this module
consumes, not what the destination contains. A module that uses only another's enums has
no record of it yet, and its edges count no enum. It has no `files` or `loc`: those
describe a module's own files, and a consumer imports entities, not files.

The in-tree graph may contain cycles, and these records keep them: a record whose
`incoming_edges` is non-zero is one side of a cycle, which the order cuts.
