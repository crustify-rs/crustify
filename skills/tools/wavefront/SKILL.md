---
name: wavefront
description: "Deterministic queries and dependency-ordered plans over the C codebase, the first resort for any question about it: entities, uses, dependencies, pointers, lifecycles, T3 cast tables. Read before querying the C codebase, before planning, decomposing or scheduling, before analysing or binding an item, when packing wrap batches, when reviewing pointer findings or lifecycles, and before changing wavefront itself."
---

# wavefront

Wavefront answers deterministic queries about a C codebase, its entities, their uses and
dependencies, their pointers and lifecycles, and generates dependency-ordered wave plans
over it.

It is the first resort for any question about the C codebase: an entity's definition,
fields or signature, its users, callers and casts, what it depends on, and the pointer
findings and lifecycle roles submitted on it are queried rather than searched for in the
source, so that each answer covers every site the traced build compiles, and every query
of one fact gets one answer. The source is read where wavefront records nothing, to read a
body, and to judge what wavefront records.

Its `README.md` and `--help` are read in full before its first command, and each section
below names the documents under its `docs/` that its stage reads, also in full. How
wavefront scopes, orders and batches, what its configuration, tables and records hold, and
what each query returns are those documents', and are not restated here. Its goals and
non-goals, `docs/goals.md`, are what a change to wavefront is judged against, as
[`evolution`](../../crustify/evolution/SKILL.md) describes.

## Campaign state

Wavefront's repo root is the C root: it is passed `<workdir>/c`, so that every path it
reads and reports is relative to the C root, as the plan records them. Its state sits
under `crustify/wavefront/`, which the configuration names as its `state_dir`,
`../crustify/wavefront`:

- `codeql/`, the CodeQL database and its T1/T2 tables, and `.cache`, both gitignored;
- `configs/wavefront-config.json`, the campaign's configuration, which every query of the
  bindings and reviews resolves through, with `"t3_dir": "t3"`;
- `t3/`, the T3 tables, one campaign-wide pair; and
- `ownership-store.json`, the findings submitted to it through the CLI. A finding
  submitted once is queried again rather than re-derived.

The configuration's `modules` hold one record per module of `modules.json`, named
`<link-unit>/<name>`, with ` (foundational)` after a foundational module's name.

What follows is how wavefront serves each stage: each section names the skill and section
it adds to, and states only what wavefront adds there.

## Setup

### Setup › Provisioning

CodeQL and wavefront's query pack dependencies are installed, as its README describes.
`crustify/.gitignore` lists `wavefront/codeql` and `wavefront/.cache`.

### Setup › Artifact tree

`crustify/wavefront/` is scaffolded for wavefront's state.

### Setup › Baseline

Once the builds and the baseline are recorded, the CodeQL database is created from a
traced build of the `plain` configuration in a fresh scratch dir, with `c/` as its source
root, and its T1/T2 tables are extracted, through a bootstrap configuration in
`crustify/tmp/`; the campaign's own configuration is the plan's.

## Planning

Planning reads `docs/scoping.md`, `docs/graph.md`, `docs/batching.md`,
`docs/type-lifecycle.md`, `docs/artifacts/t3.md` and `docs/artifacts/schedule.md`.

### Decomposition › Runs

Each planner run brings the configuration and the T3 tables up to date with the plan: it
emits what is missing, migrates what follows an earlier wavefront schema, adds what the
scope adds and corrects what is wrong. A changed configuration or T3 row changes the graph,
so the `todo` waves whose batches it moves are re-planned, and the `depends_on` in
`modules.json` when it moves them.

### Decomposition › Dependencies

The configuration's `modules` are authored from `modules.json`: each module's files, with
the entities its `items` list select, each by the kind it is in C. Wavefront refuses an
entry that claims what its file only declares, and a unit two modules claim, so that every
entity is owned by exactly one module; the configuration is verified against the CLI.
<!-- TODO: wavefront makes a unit of every macro an installed header defines, but of an
internal header's macro only where the closure's code expands it, so an internal API macro
no C of the closure expands is planned nowhere, and it makes units of the configuration and
attribute macros the closure expands too. It has yet to make units of the macros that are
API, and only those, count enums and
macros in the modules' records, and tell a closed enum from a flags one, which the planner
judges until then, as `scheduling`'s Later stages section describes. -->

