# modules.json schema

Field meaning for `<workdir>/crustify/artifacts/modules.json`, the campaign's
decomposition. Layout example: [`templates/modules.json`](../../templates/modules.json).

Planning emits this repo-tier artifact: the first run creates it, and every run adds what
it lacks and corrects what earlier runs decided, apart from what a frozen module records.
It describes the modules the user's scope selects and every module in their producer
closure.

A module is one translation unit with the headers it defines its items in, as
`specs/decomposition.md` describes. The decomposition follows the
C codebase rather than a judgement of how it is organized: a module exists because a TU,
or a header that implements what no TU does, exists. It is also the shape the Rust tree
mirrors, as `specs/conventions.md` describes: there is no second placement document.

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision — a commit, not a counter. What this decomposition describes, pinned |
| `link_units` | the campaign's link units, in `index` order |

## 1. Execution order

`index` identifies a link unit, and a module within its link unit; it is not a position.
Each run numbers the link units and modules it adds after the highest index already used,
so an index is never reused or renumbered.

The order is computed from the dependencies. A module's `depends_on` records every
dependency it has, split in two, as [Dependencies](#8-link_unitsmodulesdepends_on)
describes:

- `scheduled`, the modules that run before it, and the out-of-tree libraries it uses; and
- `cut`, the modules it depends on that run after it, its dependency on them cut to break
  a cycle.

Their in-tree records together are every module it depends on, and `scheduled` alone is
acyclic across the decomposition. Within a cycle, the dependency kept is the one on the
member the most other members depend on, and the edges between tied members break ties,
as `specs/scheduling.md`'s Order section describes. Modules are ordered one after another,
in the order of `scheduled`; their waves run whenever they are scheduled, as
[`schedule.md`](schedule.md) orders them. Among the modules ready at once, a foundational one runs first, then the one whose link
unit has the lower index, then the one with the lower index. Link units are ordered the
same way by their own `depends_on`.

A foundational module depends through `scheduled` on foundational modules only, so every
foundational module runs before any other, and those whose items depend on others' run
after them: the modules of string lifecycle routines after those of the type-erased
allocators they call.

A new module lands wherever its dependencies place it, without renumbering any other. When
a frozen module depends on it, that dependency is one of the frozen module's cuts: it runs
already, so the new module can only follow it.

## 2. Status

A module's `status` is its decomposition's: `todo` while it may still change, and
`frozen` from the launch of its first wave, of any kind, or earlier when the user freezes
it, since that wave homes items in the module's file. A frozen module's record, and its
place in the order, change only when the user asks: a re-plan neither re-decomposes nor
re-homes it, and moves no item into or out of it.

Freezing a module does not freeze its schedule: its waves that are `todo` may still be
re-planned, and waves appended to it whenever a consumer needs more of it, as
[`schedule.md`](schedule.md)'s Re-planning section describes. A module's progress is not
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
| `depends_on` | `scheduled` and `cut`: the link units it depends on, by `name`, split as for modules |
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
| `foundational` | `true` for a foundational module, `false` otherwise; see `specs/decomposition.md`'s Foundational modules section |
| `depends_on` | `scheduled` and `cut`, each an array of dependency records; see [Dependencies](#8-link_unitsmodulesdepends_on) |
| `translation_unit` | the module's TU, as a [file entry](#5-file-entries); `null` for a header module |
| `internal_headers` | the headers the build does not install that the module defines items in, as file entries |
| `api_headers` | the headers the build installs that the module defines or declares items in, as file entries |
| `tests` | the test files gated with the module, those that use its internals, as file entries whose `items` select test functions; see [File entries](#5-file-entries) |
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
selects both. Macros are neither owned nor listed: they are not translated.

Every entity is owned by exactly one module, and every translation unit is listed by
exactly one module, apart from a foundational split, whose two modules list it with the
same names, one as `included` and the other as `excluded`. A header may be listed by
several modules, each owning the entities its lists select: the module bundled with the
header usually owns it whole, or with `excluded` the entities other modules take, and each
of those lists it with them as `included`.

The owner counts, homes and translates an entity; every other module reaches it through
an ordinary dependency record.

Test files are not owned: a test file is listed in the `tests` of every module it is
gated with, as `specs/workflows/porting.md`'s Principles section describes, and its entry's
`items` name the test functions gated with that module, empty when the whole file is.

## 6. link_units[*].modules[*].objective

| field | meaning |
|---|---|
| `objective` | `wrap` to preserve the C implementation behind a safe Rust API, or `port` to reimplement it in safe Rust |
| `rust_equivalent` | what Rust already provides in its place: `std` and `crates`, below |

A module carries one objective, which follows from its `rust_equivalent` as
`specs/decomposition.md`'s Objectives section describes: `wrap` when `std` or a crate has `full` feature parity with
it, `port` otherwise, and `wrap` for every foundational module. A TU is not split for its
objective.

### 6.1 rust_equivalent.std

What the Rust standard library (`core`, `alloc` and `std`) provides in place of the
module, taken as a whole: every item it owns. `null` when the standard library provides
none of it.

| field | meaning |
|---|---|
| `library` | the standard-library paths that provide it, modules or types such as `alloc::vec::Vec` or `core::str` |
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
campaign does, so such a crate is no equivalent of a module but an alternative to the
campaign. A general-purpose crate that also serves such a reimplementation is listed on
its own merits.

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
| `enums` | enum definitions |
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
| `enums` | enums the API headers define |
| `unions` | unions the API headers define |
| `callbacks` | function-pointer types the API headers define |

The blocks overlap: a function defined in a translation unit and declared in an API
header counts in both, once as a definition and once as published. Never add them.

## 8. link_units[*].modules[*].depends_on

Every record is directed from this module, the consumer, to something it depends on: a
module of the decomposition, in `scheduled` or `cut` as the order splits them, or an
out-of-tree library, always in `scheduled`, since a library outside the tree depends on
none of the modules and so forms no cycle with them. Imported producer modules are
emitted as modules too, so every in-tree record resolves through `link_units`.

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
is mirrored: the destination's own record for this module carries the same two numbers
swapped, in its `scheduled` when this one is in `cut`, and in its `cut` when this one is
in `scheduled` and the two form a cycle.

| out-of-tree record field | meaning |
|---|---|
| `library` | external library depended on, as linked: a `libraries[*].name` of `dependencies.json` |
| `counters` | distinct entities consumed from it, by kind |

What the campaign knows of the library itself, the release the target links, its source,
its wrapper and the crates that port or bind it, is recorded once, in `dependencies.json`,
as `specs/artifacts/dependencies.md` describes, not in each record that imports it.

A record's `counters` carries the same item kinds a module's own does — `structs`,
`functions`, `global_variables`, `enums`, `unions`, `callbacks` — counting what this
module consumes, not what the destination contains. It has no `files` or `loc`: those
describe a module's own files, and a consumer imports entities, not files.

The in-tree graph may contain cycles, and this artifact records them: `cut` holds the
edges the order cuts.
