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
- Wavefront numbers its waves from 0 in every run, so the `todo` waves are numbered after
  the highest index of a started wave, in wavefront's order, their `depends_on` renumbered,
  with their module's `layer` and their `sublayer`. A wave's `items` are those of its
  wavefront batches, each with its `name`, `defined_in` and `kind`, its `used_fields` as
  `field_users`, the `home` its module gives it, its `objective`, and its
  `opaque_after`, `memory_unmanaged_after` and `unreferenced_after`, with the later stages
  they place, as [Later stages](#later-stages) describes. An item a wave
  that has started holds, or that a batch has landed with that objective, is dropped, and
  a dependency on it is one on that wave.

## Wrap batches

The units a batch's items depend on are their `depends_on`, `scheduled` and `cut`, in
the planner run's wavefront schedule, or `query dag --name <items>`. A wrap batch's items
are closed over their wrap dependencies on the public-signature graph,
`query dag --name <items> --api-headers-only`, less what has landed.

## Later stages

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
