# schedule.json schema

Field meaning for `<workdir>/crustify/campaigns/<campaign-id>/schedule.json`,
the campaign's total execution order. Layout example:
[`specs/schedule.json`](../../specs/schedule.json).

The orchestrator emits it once, before the first agent starts. Waves and
batches are computable in advance, so writing them down makes a campaign's
shape and cost reviewable before it spends anything.

It nests the way `subsystems.json` and the campaign directory do: link unit,
then subsystem, then wave. The campaign's total order is that nesting read
depth-first — every wave of link unit 0's first subsystem, then its second,
then link unit 1's. No wave records a campaign-wide position, because its
position is where it sits.

| root field | meaning |
|---|---|
| `schema_version` | `1` |
| `link_units` | the campaign's link units, in execution order |

## link_units[*]

| field | meaning |
|---|---|
| `index` | position in the campaign, from zero |
| `name` | link unit's `name` in `subsystems.json` |
| `subsystems` | its subsystems, in execution order |

Link units run to completion in turn, so a subsystem's dependencies in another
link unit must belong to an earlier one. Order link units by their dependency
graph and this holds; it is what the nesting assumes.

## link_units[*].subsystems[*]

| field | meaning |
|---|---|
| `index` | position within the link unit, from zero |
| `name` | subsystem's `name` in `subsystems.json`, or `raw-lifetime-void` / `raw-lifetime-string` |
| `waves` | its waves, in execution order |

## link_units[*].subsystems[*].waves[*]

Entry *n* runs only after entry *n-1* has landed, been reviewed and passed its
regression gate — and the last wave of a subsystem before the first wave of
the next, which is what makes the whole nesting a total order rather than
independent sequences.

| field | meaning |
|---|---|
| `index` | position within the subsystem, from zero |
| `batches` | the batches of this wave, which execute in parallel |

## …waves[*].batches[*]

A batch entry is a thin batch: the exact object `crustify translate` accepts,
documented in `docs/schemas/batch.md`. It carries `objective` and `items` and
nothing else.

`objective` is per batch, not per wave. A port campaign wraps a type while C
still reads its fields and ports it afterwards, so one wave holds batches of
differing objectives.

Writing one out is a copy: serialized verbatim to `batch-<index>.json`, no
field added or removed.

## Derived paths

Every index also addresses the filesystem, so nothing records a path:

```text
crustify/campaigns/<campaign-id>/<link_unit>/<subsystem>/wave-<index>/
├── batch-<n>.json      n is the batch's position in `batches`
└── logs/               every batch in the wave receives this as --output
```

The integration branch
`crustify/waves/<campaign-id>/<link_unit>/<subsystem>/wave-<index>` carries the
same coordinates.
