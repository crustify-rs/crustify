# wavefront › rust/items/binding

## Item analysis

The configuration, `crustify/wavefront/configs/wavefront-config.json`,
answers the queries an item's analysis needs, and the analysis's findings are submitted
with the CLI's `--update`, to be queried again rather than re-derived.

A type-erased parameter or field is looked up in the campaign's T3
`crustify/wavefront/t3/chased_casts.csv` before it is bound: an `erased_arg` or
`erased_field` row names the type it holds, and a `base_derived` row the base a type is
reached through, and the binding names that type rather than a raw pointer. The instances
of a generator in `type_generators.csv` share one generic, with per-instance aliases.

## Type route › Surface

A type's lifecycle primitives are identified as `docs/type-lifecycle.md` describes, and
submitted through the CLI's `--update`.

## Symbol route › Lifecycle strategies

Each foundational item's lifecycle role is in the ownership store, where planning
submitted it, and is queried for every item of the batch. A role that the item's body
contradicts is corrected through the CLI's `--update`, and the correction named in the
batch's commit message.
