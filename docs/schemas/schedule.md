# schedule.json schema

Field meaning for `<workdir>/crustify/campaigns/<campaign-id>/schedule.json`,
the campaign's total execution order. Layout example:
[`specs/schedule.json`](../../specs/schedule.json).

The orchestrator emits it once, before the first agent starts. Waves and
batches are computable in advance, so writing them down makes a campaign's
shape and cost reviewable before it spends anything.

| root field | meaning |
|---|---|
| `schema_version` | `1` |
| `waves` | every wave of the campaign, in execution order |

## waves[*]

Entry *n* runs only after entry *n-1* has landed, been reviewed and passed its
regression gate — across a link-unit or subsystem change too, which is what
makes this a total order rather than independent per-subsystem sequences.

| field | meaning |
|---|---|
| `index` | position in the total order, from zero |
| `link_unit` | containing link unit's `name` in `subsystems.json` |
| `subsystem` | containing subsystem's `name`, or `raw-lifetime-void` / `raw-lifetime-string` |
| `batches` | the batches of this wave, which execute in parallel |

## waves[*].batches[*]

A batch entry is a thin batch: the exact object `crustify translate` accepts,
documented in `docs/schemas/batch.md`. It carries `objective` and `items` and
nothing else.

`objective` is per batch, not per wave. A port campaign wraps a type while C
still reads its fields and ports it afterwards, so one wave holds batches of
differing objectives.

Writing one out is a copy: serialized verbatim to `batch-<index>.json`, no
field added or removed.

## Derived paths

Nothing records a path that `(campaign-id, link_unit, subsystem, index)`
already determines:

```text
crustify/campaigns/<campaign-id>/<link_unit>/<subsystem>/wave-<index>/
├── batch-<n>.json      n is the batch's position in `batches`
└── logs/               every batch in the wave receives this as --output
```

Wave directories take the campaign-global `index`, so they are unique
campaign-wide, and the integration branch
`crustify/wave/<campaign-id>/<link_unit>/<subsystem>/wave-<index>` carries the
same coordinates.
