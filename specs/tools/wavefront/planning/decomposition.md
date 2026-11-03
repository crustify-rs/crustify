# wavefront › planning/decomposition

## Runs

Wavefront's planning artifacts are the configurations under `crustify/wavefront/configs/`
and the T3 tables under `crustify/wavefront/t3/`. Each planner run brings them up to date
with the plan: it emits what is missing, updates what follows an earlier wavefront schema,
adds what the scope adds, and corrects what is wrong. A changed configuration or T3 row
changes the DAGs wavefront builds, so the `todo` waves whose batches it moves are
re-planned, and the `depends_on` in `modules.json` when the campaign-wide configuration
moves them.

## Dependencies

Each module's configuration is authored from its `modules.json` record: its files, and the
entities its file entries' `items` lists select, expressed as the configuration's
`items.included` and `items.excluded`, each entry naming its `kind`, so that every entity
is targeted by exactly one module's configuration and no two schedules hold one entity. A
struct tag and a function or global may share a name in one file, so an entry names the
kind it means, and a schedule skips one as `--skip type:<name>` or `--skip symbol:<name>`.
Macros are imported in every configuration and selected by none. Every configuration is
verified against the CLI.

The module's configuration gives the exact counts and the dependency records of its
`depends_on`.

## Foundational modules

The foundational modules' candidates are selected from the campaign-wide configuration's
graph, after the T3 tables are written, so that their cast edges resolve type-erased
values: the type-erased units that no cast edge ties to a named type, and the units whose
pointers carry the `string` property, that depend on no other module's types. Each
candidate's body is read before it is admitted.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
submitted to the ownership store through the CLI's `--update`, as `docs/type-lifecycle.md`
describes, so that the bindings of the foundational modules find it there.
