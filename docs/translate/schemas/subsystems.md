# subsystems.json schema

Field meaning for `<workdir>/crustify/subsystems.json`, the orchestrator's campaign
decomposition. Layout example: [`specs/subsystems.json`](../../specs/subsystems.json).

The orchestrator emits this repo-tier artifact. It describes the subsystem span
selected by the user and every imported subsystem in that span's producer closure.

It is also the shape the Rust tree mirrors. There is no second placement document: a
module exists because a subsystem does, the filesystem records where an entity lives, and
a batch names the authored `.rs` home of each item it schedules. Rust has no headers, so a
subsystem's headers and translation units share one module.

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision — a commit, not a counter. What this decomposition describes, pinned |
| `link_units` | ordered list of the campaign's link units |

## link_units[*]

`link_units` is an ordered list. Each entry's `name` is its identifier; clients may build
a name index without losing the authored order.

| field | meaning |
|---|---|
| `name` | unique link-unit identifier, normally the linked artifact's filename stem |
| `kind` | `library` or `executable` |
| `linkage` | `shared` or `static` for a library; `null` for an executable |
| `subsystems` | ordered list of the link unit's covered subsystems |

## link_units[*].subsystems[*]

Each subsystem's `name` identifies it within its containing link unit. The globally
addressable identity is therefore `(link_unit.name, subsystem.name)`.

| field | meaning |
|---|---|
| `name` | subsystem identifier, unique within the link unit |
| `implementation_files` | repo-relative translation units and private headers homed in the subsystem |
| `api_headers` | repo-relative public headers the subsystem publishes: those the build installs |
| `objective` | the translation intent recorded for this subsystem |
| `counters` | what the subsystem contains |
| `imported_deps` | what it depends on, in tree and out |

TUs must be homed in exactly one subsystem; headers generally too, although there
might be cases when a header is shared by multiple subsystems. A header appears in one
list only: `api_headers` when the build installs it, `implementation_files` otherwise.
A public header belongs to the subsystem that implements what it declares.

A shared header is listed by every subsystem that shares it, but each entity it defines
is owned by exactly one of them: the one scheduled first. The owner counts, homes and
translates the entity; the other subsystems reach it through an ordinary `imported_deps`
record.

## link_units[*].subsystems[*].objective

| field | meaning |
|---|---|
| `objective` | `wrap` to preserve the C implementation behind a safe Rust API, or `port` to reimplement it in safe Rust |
| `rust_native_equivalent` | well established Rust crates or `std` facilities that could replace this subsystem outright, in descending order of fit; empty when none applies |

A subsystem is objective-homogeneous: files translated under different objectives do not
share one subsystem, and a mixed grouping is split until each emitted subsystem carries
one.

`rust_native_equivalent` records a judgement, not a decision: naming a candidate does not
by itself change the objective. A generic facility with a strong candidate is the usual
reason to leave a subsystem wrapped during a partial migration rather than port it.

## link_units[*].subsystems[*].counters

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
## link_units[*].subsystems[*].imported_deps

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

A dependency's `counters` carries the same item kinds a subsystem's own does — `structs`,
`functions`, `global_variables`, `enums`, `unions`, `callbacks`, `macros` — counting what
this subsystem consumes, not what the destination contains. It has no `files` or `loc`:
those describe a subsystem's own files, and a consumer imports entities, not files.

The in-tree graph may contain cycles, and this artifact records them.
