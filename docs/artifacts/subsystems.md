# subsystems.json schema

Field meaning for `<workdir>/crustify/artifacts/subsystems.json`, the campaign's
decomposition. Layout example: [`templates/subsystems.json`](../../templates/subsystems.json).

Planning emits this repo-tier artifact: the first run creates it, and every run adds what
it lacks and corrects what earlier runs decided, apart from what a frozen subsystem
records. It describes the subsystem span
selected by the user and every imported subsystem in that span's producer closure.

It is also the shape the Rust tree mirrors. There is no second placement document: a
module exists because a subsystem does, the filesystem records where an entity lives, and
a batch names the authored `.rs` home of each item it schedules. Rust has no headers, so a
subsystem's headers and translation units share one module.

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision — a commit, not a counter. What this decomposition describes, pinned |
| `link_units` | the campaign's link units, in `index` order |

## 1. Execution order

`index` identifies a link unit, and a subsystem within its link unit; it is not a
position. Each run numbers the link units and subsystems it adds after the highest index
already used, so an index is never reused or renumbered.

The order is computed from the dependencies. A subsystem's `depends_on` splits its
in-tree dependencies in two:

- `scheduled`, the subsystems that run before it; and
- `cut`, the subsystems it depends on that run after it, its dependency on them cut to
  break a cycle.

Their union is every in-tree destination of its `imported_deps`, and `scheduled` alone is
acyclic across the decomposition. Within a cycle, the dependency kept is the one on the
member the most other members depend on, and the edges between tied members break ties,
as `docs/planning.md` describes. Subsystems run in the order of `scheduled`, and among the
subsystems ready at once, the one whose link unit has the lower index runs first, then the
one with the lower index. Link units are ordered the same way by their own `depends_on`.

A new subsystem lands wherever its dependencies place it, without renumbering any other.
When a frozen subsystem depends on it, that dependency is one of the frozen subsystem's
cuts: it runs already, so the new subsystem can only follow it.

The first link unit opens with the two foundational subsystems `void` and `string`, at
indices 0 and 1 (see `docs/planning.md`). They depend on no other subsystem through
`scheduled`, so they run first. They are ordinary entries, usually narrowed to their
`items`.

## 2. Status

A subsystem's `status` is `todo` while its plan may still change, and `frozen` once its
record is final: from the launch of its first wave, or earlier when the user freezes it. A
frozen subsystem's record, and its place in the order, change only when the user asks: a
re-plan neither edits it nor splits or renames a subsystem it names. A subsystem's
progress is not recorded here: it is its waves' `status` in `schedule.json`.

## 3. link_units[*]

Each entry's `name` is its identifier; clients may build a name index without losing the
order.

| field | meaning |
|---|---|
| `index` | the link unit's id in the campaign, from zero |
| `name` | unique link-unit identifier, normally the linked artifact's filename stem |
| `kind` | `library` or `executable` |
| `linkage` | `shared` or `static` for a library; `null` for an executable |
| `depends_on` | `scheduled` and `cut`: the link units it depends on, by `name`, split as for subsystems |
| `subsystems` | the link unit's covered subsystems, in `index` order |

## 4. link_units[*].subsystems[*]

Each subsystem's `name` identifies it within its containing link unit. The globally
addressable identity is therefore `(link_unit.name, subsystem.name)`.

