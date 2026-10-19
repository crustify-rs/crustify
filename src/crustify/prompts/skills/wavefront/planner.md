<!-- SKILL -->

Read wavefront's CLI helpstring via `--help` to learn how to use it.

## Workflow

The following steps augment your base workflow.

### For 1. The committed plan

Bring the wavefront artifacts up to date as you do the plan, as steps 2 and 3 describe:

- emit a configuration for every subsystem that has none, and the T3 tables under
  `crustify/wavefront/t3/` when they do not exist yet;
- update a configuration or table that follows an earlier wavefront schema to the current
  one, keeping its rows;
- for a subsystem or items the scope adds, add the T3 rows their erased slots, casts and
  macros call for; and
- check the configurations under `crustify/wavefront/configs/` against
  `subsystems.json`, and the T3 tables against the source and the T1/T2 tables, row by row
  and for the rows they miss (step 3), and correct what is wrong.

A changed configuration or T3 row changes the DAGs wavefront builds from it: re-emit the
`schedule.json` of every subsystem whose waves or batches it moves, and the order in
`subsystems.json` when the campaign-wide configuration moves it.

File each correction as the base workflow describes, in the reviews sub-directory of what
it amends:

- `crustify/reviews/planner/subsystems/` for a configuration, with the
  `subsystems.json` finding it follows from;
- `crustify/reviews/planner/chased-casts/` for `chased_casts.csv`: the rows changed or
  removed, and for each `add` row the chain you followed, hop by hop with `file:line`, or
  the hop that breaks it, and for each `drop` row the cast sites that derive the edge,
  with `file:line`, and why they are no polymorphism; and
- `crustify/reviews/planner/type-generators/` for `type_generators.csv`: the rows
  changed or removed, and for each the macro's invocation sites, conditional ones
  included, and the shapes they mint.

A report on a T3 table also states the DAG change the edit makes.

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

Do this before forming any DAG with wavefront. Wavefront states only what its
syntactic queries see, and derives some cast edges from it that need your judgement too.
You record both corrections in the T3 tables. Set `"t3_dir": "t3"` in every
`wavefront-config.json` (relative to `state_dir`, so `crustify/wavefront/t3/`): one
campaign-wide pair of tables serves every configuration. Track the directory. Read
`docs/artifacts/t3.md` from wavefront's checkout for the columns, and `docs/graph.md` for
how wavefront derives the edges they correct. Wavefront checks every row's entities when
it loads them and stops on a bad row, naming it.

- `chased_casts.csv`. Each row has an `op`: `add` states an edge wavefront misses, `drop`
  removes a cast edge it derives. A row names an erased slot and the `type` it holds
  (`erased_arg`, `erased_field`), or a pair's base `type` and its `derived` type
  (`base_derived`). The edges run:
  - `erased_arg`: the function depends on the type its `void *` parameter holds;
  - `erased_field`: what a type-erased field holds depends on the field's owner. The
    owner is the generic container (`AVFrameSideData`), the type one instance of it
    (`AVStereo3D`), ordered as a derived type on its base; and
  - `base_derived`: the derived type depends on its base.
- Edges wavefront misses (`add`). It records a cast only where it is written at a slot: a
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
  - A subsystem's graph keeps a cast edge only between two nodes of its own closure, so
    a relation between two of its types that runs through a type another subsystem owns
    is lost there. Find these in the campaign-wide configuration and record the edge
    directly between the subsystem's two types.
- Edges wavefront derives (`drop`). It turns three kinds of written cast into edges: what
  a `void *` parameter's own body reads it as, what a type-erased field is stored or read
  as (its variants, `erased_as` on the field in `query types`, scalar pointers such as
  `uint8_t *data` included), and casts between two named types, direct or through one
  slot. Review every one whose two ends are public, in the campaign-wide configuration,
  and drop each that is no polymorphism:
  - an alignment pun: a byte buffer read through `union unaligned_32` or `av_alias32` by
    the `AV_RN*` / `AV_WN*` macros (`AVPacket.data`, `extradata`);
  - a slot one file reuses for an unrelated type: `AVStream.priv_data` holding the
    `AVPacket` in `flacenc.c`, or the `AVFormatContext` in `sapenc.c`; and
  - the first-member convention: a `priv_data` read as `AVClass` because the private
    context it holds starts with an `AVClass *`. That type heads the private context,
    not an instance of the owner, and as an edge it closes a cycle with the owner's own
    `av_class` field.
  Keep what the public contract names: `AVFrameSideData.data` holding the struct its
  `type` names, `AVBufferRef.data` of a hardware device holding an `AVHWDeviceContext`.
- Wavefront warns, when it builds a DAG, about a row that corrects nothing: a `drop` of an
  edge it does not derive, or an `add` of a body read or variant it already derives.
  Correct or delete each such row.
- `type_generators.csv`. `t2/macro_generated_types.csv` lists which macro invocation
  minted which type. Wavefront treats no macro as a generator on its own. Record a
  macro as one when it is a template: invoked at several sites, each minting the same
  shape (`GIT_HASHMAP_STRUCT`, `git_array_t`), not a one-off definition
  (`FF_PAD_STRUCTURE`). Check the source for invocations conditional compilation hides
  from the extracted build. Name a macro the generator expands into a family of its
  own with `derived_kind = macro`.
- Under `--api-headers-only` a graph keeps a cast edge, a row's included, only when both
  of its ends are in its API closure: what the public signatures and fields reach from
  the configuration's API items. Rows outside it are still checked and kept for the
  records, and generators count only when defined in `api_headers`.
- Write the tables before you run `schedule`.

#### Scheduling

- Leverage the per-subsystem `wavefront-config.json` when emitting each subsystem's
  `schedule.json` to form dependency-ordered DAGs over its type/symbol batches, and the
  campaign-wide one to order link units and subsystems in `subsystems.json`.

- A `schedule --api-headers-only` holds only the configuration's own items. An item
  another subsystem's `api_headers` publish is scheduled there, after its own fields; it
  stays a dependency of the items that reach it, and `query dag --name X --imported-only`
  lists an item's imported dependencies.

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
