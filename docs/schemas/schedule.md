# schedule.json schema

Field meaning for `<workdir>/crustify/campaigns/<campaign-id>/schedule.json`,
the campaign's total execution order. Layout example:
[`specs/schedule.json`](../../specs/schedule.json).

The orchestrator emits it once, after `subsystems.json` and after running
`wavefront schedule` for every sub-campaign. Nothing in it is discovered during
execution: link units, subsystems, waves and batches are all computable before
the first agent starts, and writing them down makes a campaign's cost and shape
reviewable in advance.

It records **order and placement only**. Batch membership lives in each
sub-campaign's wave plan (`docs/schemas/wave.md`) and is not copied here — one
source of truth, so the two cannot drift.

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
| `objective` | execution objective the orchestrator assigns this wave's batches: `wrap`, `port` or `review` |
| `plan` | repo-relative path to the sub-campaign wave plan holding this wave's membership |
| `plan_wave` | index into that plan's own `waves` array |
| `dir` | repo-relative wave directory; holds `batch-<index>.json` and `logs/` |
| `batches` | the batches of this wave, which execute in parallel |

`index` and `plan_wave` are different numbers: the first orders the campaign,
the second addresses a wave inside one sub-campaign's plan. Both are needed —
neither is derivable from the other once several sub-campaigns interleave.

## waves[*].batches[*]

| field | meaning |
|---|---|
| `index` | position in the wave; names the file `<dir>/batch-<index>.json` |
| `kind` | objective-neutral route: `type`, `symbol` or `raw-lifetime` |

`kind` is repeated from the plan so a reader sees a wave's parallel shape
without opening it. Item lists are not repeated.

## What is deliberately absent

No status, progress or result fields. A wave is done because its integration
branch landed and its artifacts are on disk; recording it here would create a
second answer that can disagree with the first.
