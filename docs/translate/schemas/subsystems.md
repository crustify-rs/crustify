# subsystems.json schema

Field meaning for `<workdir>/crustify/subsystems.json`, the orchestrator's
campaign decomposition. Layout example:
[`specs/subsystems.json`](../../specs/subsystems.json).

The orchestrator emits this repo-tier artifact after it has authored the
campaign-wide Wavefront config and populated its CodeQL inventory. It describes
the subsystem span selected by the user and every imported subsystem in that
span's producer closure.

It is also the shape the Rust tree mirrors. There is no second placement
document: a module exists because a subsystem does, the filesystem records
where an entity lives, and a batch names the authored `.rs` home of each item
it schedules. Rust has no headers, so a subsystem's headers and translation
units share one module.

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision — a commit, not a counter. What this decomposition describes, pinned |
| `wavefront_config` | campaign-wide `wavefront-config.json` the decomposition was derived from |
| `link_units` | ordered list of the campaign's link units |

## link_units[*]

`link_units` is an ordered list. Each entry's `name` is its identifier; clients
may build a name index without losing the authored order.

| field | meaning |
|---|---|
| `name` | unique link-unit identifier, normally the linked artifact's filename stem |
| `kind` | `library` or `executable` |
| `linkage` | `shared`, `static`, or `system` for a library; `null` for an executable |
| `subsystems` | ordered list of the link unit's covered subsystems |

A system link unit may contain imported, header-derived subsystems whose
`implementation_files` list is empty and whose counters are zero. It may have
an empty `subsystems` list when no entity from that link unit enters the
campaign closure.

## link_units[*].subsystems[*]

Each subsystem's `name` identifies it within its containing link unit. The
globally addressable identity is therefore `(link_unit.name, subsystem.name)`.

| field | meaning |
|---|---|
| `name` | subsystem identifier, unique within the link unit |
| `implementation_files` | repo-relative files homed in the subsystem: translation units and headers alike |
| `objective` | the translation intent recorded for this subsystem |
| `counters` | what the subsystem contains |
| `imported_deps` | what it depends on, in tree and out |

The orchestrator must home every covered file in exactly one subsystem. This is
an authoring instruction, not a separate validation gate.

## link_units[*].subsystems[*].objective

| field | meaning |
|---|---|
| `objective` | `wrap` to preserve the C implementation behind a safe Rust API, or `port` to reimplement it in safe Rust |
| `rust_native_equivalent` | well established Rust crates or `std` facilities that could replace this subsystem outright, in descending order of fit; empty when none applies |

A subsystem is objective-homogeneous: files translated under different
objectives do not share one subsystem, and a mixed grouping is split until each
emitted subsystem carries one.

`rust_native_equivalent` records a judgement, not a decision: naming a
candidate does not by itself change the objective. A generic facility with a
strong candidate is the usual reason to leave a subsystem wrapped during a
partial migration rather than port it.

Changing the target selection or the objective requires regenerating this
artifact from the campaign-wide Wavefront config.

## link_units[*].subsystems[*].counters

| field | meaning |
|---|---|
| `impl_files` | number of entries in `implementation_files` |
| `loc` | physical nonblank, noncomment lines across them |
| `structs` | struct definitions |
| `functions` | function definitions |
| `global_variables` | file- and program-scope variables |
| `enums` | enum definitions |
| `unions` | union definitions |
| `callbacks` | function-pointer types the subsystem defines |
| `macros` | object- and function-like macro definitions |

Derive these by grouping the oracle's own records — `wavefront ... query types`
and `query symbols` return each entity's resolved kind — not by reading C. A
second count that disagrees is indistinguishable from a decomposition that has
drifted.

The oracle's kinds map onto these counters as:

| counter | oracle kind |
|---|---|
| `structs` | type `struct` |
| `unions` | type `union` |
| `enums` | type `enum` |
| `callbacks` | `callback` |
| `macros` | `macro` |
| `functions` | symbol `function_exported`, `function_inline_header` |
| `global_variables` | symbol `global_extern` |

A typedef is reported under the kind it resolves to, so a typedef of a struct
counts as a struct and a function-pointer typedef counts as a callback. There
is no typedef counter: the oracle resolves them away deliberately, and one
would either duplicate a count already made or stay zero.

## link_units[*].subsystems[*].imported_deps

Every record is directed from this subsystem, the consumer, to something it
depends on. Imported producer subsystems are emitted as subsystems too, so
every in-tree destination resolves through `link_units`.

| `in_tree[*]` field | meaning |
|---|---|
| `link_unit` | destination `link_units[*].name` |
| `subsystem` | destination subsystem's `name` within that link unit |
| `nr_edges` | oracle dependency edges aggregated into this relation |
| `counters` | distinct entities consumed from that destination, by kind |

| `out_of_tree[*]` field | meaning |
|---|---|
| `library` | external library depended on, as linked |
| `counters` | distinct entities consumed from it, by kind |

A dependency's `counters` carries the same item kinds a subsystem's own does —
`structs`, `functions`, `global_variables`, `enums`, `unions`, `callbacks`,
`macros` — counting what this subsystem consumes, not
what the destination contains. It has no `impl_files` or `loc`: those describe
a subsystem's own files, and a consumer imports entities, not files.

The in-tree graph may contain cycles, and this artifact records them. It
describes the decomposition as it is; it is not a schedule, and dropping an
edge to make it a DAG would falsify the dependency it documents and hide the
cycle from everything downstream.

The orchestrator cuts cycles when it schedules, not here. Within a cyclic
region, a subsystem with more incoming consumer edges has greater producer
weight and should preferentially remain the producer; `nr_edges` refines that
weight when choosing where to cut. A cut belongs to the wave plan that made
it, which records it as an explicit SCC cut.
