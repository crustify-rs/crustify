# wavefront › planning/scheduling

## Order

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

## Waves and batches

- A planner run schedules once, with `wavefront schedule`: its `schedule_seeds` are the
  files of the modules it plans, and the schedule holds them and every unit they depend
  on, ordered over the whole closure. The output is written to `crustify/tmp/`, never
  over `schedule.json`.
- A wrap campaign schedules with `--api-headers-only`.
- The campaign's `workload` caps are its batch caps, `--max-types`, `--min-fields`,
  `--max-syms` and `--max-loc`.
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
- Wavefront numbers its waves from 0 in every run, so they are appended after
  `schedule.json`'s highest index, in wavefront's order, their `depends_on` renumbered,
  with their module's `layer`, their `sublayer` and the caps as their `budgets`. Each
  wavefront batch becomes a `wrap` batch of its wave's module, each item with its `name`,
  `defined_in` and `kind`, its `used_fields` as `field_anchors`, and the `home` its module
  gives it. An item a wave that has started holds is dropped, and a dependency on it is
  one on that wave.
- With merged waves, the waves of the same `layer` and `sublayer` merge into one, which
  keeps every module's batches, and whose `depends_on` is the union of theirs, less the
  waves merged into it.

## Wrap waves

A wrap batch's items are closed over their wrap dependencies on the public-signature
graph, `query dag --name <items> --api-headers-only`, less what an earlier wave wrapped or
ported.

## Porting types

`query types --name <T> --field-touchers` lists the functions that touch each field of a
type, and `--users` every function that mentions it; the users that touch no field are the
layout users to check in the source. The globals and embedding structs are in
`t1/globals.csv` and `t1/fields.csv`.
