# Thin batch schema

Field meaning for the JSON the orchestrator passes to `crustify spawn-binder <workdir>
<batch.json> --base-branch <wave branch> --output <batch dir>` for a `wrap` batch, to
`crustify spawn-translator` with the same arguments for a `port` batch, or to `crustify
spawn-reviewer` for a review batch. One batch is one agent's entire worklist, and each
command rejects a batch whose objective belongs to another.

The orchestrator plans it as one batch entry of `docs/translate/schemas/schedule.md` and
writes it out verbatim.

It lands as `batch.json` in that batch's own directory, beside the log and usage record
the agent writes there. The harness reads it once and the file names no wave, branch, log
path or dependency: everything about where the batch sits is the directory it sits in.

```json
{
  "objective": "wrap",
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "type",
      "field_anchors": ["data", "linesize"],
      "home": "crustify/rust/ffmpeg/libavutil/frame.rs"
    }
  ]
}
```

| root field | meaning |
|---|---|
| `objective` | execution objective for every item: `wrap` or `port` |
| `items` | non-empty worklist; every item routes to the same agent |

Both are required and no other root field is accepted.

## Review batches

A review batch carries, instead of `objective`, an optional `objectives` array, and reviews
either the same `items` or, in an audit, `modules`:

```json
{
  "objectives": ["lifecycle", "unsafety", "ub", "equiv", "fix"],
  "items": [ ... ]
}
```

```json
{
  "objectives": ["ub", "equiv", "disclose"],
  "modules": ["src/frame.rs", "src/codec/"]
}
```

| root field | meaning |
|---|---|
| `objectives` | the review objectives to run; optional, every one the reviewer offers that applies when absent |
| `items` | as above |
| `modules` | repo-relative source files and directories of a crate wavefront does not describe; route `modules` |
| `reports` | repo-relative report dirs, `crustify/reviews/<batch id>/<kind>/<slug>`, to revisit |

A batch carries `items` or `modules`, not both, and needs at least one of `items`,
`modules` and `reports`; one with only `reports` has route `reports`. `reports` is given
exactly when `revisit` is among the objectives, and an absent `objectives` includes
`revisit` exactly when `reports` is given. No other root field is accepted.

The reviewer's prompt offers `unsafety`, `contracts`, `ub`, `equiv`, `internal`,
`conventions`, `misc`, `coverage`, `revisit`, `disclose` and `fix`, with `conventions`
applying to a Crustify-generated batch only. Its skills add their own. A batch naming
an objective the installed skills do not offer is rejected.
Without `fix`, the reviewer reports and reproduces what it finds but patches nothing.

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

`home` is the sole placement input. A translator resolves no repo-tier artifact to decide
where an item goes, so the tree the batch names must still exist when its agent starts: do
not restructure `rust/` during a wave.

## Routes

`kind` selects the agent route, and every item in a batch must select the same one. A
batch mixing routes is rejected.

| kind | route |
|---|---|
| `type` | `type` |
| `symbol`, `callback` | `symbol` |
| `raw-lifetime` | `raw-lifetime` |

A `raw-lifetime` batch holds exactly one item, named `void` or `string`, with `defined_in:
null`. Its task objective is always `wrap`: raw lifetime discovery wraps a C primitive, so
`port` normalizes to `wrap`, and the batch runs under the binder.
