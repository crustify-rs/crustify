<!-- SKILL -->

Before your first command, read wavefront's `README.md`, its `--help`, and the documents
under its `docs/`: `scoping.md`, `graph.md` and `batching.md` for how it selects, orders
and batches, and `artifacts/t3.md` for the T3 tables. What follows is only how the
campaign uses it.

## Workflow

The following steps augment your base workflow.

### For 1. The committed plan

Your wavefront artifacts are the configurations under `crustify/wavefront/configs/` and
the T3 tables under `crustify/wavefront/t3/`. Bring them up to date as you do the plan:
emit what is missing, update what follows an earlier wavefront schema, add what the scope
adds, and correct what is wrong.

A changed configuration or T3 row changes the DAGs wavefront builds: re-plan the `todo`
waves whose batches it moves, and the `depends_on` in `modules.json` when the
campaign-wide configuration moves them.

File each correction in the reviews sub-directory of what it amends:

- `crustify/reviews/planner/modules/` for a configuration, with the
  `modules.json` finding it follows from;
- `crustify/reviews/planner/chased-casts/` for `chased_casts.csv`: for each `add` row
  the chain you followed, hop by hop with `file:line`, or the hop that breaks it; for each
  `drop` row the cast sites that derive the edge, and why they are no type relation; and
- `crustify/reviews/planner/type-generators/` for `type_generators.csv`: the macro's
  invocation sites, conditional ones included, and the shapes they mint.

A report on a T3 table also states the DAG change the edit makes.

### For 2. Module decomposition

The campaign has two kinds of `wavefront-config.json`:

- the campaign-wide `crustify/wavefront/configs/wavefront-config.json`, whose
  `impl_files` and `api_headers` are the union of every module's. Binders, translators
  and reviewers resolve their queries through it, it orders the link units and modules,
  and only its graph shows the relations between two modules; and
- one `crustify/wavefront/configs/<link-unit>/<module>/wavefront-config.json` per
  module, which finds the module's dependency edges. Use them for the exact counts and
  the `imported_deps` in `modules.json`, and for the module's schedule.

Every configuration shares `crustify/wavefront/` as its `state_dir` and sets
`"t3_dir": "t3"`, so one campaign-wide pair of T3 tables serves them all. Verify each
configuration you author against the CLI.

Author each module's configuration with its `modules.json` record as the reference: its
files, and the entities its file entries' `items` lists select, expressed through the
configuration's `items` and `out_of_scope.items`, so that every entity is targeted by
exactly one module's configuration and no two schedules hold one entity. Macros are
imported in every configuration and selected by none.

Select the foundational modules' candidates from the campaign-wide configuration's
graph, after the T3 tables are written, so that their cast edges resolve type-erased
values: the type-erased units that no cast edge ties to a named type, and the units whose
pointers carry the `string` property, that depend on no other module's types. Read
each candidate's body before you admit it.

Submit each member's lifecycle role (allocator or constructor, releaser, disposer,
cloner) to the ownership store through the CLI's `--update`, as `docs/type-lifecycle.md`
describes, so that the binders of the foundational modules find it there.

### For 3. Planning

#### T3 tables

Write the T3 tables before you schedule. Review, in the campaign-wide configuration:

- every type-erased parameter and field (`is_erased` in `t1/params.csv` and
  `t1/fields.csv`) with no cast in `t2/arg_casts.csv` or `t2/field_casts.csv`, following
  the value until it is read as a named type, stored, returned or lost. A hop that
  dispatches on a tag and reads different types per branch establishes none of them;
- every cast edge wavefront derives between two public types, dropping each that is no
  type relation;
- every public type in a cast relation, recording the pairs that are a hierarchy as
  `base_derived` rows; and
- the type-minting macros in `t2/macro_generated_types.csv`, checking the source for
  invocations conditional compilation hides from the traced build.

A per-module graph keeps a cast edge only between two nodes of its own closure, so a
relation between two of its types through a type another module owns is lost there:
record it as a row directly between the module's two types. Correct or delete each row
wavefront warns is stale.

#### Scheduling

- Schedule each module from its own configuration, and order the link units and
  modules from the campaign-wide one.
- Select the module's files with `--transitive`; use an exact selection only when the
  dependencies it leaves out are already satisfied or intentionally excluded.
- A wrap campaign schedules with `--api-headers-only`.
- Pass the campaign's `workload` caps as the batch limits.
- `wavefront schedule` numbers its waves from 0 in every run: append them to
  `schedule.json` after its highest index, in wavefront's order, each depending on the
  wave before it and on the last waves of the modules its units depend on, and record
  the run's `budgets` on each. Write each output to `crustify/tmp/`, never over
  `schedule.json`.
- For a port campaign's types, `query types --name <T> --field-touchers` lists the
  functions that touch each field, and `--users` every function that mentions the type;
  the users that touch no field are the layout users to check in the source. Find the
  globals and embedding structs in `t1/globals.csv` and `t1/fields.csv`.
