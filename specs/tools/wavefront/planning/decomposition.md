# wavefront › planning/decomposition

## Runs

Wavefront's planning artifacts are the configuration under `crustify/wavefront/configs/`
and the T3 tables under `crustify/wavefront/t3/`. Each planner run brings them up to date
with the plan: it emits what is missing, updates what follows an earlier wavefront schema,
adds what the scope adds, and corrects what is wrong. A changed configuration or T3 row
changes the DAGs wavefront builds, so the `todo` waves whose batches it moves are
re-planned, and the `depends_on` in `modules.json` when the configuration moves them.

## Dependencies

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

## Foundational modules

The foundational modules' candidates are selected from the configuration's
graph, after the T3 tables are written, so that their cast edges resolve type-erased
values: the type-erased units that no cast edge ties to a named type, and the units whose
pointers carry the `string` property, that depend on no other module's types. Each
candidate's body is read before it is admitted.

Each member's lifecycle role (allocator or constructor, releaser, disposer, cloner) is
submitted to the ownership store through the CLI's `--update`, as `docs/type-lifecycle.md`
describes, so that the bindings of the foundational modules find it there.
