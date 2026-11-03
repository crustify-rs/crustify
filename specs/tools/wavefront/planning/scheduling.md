# wavefront › planning/scheduling

## Order

The link units and modules are ordered from the campaign-wide configuration, after its T3
tables are written. They are reviewed in that configuration:

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

A per-module graph keeps a cast edge only between two nodes of its own closure, so a
relation between two of its types through a type another module owns is lost there: it is
recorded as a row directly between the module's two types. A row wavefront warns is stale
is corrected or deleted.

## Waves and batches

- Each module is scheduled from its own configuration, its files selected with
  `--transitive`; an exact selection serves only when the dependencies it leaves out are
  already satisfied or intentionally excluded.
- A wrap campaign schedules with `--api-headers-only`.
- The campaign's `workload` caps are the batch limits.
- `wavefront schedule` numbers its waves from 0 in every run, so they are appended to
  `schedule.json` after its highest index, in wavefront's order, each depending on the
  wave before it and on the last waves of the modules its units depend on, with the run's
  `budgets` recorded on each. Each output is written to `crustify/tmp/`, never over
  `schedule.json`.

## Wrap waves

A wrap batch's items are closed over their wrap dependencies on the public-signature
graph, `query dag --name <items> --api-headers-only`, less what an earlier wave wrapped or
ported.

## Porting types

`query types --name <T> --field-touchers` lists the functions that touch each field of a
type, and `--users` every function that mentions it; the users that touch no field are the
layout users to check in the source. The globals and embedding structs are in
`t1/globals.csv` and `t1/fields.csv`.
