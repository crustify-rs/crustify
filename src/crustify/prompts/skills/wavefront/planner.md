<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Workflow

The following steps augment your base workflow.

### For 1. Objective

#### Emit (`emit`)

Emit the wavefront artifacts the plan lacks, as steps 2 and 3 describe: a configuration
for every subsystem that has none, and the T3 tables under `crustify/wavefront/t3/` when
they do not exist yet. For a subsystem or items the scope adds, add the T3 rows their
erased slots, casts and macros call for, and leave the existing rows as they are.

#### Review (`review`)

Review an earlier planner's wavefront artifacts as you review its plan: the
configurations under `crustify/wavefront/configs/` against `subsystems.json`, and the T3
tables under `crustify/wavefront/t3/` against the source and the T1/T2 tables, row by
row and for the rows it missed (step 3).

File each finding as the base workflow describes, in the reviews sub-directory of what it
amends:

- `crustify/reviews/planner/subsystems/` for a configuration, with the
  `subsystems.json` finding it follows from;
- `crustify/reviews/planner/chased-casts/` for `chased_casts.csv`: the rows added,
  changed or removed, and for each the chain you followed, hop by hop with `file:line`,
  or the hop that breaks it; and
- `crustify/reviews/planner/type-generators/` for `type_generators.csv`: the rows
  added, changed or removed, and for each the macro's invocation sites, conditional ones
  included, and the shapes they mint.

A report on a T3 table also states the DAG change the edit makes: the `schedule` output
before and after it, for every configuration whose schedule moved.

### For 2. Subsystem decomposition

#### Configuring `wavefront-config.json`

After subsystem decomposition, emit campaign-wide and per-subsystem
`wavefront-config.json` specs that can be consumed by the wavefront CLI.

Selection rules:

- `impl_files` and `api_headers` seed the implementation graph.
- An entity is targeted when its definition is in a named file. For an entity without a
  body, all declarations must be in named files.
- Headers outside the implementation tree must be named when they define target types.
- Add a header to `api_headers` only when its implementors are in `impl_files`.
- Dependencies merely used by the target enter the imported closure.
- `--api-headers-only` selects declarations published by `api_headers` and does not walk
  bodies.
- A struct defined in `api_headers` retains field layout. A forward declaration remains
  opaque.
- `targeted` and `imported` describe ownership; `api` describes publication. These sets
  intersect.
- `out_of_scope.paths` changes selection. `out_of_scope.features` is documentation only.

##### Campaign-wide

- Configure a campaign-wide `crustify/wavefront/configs/wavefront-config.json` that every
  translator agent will resolve its queries through.

##### Per subsystem

- To get exact counts when authoring `subsystems.json`, configure for each subsystem a
  `crustify/wavefront/configs/<link-unit>/<subsystem>/wavefront-config.json`.

- Its `impl_files` and `api_headers` must be exact subsets of the campaign-wide
  configuration, and must mirror the subsystem's `implementation_files` and `api_headers`
  in `subsystems.json`.

- Verify the authored configurations against wavefront's CLI.

### For 3. Planning

#### T3 tables: chased casts and type generators

Wavefront states only what its syntactic queries see. Two kinds of dependency need your
judgement, and you record them in the T3 tables. Set `"t3_dir": "t3"` in every
`wavefront-config.json` (relative to `state_dir`, so `crustify/wavefront/t3/`), track
the directory, and read `docs/schemas/t3.md` from wavefront's checkout for the columns.
Wavefront checks every row's entities when it loads them and stops on a bad row, naming
it; each accepted row becomes one DAG edge.

- `chased_casts.csv`. Wavefront records a cast only where it is written at a slot: a
  value converted into a parameter or field, or that slot read as a named type. It does
  not follow a type-erased value (`void *`, `void **`) handed on through calls or
  locals, so a function that only passes its `void *` on gets no dependency on the type
  its callees read it as (`av_log` hands `avcl` to `av_vlog`, which reads `AVClass`).
  - Review every type-erased parameter and field (`is_erased` in `t1/params.csv` and
    `t1/fields.csv`) with no `to` row in `t2/arg_casts.csv` / `t2/field_casts.csv`.
    Follow it until it is read as a named type, or is stored, returned or lost.
  - A chain counts only when every hop hands the value on unchanged. A hop that
    dispatches on a tag (`switch (obj->flags)`) and reads different types per branch
    establishes none of them.
  - Record each established type as an `erased_arg` or `erased_field` row, and each
    base/derived pair joined through such slots as a `base_derived` row.
  - Casts between two named types order as written: a type cast to another depends on
    it, so a downcast puts the base after its derived type. `query types` shows both
    sides (`casted`, `casted_via`). For every public type in a cast relation, decide
    whether the pair is a hierarchy and record it as a `base_derived` row; the row
    replaces the cast's edge. Wavefront falls back to cast centrality only to break a
    cycle among the remaining casts.
- `type_generators.csv`. `t2/macro_generated_types.csv` lists which macro invocation
  minted which type. Wavefront treats no macro as a generator on its own. Record a
  macro as one when it is a template: invoked at several sites, each minting the same
  shape (`GIT_HASHMAP_STRUCT`, `git_array_t`), not a one-off definition
  (`FF_PAD_STRUCTURE`). Check the source for invocations conditional compilation hides
  from the extracted build. Name a macro the generator expands into a family of its
  own with `derived_kind = macro`.
- Under `--api-headers-only` chase public relations: erased slots of public functions
  and of structs defined in `api_headers`, pairs whose two types are both public, and
  generators defined in `api_headers`. Other rows are still checked and kept for the
  records, but add no edge in the API graph.
- Write the tables before you run `schedule`; rows only add edges.

#### Scheduling

- Leverage the per-subsystem `wavefront-config.json` when emitting `schedule.json` to form
  dependency-ordered DAGs over link units, subsystems, and type/symbol batches.

- Prefer `--transitive` so the subsystem includes the selected surface's in-scope
  producer dependencies. Use an exact non-transitive selection only when those
  dependencies are already satisfied or intentionally excluded.

- Wrap campaigns use `schedule --api-headers-only`.

- For a port campaign, `query types --name <T> --field-touchers` lists every function
  that touches each of a type's fields, and `--users` every function that mentions the
  type at all. A layout user that touches no field is among the `--users` that are not
  field touchers; check each in the source. Neither lists globals or embedding structs:
  find those in `t1/globals.csv` and `t1/fields.csv`.

- Use the established batch caps to limit agent work.
