---
name: wavefront
description: "Deterministic queries and dependency-ordered plans over the C codebase (CodeQL tables, ownership store, T3 cast tables). Read before planning, decomposing or scheduling, before analysing or binding an item, when packing wrap batches, and when reviewing pointer findings or lifecycles."
---

# wavefront

Wavefront answers deterministic queries about a C codebase: type and symbol records,
pointer analysis, lifecycle roles, dependency closures and the source inventory, and it
generates objective-neutral, dependency-ordered wave plans. Its own documentation, its `README.md`, its `--help` and the documents under its `docs/`,
is read in full before its first command: `docs/scoping.md`, `docs/graph.md` and
`docs/batching.md` describe how it selects, orders and batches; `docs/artifacts/t3.md`
the T3 tables; and `docs/type-lifecycle.md` how a type's lifecycle primitives are
identified.

Wavefront's repo root is the C root, `c/`: it is passed `<workdir>/c` as its
`repo_root`, so that every path it reads and reports is below the C root, as the plan
records them.

A campaign keeps its wavefront state under `crustify/wavefront/`:

- the CodeQL database and its T1/T2 tables, under `codeql/`, and wavefront's `.cache`,
  both gitignored;
- the configuration, `configs/wavefront-config.json`, which every query of the bindings
  and reviews resolves through, and which orders and schedules the modules. Its `closure`
  holds the files of every module, its `impl_files` the translation units and internal
  headers and its `api_headers` the installed headers; its `modules` holds one record per
  module of `modules.json`, named `<link-unit>/<name>`, with ` (foundational)` after a
  foundational module's name, whose `files` are the module's file entries with their
  `items`; and its `schedule_seeds` names what a planner run schedules. It uses
  `../crustify/wavefront`, relative to the C root, as its `state_dir`, and sets
  `"t3_dir": "t3"`;
- the T3 tables, under `t3/`, one campaign-wide pair serving the configuration:
  `chased_casts.csv`, whose `erased_arg` and `erased_field` rows name the type a
  type-erased parameter or field holds and whose `base_derived` rows the base a type is
  reached through, and `type_generators.csv`, the type-minting macros and the shapes they
  mint; and
- the ownership store, `ownership-store.json`, which holds the findings submitted with
  the CLI's `--update`: pointer ownership, access, nullability, cardinality and keepalive,
  and lifecycle roles. A finding submitted once is queried again rather than re-derived.

What follows is how wavefront serves each stage: each section names the skill and section
it adds to, and states only what wavefront adds there.

## Setup

### Setup › Provisioning

CodeQL is installed, and wavefront's query pack dependencies with `codeql pack install`
on wavefront's `src/`: extraction fails without them. `crustify/.gitignore` lists
`wavefront/codeql` and `wavefront/.cache`.

### Setup › Artifact tree

`crustify/wavefront/` is scaffolded for wavefront's artifacts.

### Setup › Baseline

Once the builds and the baseline are recorded, the CodeQL T1/T2 tables wavefront computes
dependencies from are emitted. The CodeQL database is created under
`crustify/wavefront/codeql/` from a traced build of the `plain` configuration in a fresh
scratch dir, with `c/` as its source root, and the tables are extracted into
`crustify/wavefront/codeql/{t1,t2}` through a configuration whose `state_dir` is
`../crustify/wavefront`. That bootstrap configuration sits in `crustify/tmp/`; the
campaign's own configurations are the plan's.

## Planning

### Decomposition › Runs

Wavefront's planning artifacts are the configuration under `crustify/wavefront/configs/`
and the T3 tables under `crustify/wavefront/t3/`. Each planner run brings them up to date
with the plan: it emits what is missing, updates what follows an earlier wavefront schema,
adds what the scope adds, and corrects what is wrong. A changed configuration or T3 row
changes the DAGs wavefront builds, so the `todo` waves whose batches it moves are
re-planned, and the `depends_on` in `modules.json` when the configuration moves them.

### Decomposition › Dependencies

