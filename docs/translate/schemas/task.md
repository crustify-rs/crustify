# task.json schema

Field meaning for `task.json`, the one input of a spawned agent: `crustify spawn-binder
<workdir> <batch dir>/task.json --log-dir <batch dir>` for a `wrap` batch, `crustify
spawn-translator` with the same arguments for a `port` batch, `crustify spawn-reviewer`
for a review batch, and `crustify spawn-planner <workdir> <run dir>/task.json --log-dir
<run dir>` for a planner run. The path names the file itself; a missing file fails the
command. One task is one
agent's entire worklist and how that agent runs, and each command rejects a task whose
objective belongs to another.

A planner plans a binder's or translator's task as one batch entry of
`docs/translate/schemas/schedule.md`. The orchestrator writes that entry as `task.json`,
adding the [run fields](#run-fields) it decides when it launches the batch.

`task.json` sits in the batch's own directory, which the orchestrator also passes as
`--log-dir`. The agent writes its log and usage record there, so the directory holds
everything about the batch: what it was given, how it ran, and what it produced. The file names no wave, log path or dependency.

```json
{
  "objective": "wrap",
  "base_branch": "crustify/waves/libavutil/frame/wave-0",
  "model": "anthropic/claude-opus-5-5",
  "billing": "subscription",
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
| `base_branch`, `model`, `billing` | the [run fields](#run-fields) |

All five are required and no other root field is accepted.

## Run fields

| field | meaning |
|---|---|
| `base_branch` | the unchecked-out integration branch the agent lands on: its wave branch, or its review wave branch; a `refs/heads/` prefix is accepted |
| `model` | the agent's model, `<provider>/<model>`, such as `anthropic/claude-opus-5-5`; an unknown provider is rejected |
| `billing` | how the provider CLI authenticates: `subscription`, its own logged-in account, or `api`, an API key from the environment |

A binder, translator or reviewer task carries all three. A planner task carries `model`
and `billing` only: a planner commits on the campaign branch it is spawned on, and lands on
no other.

The settings a campaign ran under are recorded twice: per batch in its `task.json`, and per
campaign in the history of `crustify/CRUSTIFY.md`.

## Review batches

A review batch carries, instead of `objective`, an optional `objectives` array, and a Rust
worklist instead of `items`: in a translate campaign, the commits its translation batches
landed; in an audit, modules of the crate.

```json
{
  "objectives": ["lifecycle", "unsafety", "ub", "equiv", "fix"],
  "commits": ["3f2a9c1", "8be04d7"],
  "base_branch": "crustify/reviews/libavutil/frame/wave-0",
  "model": "anthropic/claude-opus-5-5",
  "billing": "subscription"
}
```

```json
{
  "objectives": ["ub", "contracts", "disclose"],
  "modules": ["src/frame.rs", {"path": "src/codec.rs", "types": ["Decoder"], "trait_impls": ["Drop for Decoder"], "functions": ["open_input"]}]
}
```

| root field | meaning |
|---|---|
| `objectives` | the review objectives to run; optional, every one the reviewer offers that applies when absent |
| `commits` | distinct commit ids, as they sit on the wave branch; route `commits`. Each commit's `Batch:` trailer names the translation batch whose `task.json` lists its C items |
| `modules` | repo-relative source files and directories; route `modules`. An entry may instead be `{"path", "types", "trait_impls", "functions"}`, naming the parts of a module too large to review whole: types, each with its fields and inherent impls; trait impls, each `<trait> for <type>` as its impl header spells it; and free functions |
| `reports` | repo-relative report dirs, `crustify/reviews/<batch id>/<kind>/<slug>`, to revisit |

The run fields are required, as on a translation task; the second example leaves them out.
A batch carries `commits` or `modules`, not both, and needs one of them or `reports`; one
with only `reports` has route `reports`. A module path appears once, and a module object
names one or more of `types`, `trait_impls` and `functions`, each a distinct list. `reports` is given exactly when `revisit` is among the
objectives, and an absent `objectives` includes `revisit` exactly when `reports` is given.
No other root field is accepted.

The reviewer's prompt offers `unsafety`, `contracts`, `ub`, `equiv`, `internal`,
`conventions`, `misc`, `coverage`, `revisit`, `disclose` and `fix`, with `conventions`
applying to a Crustify-generated batch only. Its skills add their own. A batch naming
an objective the installed skills do not offer is rejected.
Without `fix`, the reviewer reports and reproduces what it finds but patches nothing.

## Planner tasks

A planner task names the one arm a planner run executes, and how it runs: the plan it works
on is the campaign branch it is spawned on.

```json
{"objective": "review", "model": "anthropic/claude-opus-5-5", "billing": "subscription"}
```

| root field | meaning |
|---|---|
| `objective` | `emit`: create the plan, or add what the committed plan lacks, leaving its judgements as they are; `review`: assess the committed judgements, correct them, and file a report per edit |
| `model`, `billing` | the [run fields](#run-fields) |

All three are required and no other root field is accepted. The orchestrator writes it as
`task.json` in the run's artifact dir, `crustify/artifacts/planning/run-<k>/`.

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
