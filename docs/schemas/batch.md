# Thin batch schema

Field meaning for the JSON the orchestrator passes to
`crustify <workdir> <target> translate <batch.json>`. One batch is one agent's
entire worklist.

The orchestrator projects it from one recorded batch of a sub-campaign
schedule — Wavefront's output, documented in that checkout's
`docs/schemas/schedule.md` — adding the execution objective and each item's
authored Rust home. Projection must not change batch membership.

The file is transient input, not a tracked artifact: it names no wave, branch,
log path or dependency, and the harness reads it once.

```json
{
  "objective": "wrap",
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "type",
      "field_anchors": ["data", "linesize"],
      "home": "crustify/rust/libavutil/src/frame.rs"
    }
  ]
}
```

| root field | meaning |
|---|---|
| `objective` | execution objective for every item: `wrap`, `port` or `review` |
| `items` | non-empty worklist; every item routes to the same agent |

Both are required and no other root field is accepted.

## items[*]

Every field is required on every item, and no other field is accepted.

| field | meaning |
|---|---|
| `name` | C entity name, non-empty |
| `defined_in` | repo-relative path of its definition; `null` only for `raw-lifetime` |
| `kind` | `type`, `symbol`, `callback` or `raw-lifetime` |
| `field_anchors` | C field identifiers assigned to this item; empty unless `kind` is `type` |
| `home` | repo-relative `.rs` path the item is authored into |

`(name, defined_in)` identifies an item and must be unique within the batch.
`field_anchors` must not repeat a name.

`home` is the sole placement input. A translator resolves no repo-tier artifact
to decide where an item goes, so the tree the batch names must still exist when
its agent starts: do not restructure `rust/` during a wave.

## Routes

`kind` selects the agent route, and every item in a batch must select the same
one. A batch mixing routes is rejected.

| kind | route |
|---|---|
| `type` | `type` |
| `symbol`, `callback` | `symbol` |
| `raw-lifetime` | `raw-lifetime` |

A `raw-lifetime` batch holds exactly one item, named `void` or `string`, with
`defined_in: null`. Its task objective is always `wrap` unless the batch
objective is `review` — raw lifetime discovery wraps a C primitive, so `port`
normalizes to `wrap`.
