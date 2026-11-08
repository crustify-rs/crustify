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
- Wavefront numbers its waves from 0 in every run, so they are appended after
  `schedule.json`'s highest index, in wavefront's order, their `depends_on` renumbered,
  with their module's `layer` and their `sublayer`. A wave's `items` are those of its
  wavefront batches, each with its `name`, `defined_in` and `kind`, its `used_fields` as
  `field_anchors`, the `home` its module gives it, and its `objective`. An item a wave
  that has started holds, or that a batch has landed with that objective, is dropped, and
  a dependency on it is one on that wave.
- With merged waves, the waves of the same `layer` and `sublayer` merge into one, which
  keeps every module's items, and whose `depends_on` is the union of theirs, less the
  waves merged into it.

## Wrap batches

The units a batch's items depend on are their `depends_on`, `scheduled` and `cut`, in
the planner run's wavefront schedule, or `query dag --name <items>`. A wrap batch's items
are closed over their wrap dependencies on the public-signature graph,
`query dag --name <items> --api-headers-only`, less what has landed.

## Porting types

Wavefront's T2 `layout_uses.csv` records every kind of layout use, and
`query types --name <T> --layout-users` lists a type's users with the site and kind of
each use; a test the closure leaves out is no user. A port campaign's schedule, which is
not `--api-headers-only`, gives each scheduled struct or union its `opaque_after`, whose
`closure` record names the `modules` of its last layout users over the order of the whole
closure, those no other user depends on, the type's own module among them when its own
wave is. Those modules, less the type's own, are the ones whose integration its `port`
waits for; with none left, it is `port` where the order places it. Whether a user stays C
is read from the whole list, `--layout-users`. `query types --name <T> --field-touchers`
lists the functions that touch each field.
