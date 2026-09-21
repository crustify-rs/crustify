# schedule.json schema

Field meaning for `<workdir>/crustify/campaigns/<campaign-id>/schedule.json`,
the campaign's total execution order. Layout example:
[`specs/schedule.json`](../../specs/schedule.json).

The orchestrator emits it once, after `subsystems.json` and after running
`wavefront schedule` for every sub-campaign. Nothing in it is discovered during
execution: link units, subsystems, waves and batches are all computable before
the first agent starts, and writing them down makes a campaign's cost and shape
reviewable in advance.

Each sub-campaign's objective-neutral plan from `wavefront schedule` is the
input; this document is the orchestrator's projection of those plans into one
ordered, objective-bearing whole.

| root field | meaning |
|---|---|
| `schema_version` | `1` |
| `campaign` | campaign id; the directory this file sits in |
| `subsystems` | repo-relative path to the `subsystems.json` this order was derived from |
| `waves` | every wave of the campaign, in execution order |

## waves[*]

`waves` is the campaign's total order. Entry *n* runs only after entry *n-1*
has landed, been reviewed, and passed its regression gate — including across a
link-unit or subsystem change, which is what makes this a total order rather
than a set of independent per-subsystem sequences.

| field | meaning |
|---|---|
| `index` | position in the campaign's total order, from zero |
| `link_unit` | containing link unit's `name` in `subsystems.json` |
| `subsystem` | containing subsystem's `name`, or `raw-lifetime-void` / `raw-lifetime-string` |
| `batches` | the batches of this wave, which execute in parallel |

## waves[*].batches[*]

A batch entry **is** a thin batch: the exact object `crustify translate`
accepts, documented in `docs/schemas/batch.md`. It carries `objective` and
`items` and nothing else — no index, no route, no paths.

`objective` sits here rather than on the wave because it is a per-batch
decision. A port campaign wraps a type while C still reads its fields and
ports it afterwards, so one wave can hold batches of differing objectives.

Writing a batch out is a copy, not a transformation: the entry is serialized
verbatim to its `batch-<index>.json`, with no field added or removed. That is
the whole reason the schemas are identical — a projection step that reshaped
anything could reshape it wrongly.

## Derived paths

Nothing records a path that `(campaign, link_unit, subsystem, index)` already
determines:

```text
crustify/campaigns/<campaign>/<link_unit>/<subsystem>/wave-<index>/
├── batch-<n>.json      n is the batch's position in `batches`
└── logs/               passed to every batch in the wave as --output
```

Wave directories are named by the campaign-global `index`, so they are unique
across the whole campaign, and the integration branch
`crustify/wave/<campaign>/<link_unit>/<subsystem>/wave-<index>` carries the
same coordinates.