| field | meaning |
|---|---|
| `index` | the subsystem's id within its link unit, from zero |
| `name` | subsystem identifier, unique within the link unit |
| `status` | `todo` or `frozen`; see [Status](#2-status) |
| `depends_on` | `scheduled` and `cut`, each an array of `<link-unit>/<subsystem>` names; see [Execution order](#1-execution-order) |
| `implementation_files` | repo-relative translation units and private headers homed in the subsystem |
| `api_headers` | repo-relative public headers the subsystem publishes: those the build installs |
| `objective` | the translation intent recorded for this subsystem |
| `counters` | what the subsystem contains |
| `imported_deps` | what it depends on, in tree and out |
| `items` | optional: the entities the subsystem owns, which narrow it to them |

TUs must be homed in exactly one subsystem, apart from the items an item-granular
subsystem takes; headers generally too, although there
might be cases when a header is shared by multiple subsystems. A header appears in one
list only: `api_headers` when the build installs it, `implementation_files` otherwise.
A public header belongs to the subsystem that implements what it declares.

A shared header is listed by every subsystem that shares it, but each entity it defines
is owned by exactly one of them: the one that runs first. The owner counts, homes and
translates the entity; the other subsystems reach it through an ordinary `imported_deps`
record.

## 5. link_units[*].subsystems[*].items

A subsystem is file-granular by default: it owns every entity its files define or
publish. One with `items` is item-granular: it owns only the entities listed, and lists
in `implementation_files` and `api_headers` only the files those entities are defined in
or published by. Those files stay listed by the file-granular subsystem that owns the
rest of them, which does not own the listed entities.

| `items[*]` field | meaning |
|---|---|
| `name` | C entity name |
| `defined_in` | repo-relative path of its definition, as a batch item's `defined_in` |

`(name, defined_in)` is unique across the decomposition's `items`: an entity belongs to at
most one item-granular subsystem. An item-granular subsystem's `counters` count its items
only, and its `imported_deps` record what those items depend on.

## 6. link_units[*].subsystems[*].objective

| field | meaning |
|---|---|
| `objective` | `wrap` to preserve the C implementation behind a safe Rust API, or `port` to reimplement it in safe Rust |
| `rust_equivalent` | what Rust already provides in its place: `std` and `crates`, below |

A subsystem is objective-homogeneous: files translated under different objectives do not
share one subsystem, and a mixed grouping is split until each emitted subsystem carries
one.

`rust_equivalent` records a judgement, not a decision: naming a candidate does not by
itself change the objective. A generic facility with a strong candidate is the usual
reason to leave a subsystem wrapped during a partial migration rather than port it.

### 6.1 rust_equivalent.std

Whether the subsystem's items are already in the Rust standard library (`core`, `alloc`
and `std`), item by item:

| field | meaning |
|---|---|
| `coverage` | `full` when every type and function the subsystem owns has an `exact` equivalent, `none` when none has any, `partial` otherwise |
| `items` | the owned items that have an equivalent; empty when `coverage` is `none` |

| `items[*]` field | meaning |
|---|---|
| `name` | C entity name |
| `defined_in` | repo-relative path of its definition, as a batch item's `defined_in` |
| `facility` | the standard-library path that provides it, such as `alloc::vec::Vec::push` or `core::str::from_utf8` |
| `fit` | `exact` when the facility has the item's observable behaviour, `partial` when it differs in a way a port has to bridge |
| `notes` | for a `partial` fit, the difference; empty for an `exact` one |

### 6.2 rust_equivalent.crates

Established crates that could replace the subsystem outright, in descending order of fit;
empty when none applies.

| `crates[*]` field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `fit` | `exact` or `partial`, as for `std` |
| `license` | its SPDX license expression |
| `notes` | how it differs: semantics, platform support or performance; empty when it does not |

Each candidate is checked for its semantics, platform support, performance and licensing
before it is listed.

## 7. link_units[*].subsystems[*].counters

Two blocks with the same fields: `implementation` counts what the subsystem's
`implementation_files` define, and `api` counts what its `api_headers` publish. Only
entities the subsystem owns are counted, so a shared header's entities count once across
the decomposition.

| `implementation` field | meaning |
|---|---|
| `files` | number of entries in `implementation_files` |
| `loc` | physical nonblank, noncomment lines across them |
| `structs` | struct definitions |
| `functions` | function definitions |
| `global_variables` | file- and program-scope variables |
| `enums` | enum definitions |
| `unions` | union definitions |
| `callbacks` | function-pointer types the subsystem defines |
| `macros` | object- and function-like macro definitions |

| `api` field | meaning |
|---|---|
| `files` | number of entries in `api_headers` |
| `loc` | physical nonblank, noncomment lines across them |
| `structs` | structs whose body the API headers publish |
| `opaque_structs` | structs the API headers only forward-declare |
| `functions` | functions the API headers declare, prototypes and `static inline` alike |
| `global_variables` | variables the API headers declare |
| `enums` | enums the API headers define |
| `unions` | unions the API headers define |
| `callbacks` | function-pointer types the API headers define |
| `macros` | object- and function-like macros the API headers define |

The blocks overlap: a function defined in a translation unit and declared in an API
header counts in both, once as a definition and once as published. Never add them.
## 8. link_units[*].subsystems[*].imported_deps

Every record is directed from this subsystem, the consumer, to something it depends on.
Imported producer subsystems are emitted as subsystems too, so every in-tree destination
resolves through `link_units`.

| `in_tree[*]` field | meaning |
|---|---|
| `link_unit` | destination `link_units[*].name` |
| `subsystem` | destination subsystem's `name` within that link unit |
| `outgoing_edges` | dependency edges from this subsystem to the destination |
| `incoming_edges` | dependency edges from the destination back to this subsystem |
| `counters` | distinct entities consumed from that destination, by kind |

`outgoing_edges` is what this subsystem needs from the destination; `incoming_edges` is
what the destination needs from it, and is non-zero exactly when the two form a cycle. The
pair is mirrored: the destination's own record for this subsystem carries the same two
numbers swapped.

| `out_of_tree[*]` field | meaning |
|---|---|
| `library` | external library depended on, as linked |
| `counters` | distinct entities consumed from it, by kind |
| `rust_equivalent` | what Rust already provides for it: `ported` and `bindings`, below |

`rust_equivalent.ported` lists the crates that reimplement the library in Rust, and
`rust_equivalent.bindings` the crates that put a safe Rust API over the C library itself.
Each is in descending order of fit, and empty when no such crate exists. They decide how a
port reaches the library: through a ported crate, which drops the C dependency, through
safe bindings, which keep it, or through its own wrapper when neither exists.

| `ported[*]` and `bindings[*]` field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `sys` | `bindings` only: the raw `-sys` crate it builds on, or `null` when it binds the library itself |
| `covers` | `all` when it provides every entity this subsystem consumes from the library, `some` otherwise |
| `fit` | `exact` or `partial`, as for a subsystem's `std` items |
| `license` | its SPDX license expression |
| `notes` | what it lacks or how it differs; empty when nothing |

A crate that wraps the library but exposes raw pointers or `unsafe` to its users is not
safe bindings; a `-sys` crate alone is listed as no binding. The same library is assessed
the same way in every record that imports it.

A dependency's `counters` carries the same item kinds a subsystem's own does — `structs`,
`functions`, `global_variables`, `enums`, `unions`, `callbacks`, `macros` — counting what
this subsystem consumes, not what the destination contains. It has no `files` or `loc`:
those describe a subsystem's own files, and a consumer imports entities, not files.

The in-tree graph may contain cycles, and this artifact records them; `depends_on` records
how the order cuts them.

## 9. Earlier versions

Earlier decompositions recorded a subsystem's Rust equivalents as one list,
`objective.rust_native_equivalent`, of crates and `std` paths together, and nothing for
out-of-tree libraries. A decomposition still holding it is converted by its next planner
run: its crates become `crates`, and its `std` paths are re-assessed item by item into
`std`.