The configuration's `modules` are authored from `modules.json`: each module's record
lists its `translation_unit`, `internal_headers` and `api_headers` entries, each with the
entities its `items` lists select, as `{"name", "kind"}` items. A struct tag and a
function or global may share a name in one file, so an item names the kind it means. A
module claims the units its files are home to, the file that defines them or, with none,
their declaration: a shared header's types and `static inline` functions are claimed by
listing the header with them as `included`, never by listing a header that only declares
them, which wavefront refuses. A unit two modules claim is refused too, so every entity is
owned by exactly one module. Macros are listed by none. The configuration is verified
against the CLI.

A module's dependency records are counted from a schedule of the whole closure, without
`schedule_seeds` and without `--with-enums`: the module's record in its `modules` gives each in-tree record's
`outgoing_edges` as its `total_edges`, and the other module's record its
`incoming_edges`; the items' `depends_on` give the `counters`, and their `external`
references the out-of-tree records.

### Decomposition › Foundational modules

The foundational modules' candidates are selected from the configuration's
graph, after the T3 tables are written, so that their cast edges resolve type-erased
values: the type-erased units that no cast edge ties to a named type, and the units whose
pointers carry the `string` property, that depend on no other module's types. Each
candidate's body is read before it is admitted.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
submitted to the ownership store through the CLI's `--update`, as `docs/type-lifecycle.md`
describes, so that the bindings of the foundational modules find it there.

### Scheduling › Order

The link units and modules are ordered from the configuration, after its T3 tables are
written. They are reviewed in that configuration:

- every type-erased parameter and field (`is_erased` in `t1/params.csv` and
  `t1/fields.csv`) with no cast in `t2/arg_casts.csv` or `t2/field_casts.csv`, followed
  until it is read as a named type, stored, returned or lost. A hop that dispatches on a
  tag and reads different types per branch establishes none of them;
- every cast edge wavefront derives between two public types, each that is no type
  relation dropped;
- every public type in a cast relation, the pairs that are a hierarchy recorded as
  `base_derived` rows; and
- the type-minting macros in `t2/macro_generated_types.csv`, the source checked for
  invocations conditional compilation hides from the traced build.

A row wavefront warns is stale is corrected or deleted.

### Scheduling › Waves and batches

- A planner run schedules once, with `wavefront schedule`: its `schedule_seeds` are the
  files of the modules it plans, and the schedule holds them and every unit they depend
  on, ordered over the whole closure. The output is written to `crustify/tmp/`, never
  over `schedule.json`.
- A wrap campaign schedules with `--api-headers-only`.
- It schedules without batch caps: the waves' batches are packed when each starts.
- A unit wavefront warns belongs to no module, and a module it warns claims no unit, are
  gaps in the decomposition, corrected before the schedule is used.
- Wavefront's `modules` become `schedule.json`'s, each named back to its `link_unit`,
  `module` and `foundational`, with its `layer`, its waves and its dependency records:
  their `unique_edges`, `total_edges` and, on a cut record, `items`.
- A module's `depends_on.external` records are built from its units' references whose
  `scope` is `external`, the edges from each unit's `depends_on`, grouped by the library
  whose installed headers define the referenced entity, as `dependencies.json` names it.
  wavefront walks an external entity's own dependencies, a function's signature and the
  fields of a struct the closure's code touches, but those are dependencies of the
  external entity, not of the units: the side campaign's own schedule closes over them.