A module's dependency records are counted from a schedule of the whole closure, without
`schedule_seeds`: its module record's `depends_on` gives its in-tree records, with their
`unique_edges` and `total_edges`; its items give the `counters`, and their references
whose `scope` is `external` the out-of-tree records.

### Decomposition › Foundational modules

The foundational modules' candidates are selected from the configuration's graph, after
the T3 tables are written, so that their cast edges resolve type-erased values: the
type-erased units that no cast edge ties to a named type, and the units whose pointers
carry the `string` property, that depend on no other module's types. Each candidate's body
is read before it is admitted. Each member's lifecycle role is identified as
`docs/type-lifecycle.md` describes and submitted to the ownership store, so that the bindings of
the foundational modules find it.

### Scheduling › Order

The link units and modules are ordered from the configuration, after its T3 tables are
written, and reviewed there:

- every type-erased parameter and field with no cast, followed until it is read as a named
  type, stored, returned or lost. A hop that dispatches on a tag and reads different types
  per branch establishes none of them;
- every cast edge wavefront derives between two public types, each that is no type
  relation dropped;
- every public type in a cast relation, the pairs that are a hierarchy recorded as
  `base_derived` rows; and
- the type-minting macros, the source checked for invocations that conditional
  compilation hides from the traced build.

A row wavefront warns is stale is corrected or deleted.

### Scheduling › Waves and batches

- A planner run schedules once, its `schedule_seeds` the files
  of the modules it plans, without batch caps: the waves' batches are packed when each
  starts. The output is written to `crustify/tmp/`, never over `schedule.json`.
- A wrap campaign schedules over the API headers alone, in wavefront's API mode.
- A unit wavefront warns belongs to no module, and a module it warns claims no unit, are
  gaps in the decomposition, corrected before the schedule is used.
- Wavefront's `modules` become `schedule.json`'s, each named back to its `link_unit`,
  `module` and `foundational`, with its `layer`, its waves and its dependency records. Its
  `depends_on.external` records group its units' references whose `scope` is `external`
  by the library whose installed headers define the referenced entity, as
  `dependencies.json` names it; the external entity's own dependencies, which wavefront
  walks too, are the side campaign's to schedule.
- Wavefront numbers its waves from 0 in every run, so the `todo` waves are numbered after
  the highest index of a started wave, in wavefront's order, their `depends_on`
  renumbered. A wave's `items` are those of its wavefront batches, with their `home`, their
  `objective`, their `used_fields` as `field_users`, a macro's `type_generator_for`
  deciding its route, and their release points. An item a started wave holds, or that a
  batch has landed with that objective, is dropped, and a dependency on it is one on that
  wave.

### Scheduling › Wrap batches

The units a batch's items depend on are their `depends_on` in the planner run's schedule,
or wavefront's dependency query over them. A wrap batch's items are closed over their wrap
dependencies by that query in API mode, less what
`scheduling`'s Wrap batches section leaves out.

### Scheduling › Later stages

A port campaign's schedule, which is not in API mode, gives each item its release
points, which `schedule.json`'s items carry as wavefront records them, and which place its
later stages: `opaque_after` a `port/layout`, `memory_unmanaged_after` a `port/memory` and
`unreferenced_after` a `port/unexport`; a macro's or a typedef's places none. A stage's
wave waits for the last waves of the modules its point's `closure.modules` names, less the
item's own; with none left, the stage is not planned, unless C tests still reference the
export once the item's module has switched, as the `scheduling` skill's Later stages
section describes. The C tests, which the closure leaves out, hold
no stage back: a `port/unexport` carries over those that still reference its export, as the
`scheduling` skill's Later stages section describes. Whether a user stays C is read from
the whole list of its users, as `docs/batching.md`'s Release points section queries them.
`memory_unmanaged_after` is `null` until the ownership store holds the raw roles, so they
are established first.

