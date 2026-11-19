---
name: wavefront
description: "Deterministic queries over the C codebase, the first resort for any question about it: entities, uses, dependencies, pointers, lifecycles, T3 cast tables, and a dependency order of its components. Read before querying the C codebase, before choosing the order to port components in, before analysing or porting an item, when reviewing pointer findings or lifecycles, and before changing wavefront itself."
---

# wavefront

Wavefront answers deterministic queries about a C codebase, its entities, their uses and
dependencies, their pointers and lifecycles, and orders its units by dependency.

It is the first resort for any question about the C codebase: an entity's definition,
fields or signature, its users, callers and casts, what it depends on, and the pointer
findings and lifecycle roles submitted on it are queried rather than searched for in the
source, so that each answer covers every site the traced build compiles, and every query
of one fact gets one answer. The source is read where wavefront records nothing, to read a
body, and to judge what wavefront records.

Read its `README.md` and `--help` in full before its first command, and read in full the
documents under its `docs/` that each section below names before that kind of work. How
wavefront scopes and orders, what its configuration, tables and records hold, and what each
query returns are those documents', and are not restated here.

## State

Wavefront's repo root is the C root, the directory that holds the C codebase, so that every
path it reads and reports is relative to it. Its state sits under `.crustify/wavefront/`,
which the configuration names as its `state_dir`:

- `codeql/`, the CodeQL database and its T1/T2 tables, and `.cache`, both gitignored;
- `configs/wavefront-config.json`, the port's configuration, which every query resolves
  through, with `"t3_dir": "t3"`;
- `t3/`, the T3 tables, one pair for the whole port; and
- `ownership-store.json`, the findings submitted to it through the CLI. A finding
  submitted once is queried again rather than re-derived.

The configuration's `modules` hold one record per component, each with its files and the
entities they define. Wavefront refuses an entry that claims what its file only declares,
and a unit two components claim, so that every entity belongs to exactly one component.

## Setup

Install CodeQL and wavefront's query pack dependencies, as its README describes, and list
`wavefront/codeql` and `wavefront/.cache` in `.crustify/.gitignore`. Once the C builds,
create the CodeQL database from a traced build of the C, in a fresh dir under
`.crustify/tmp/`, with the C root as its source root, and extract its T1/T2 tables.

A worktree another agent works in needs the database and tables too: symlink
`.crustify/wavefront/codeql/` and `.cache` into it rather than building them again.

## Ordering components

Read `docs/scoping.md` and `docs/graph.md`.

A schedule of the scope, its `schedule_seeds` the files to port, gives the dependency order
of the components and which of them are independent, so that the agent can port
independent components at the same time and each component after what it depends on. Write
its output to `.crustify/tmp/`.

Before the order is used, write the T3 tables, so that cast edges resolve type-erased
values, and check them:

- every type-erased parameter and field with no cast, followed until it is read as a named
  type, stored, returned or lost. A hop that dispatches on a tag and reads different types
  per branch establishes none of them;
- every cast edge wavefront derives between two public types, each that is no type
  relation dropped;
- every public type in a cast relation, the pairs that are a hierarchy recorded as
  `base_derived` rows; and
- the type-minting macros, the source checked for invocations that conditional
  compilation hides from the traced build.

A row wavefront warns is stale is corrected or deleted. A unit wavefront warns belongs to
no component, and a component it warns claims no unit, are gaps in the configuration,
corrected before the order is used.

## Analysis and porting

Read `docs/pointer-properties.md`, `docs/type-lifecycle.md`, `docs/artifacts/findings.md`
and `docs/artifacts/t3.md`.

An item's analysis queries the configuration, and its findings are submitted to the
ownership store. A type-erased parameter or field is looked up in the T3 tables before it
is ported, and the Rust names the type a row gives it rather than a raw pointer. The
instances of a type generator share one generic, with per-instance aliases.

A type's lifecycle primitives, its constructors, releasers, disposers and cloners, are
identified as `docs/type-lifecycle.md` describes, and submitted to the ownership store. A
role that the item's body contradicts is corrected in the ownership store, and the
correction named in the commit message.

A function pointer's record and its users are those of wavefront's function-pointer query,
named as `docs/graph.md`'s Nodes section names it, and the sites of one written inline,
and what reaches them, are as `docs/batching.md`'s Release points section describes.
<!-- TODO: no query lists an inline function pointer's sites yet: they are read from the
table that section names. -->

## Reviewing

Whatever else it looks for, a review checks the pointer findings submitted for the code it
reviews: ownership, access, nullability, cardinality and keepalive. A wrong inference is a
finding.

A lifecycle submitted to wavefront is incomplete when it misses a releaser, disposer,
cloner or constructor, checked against the lifecycle primitives `docs/type-lifecycle.md`
identifies. An incomplete lifecycle is a finding too.

A finding on wavefront's findings is filed in its own `<slug>` directory, with its report
and the evidence that proves the submitted finding wrong or incomplete, under:

- `.crustify/reviews/wavefront/ownership/`, for a wrong pointer-related inference; or
- `.crustify/reviews/wavefront/lifecycle/`, for an incomplete lifecycle.

Its fix submits the corrected or completed findings again, and gives a completed lifecycle
the representations the Rust is missing. A report on a T3 table also states the change the
edit makes to the dependency graph.

A defect in wavefront itself is no finding on its findings: file it in `.crustify/reviews/`
with its reproducer.

## Changing wavefront

A change to a query or a fixture's C runs the opt-in CodeQL tests that its README's Tests
section names.