- Wavefront numbers its waves from 0 in every run, so the `todo` waves are numbered after
  the highest index of a started wave, in wavefront's order, their `depends_on` renumbered,
  with their module's `layer` and their `sublayer`. A wave's `items` are those of its
  wavefront batches, each with its `name`, `defined_in` and `kind`, its `used_fields` as
  `field_users`, the `home` its module gives it, its `objective`, and its
  `opaque_after`, `memory_unmanaged_after` and `unreferenced_after`, with the later stages
  they place, as [Scheduling › Later stages](#scheduling--later-stages) describes. An item a wave
  that has started holds, or that a batch has landed with that objective, is dropped, and
  a dependency on it is one on that wave.

### Scheduling › Wrap batches

The units a batch's items depend on are their `depends_on`, `scheduled` and `cut`, in
the planner run's wavefront schedule, or `query dag --name <items>`. A wrap batch's items
are closed over their wrap dependencies on the public-signature graph,
`query dag --name <items> --api-headers-only`, less what has landed.

### Scheduling › Later stages

A port campaign's schedule, which is not `--api-headers-only`, gives each scheduled item
its release points, which `schedule.json`'s items carry as wavefront records them and which
place its later stages: a struct's or union's `opaque_after` its `port/layout`, its
`memory_unmanaged_after` its `port/memory`, and a function's or global's
`unreferenced_after` its `port/unexport`. A module's C leaves at its integration, so a
stage's wave waits for the last waves of the modules its point's `closure.modules` names,
less the item's own; with none left, the stage is not planned. The users behind each point
are a query away: `query types --name <T> --layout-users` lists a type's layout users with
the site and kind of each use, `query types --name <T> --raw-sites` its memory users, and
`query symbols --name <F> --callers` a function's or global's referrers. Whether a user
stays C is read from those whole lists. `query types --name <T> --field-touchers` lists the
functions that touch each field.

The layout users are read from T2's `layout_uses.csv`, which the tables extracted before
it lack, and the memory users from the lifecycle roles of the ownership store and T2's
`arg_casts.csv`: without the store's raw roles, `memory_unmanaged_after` is `null`, and
the planner establishes the roles first, as `docs/type-lifecycle.md` describes.

## Batches

### Versioning › Lifecycle › Batches

The CodeQL database and tables under `crustify/wavefront/codeql/`, and wavefront's
`.cache`, are gitignored state every batch needs: they are symlinked into each batch's
worktree once it is forked.

## Binding and porting

### Binding › Item analysis

The configuration, `crustify/wavefront/configs/wavefront-config.json`,
answers the queries an item's analysis needs, and the analysis's findings are submitted
with the CLI's `--update`, to be queried again rather than re-derived.

A type-erased parameter or field is looked up in the campaign's T3
`crustify/wavefront/t3/chased_casts.csv` before it is bound: an `erased_arg` or
`erased_field` row names the type it holds, and a `base_derived` row the base a type is
reached through, and the binding names that type rather than a raw pointer. The instances
of a generator in `type_generators.csv` share one generic, with per-instance aliases.

### Binding › Type route › Surface

A type's lifecycle primitives are identified as `docs/type-lifecycle.md` describes, and
submitted through the CLI's `--update`.

### Binding › Symbol route › Lifecycle strategies

Each foundational item's lifecycle role is in the ownership store, where planning
submitted it, and is queried for every item of the batch. A role that the item's body
contradicts is corrected through the CLI's `--update`, and the correction named in the
batch's commit message.

### Porting › Surface

A ported type's lifecycle primitives are identified as `docs/type-lifecycle.md`
describes, and submitted through the CLI's `--update`.

## Reviewing

### Reviewing › Objectives

#### Lifecycle (`lifecycle`)

Lifecycles submitted to wavefront that are incomplete: a releaser, disposer, cloner or
constructor that the findings of the batches that bound or ported `type` items, or items
of the foundational modules, missed. They are checked against the lifecycle primitives
`docs/type-lifecycle.md` identifies.

#### The submitted findings

Whatever the objectives, a review checks the pointer-related findings an earlier run submitted for the
workset: ownership, access, nullability, cardinality and keepalive. A wrong inference is a
finding.

#### Unsafety

The plan cuts the cycles between modules and types. A raw pointer that stands in for a
dependency a later scheduled batch wraps is such a cut, not an `unsafety` finding.

### Reviewing › Reports

A finding on wavefront's findings is filed in its own `<slug>` directory, with its report
and the evidence that proves the submitted finding wrong or incomplete, under:

- `<reviews dir>/wavefront/ownership/`, for a wrong pointer-related inference; or
- `<reviews dir>/wavefront/lifecycle/`, for an incomplete lifecycle.

A defect in wavefront itself is no finding on its findings: it is filed on a dedicated
branch and worktree of the local wavefront checkout, as any tool defect is.

### Reviewing › Fixes

Under `fix`, each corrected or completed set of findings is submitted again through the
CLI's `--update`, and a completed lifecycle gets the representations the Rust is missing.

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
