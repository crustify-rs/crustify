# Sub-campaign schedule schema

A campaign is the orchestrator's end-to-end translation session. Each
sub-campaign mirrors one subsystem and its schedule contains sequential
**waves**; each wave contains parallel **batches**. `wavefront schedule` writes
the objective-neutral composition. The orchestrator projects each recorded
batch into the thin, objective-bearing input accepted by `crustify translate`.
Crustify does not execute or reinterpret this whole document.

The filename is not identity. `schedule --output` accepts any path whose parent
directory already exists, so tracked plans normally use descriptive names such
as `crustify/campaigns/<target>/<sub-campaign>/types.json`, beside that
sub-campaign's narrow `wavefront-config.json`. The orchestrator scaffolds the
sub-campaign directory; the oracle never creates it. For execution, it numbers
the `waves` array as `wave-0`, `wave-1`, and so on, and routes each harness's
generated logs to that wave's `logs/` directory.

## Version 3

```json
{
  "schema_version": 3,
  "oracle_config": {
    "path": "crustify/campaigns/src/widget/wavefront-config.json",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "api_headers_only": false,
  "budgets": {
    "max_syms": 25,
    "max_loc": 500,
    "max_types": 2,
    "min_fields": 20
  },
  "summary": {
    "unit_count": 3,
    "layer_count": 2,
    "batch_count": 2,
    "file_count": 2
  },
  "waves": [
    {
      "unit_count": 2,
      "batches": [
        {
          "kind": "type",
          "source_file": "include/example.h",
          "items": []
        }
      ]
    }
  ]
}
```

`oracle_config` records the exact `--config` input as a repository-relative or
absolute path plus its SHA-256. The orchestrator rejects the plan if that config
is missing or has changed since scheduling. `api_headers_only` records the
selection mode and `budgets` records the packing limits used by the oracle.

`summary` gives totals for the selected units, underlying dependency layers,
emitted batches, and distinct batch source files. Selected items occur exactly
once under their batch; there is no duplicate `plan_items` table. Dependencies
are self-contained references on those items; there is no separate
`dependency_nodes` table. Each item's `layer` is the sole copy of its DAG layer;
consumers derive a wave's layer set from its batched items.

## Waves and batches

The orchestrator executes waves in array order behind full translation,
adversarial-review and regression barriers. A wave contains one or more
topological DAG `layers`; each wave must land before the next starts. The
oracle folds adjacent layers whenever the merged work fits one batch, including
for non-transitive selections. A fold never creates parallel producer and
consumer batches.

The batches within one wave may execute concurrently. `kind` records the
objective-neutral route (`type`, `symbol`, or the special `raw-lifetime` route),
`source_file` records its source grouping, and `items` is the exact worklist the
orchestrator projects for one agent.

Each item has this shape:

```json
{
  "name": "example_new",
  "defined_in": "src/example.c",
  "kind": "symbol",
  "source_kind": "function",
  "layer": 1,
  "loc": 12,
  "deps": {"types": [], "symbols": []},
  "fallback": [],
  "back_fill": [],
  "generates": [],
  "field_anchors": []
}
```

Every reference in `deps`, `fallback`, and `back_fill` is
`{"name": "...", "defined_in": "...", "scope": "wrap|port|ext"}`. The scope
lets consumers understand dependency context without a second node table.
`field_anchors` occurs on batched items and lists the field accessors assigned
to that type batch.

Schema-v2 schedules with `steps`, `plan_items`, and `dependency_nodes` remain
historical campaign records and need not be rewritten. New schedules are
always schema v3, and only v3 batches are projected for new execution.