## Batches

### Versioning › Lifecycle › Batches

The CodeQL database and tables under `crustify/wavefront/codeql/`, and wavefront's
`.cache`, are gitignored state every batch needs: they are symlinked into each batch's
worktree once it is forked.

## Binding and porting

Binding and porting read `docs/pointer-properties.md`, `docs/type-lifecycle.md`,
`docs/artifacts/findings.md` and `docs/artifacts/t3.md`.

### Analysis

An item's analysis queries the campaign's configuration, and its findings are submitted
to the ownership store. A type-erased parameter or field is looked up in the T3 tables before it
is bound, and the binding names the type a row gives it rather than a raw pointer. The
instances of a type generator share one generic, with per-instance aliases.

### Binding types › Surface

A type's lifecycle primitives are identified as `docs/type-lifecycle.md` describes, and
submitted to the ownership store.

### Binding symbols › Function pointers

A function pointer's record and its users are those of wavefront's function-pointer query,
named as `docs/graph.md`'s Nodes section names it, and the sites of one written inline,
and what reaches them, are as `docs/batching.md`'s Release points section describes.
<!-- TODO: no query lists an inline function pointer's sites yet: they are read from the
table that section names. -->

### Binding symbols › Lifecycle strategies

Each foundational item's lifecycle role is in the ownership store, where planning
submitted it, and is queried for every item of the batch. A role that the item's body
contradicts is corrected in the ownership store, and the correction named in the batch's commit
message.

### Porting types

A ported type's lifecycle primitives are identified as `docs/type-lifecycle.md`
describes, and submitted to the ownership store.

## Reviewing

### Reviewing › Objectives

#### Lifecycle (`lifecycle`)

Lifecycles submitted to wavefront that are incomplete: a releaser, disposer, cloner or
constructor that the findings of the batches that bound or ported items of the type
route, or items of the foundational modules, missed, checked against the lifecycle
primitives `docs/type-lifecycle.md` identifies.

#### The submitted findings

Whatever the objectives, a review checks the pointer findings an earlier run submitted for
the workset: ownership, access, nullability, cardinality and keepalive. A wrong inference
is a finding.

#### Unsafety

The plan cuts the cycles between modules and types. A raw pointer that stands in for a
dependency a later scheduled batch wraps is such a cut, not an `unsafety` finding.

### Reviewing › Reports

A finding on wavefront's findings is filed in its own `<slug>` directory, with its report
and the evidence that proves the submitted finding wrong or incomplete, under:

- `<reviews dir>/wavefront/ownership/`, for a wrong pointer-related inference; or
- `<reviews dir>/wavefront/lifecycle/`, for an incomplete lifecycle.

A defect in wavefront itself is no finding on its findings: it is a proposal, as any tool
defect is.

### Reviewing › Fixes

Under `fix`, each corrected or completed set of findings is submitted again, and a completed lifecycle gets the representations the Rust is missing.

### Reviewing › Plan corrections

A correction of wavefront's planning artifacts is filed in the reviews sub-directory of
what it amends:

- `crustify/reviews/planner/modules/` for a configuration, with the `modules.json`
  finding it follows from;
- `crustify/reviews/planner/chased-casts/` for `chased_casts.csv`: for each `add` row the
  chain followed, hop by hop with `file:line`, or the hop that breaks it; for each `drop`
  row the cast sites that derive the edge, and why they are no type relation; and
- `crustify/reviews/planner/type-generators/` for `type_generators.csv`: the macro's
  invocation sites, conditional ones included, and the shapes they mint.

A report on a T3 table also states the DAG change the edit makes.

## Evolution

A change to wavefront reads its README's Tests section, which names its opt-in CodeQL
tests: a change to a query or a fixture's C runs them, as the `evolution` skill's Changes
section asks of a tool's opt-in tests.
