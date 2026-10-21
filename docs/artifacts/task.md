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
`docs/artifacts/schedule.md`. That entry is written as `task.json`, with the
[run fields](#1-run-fields) decided when the batch launches.

`task.json` sits in the batch's own directory, which is also passed as
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
| `base_branch`, `model`, `billing` | the [run fields](#1-run-fields) |
| `instructions` | optional [additional instructions](#2-additional-instructions) |

All five are required, and `instructions` is the only other root field accepted.

## 1. Run fields

| field | meaning |
|---|---|
| `base_branch` | the unchecked-out integration branch the agent lands on: its wave branch, or its review wave branch; a `refs/heads/` prefix is accepted |
| `model` | the agent's model, `<provider>/<model>`, such as `anthropic/claude-opus-5-5`; an unknown provider is rejected |
| `billing` | how the provider CLI authenticates: `subscription`, its own logged-in account, or `api`, an API key from the environment |

A binder, translator or reviewer task carries all three. A planner task carries `model`
and `billing` only: a planner commits on the planning branch it is spawned on, which is
then promoted to the campaign branch.

## 2. Additional instructions

Every task may carry `instructions`, the path of a Markdown file, relative to the task's
own directory, that customizes the agent's task on top of its role:

```json
{"model": "anthropic/claude-opus-5-5", "billing": "subscription",
 "instructions": "instructions.md"}
```

The role's prompt has an `## Additional instructions` section, which states that the
instructions take precedence over the rest of the prompt where the two conflict; the
file's text fills it, and the section stays empty when the task names no file. An unreadable or empty file fails the command; a dry run reports
the file it would use. The file usually sits in the batch's directory beside `task.json`,
so git records what the agent was told along with the task.

The settings a campaign ran under are recorded twice: per batch in its `task.json`, and per
campaign in the history of `crustify/CRUSTIFY.md`.

## 3. Review batches

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
The optional `instructions` is the only other root field accepted.

The reviewer's prompt offers `unsafety`, `contracts`, `ub`, `equiv`, `internal`,
`conventions`, `misc`, `coverage`, `revisit`, `disclose` and `fix`, with `conventions`
applying to a Crustify-generated batch only. Its skills add their own. A batch naming
an objective the installed skills do not offer is rejected.
Without `fix`, the reviewer reports and reproduces what it finds but patches nothing.

## 4. Planner tasks

A planner task says only how a planner run runs. What it plans is the branch it is spawned
on, forked from the campaign branch: every run emits what the committed plan lacks, updates what follows an earlier
schema, corrects what earlier runs decided, and re-emits the schedules its changes move.

```json
{"model": "anthropic/claude-opus-5-5", "billing": "subscription"}
```

| root field | meaning |
|---|---|
| `model`, `billing` | the [run fields](#1-run-fields) |
| `instructions` | optional [additional instructions](#2-additional-instructions) |

Both run fields are required, and `instructions` is the only other root field accepted. It is written as
`task.json` in the run's artifact dir, `crustify/artifacts/planning/run-<k>/`.

## 5. items[*]

Every field is required on every item, and no other field is accepted.

| field | meaning |
|---|---|
| `name` | C entity name, non-empty |
| `defined_in` | repo-relative path of its definition |
| `kind` | `type`, `symbol` or `callback` |
| `field_anchors` | C field identifiers assigned to this item; empty unless `kind` is `type` |
| `home` | repo-relative `.rs` path the item is authored into |

`(name, defined_in)` identifies an item and must be unique within the batch.
`field_anchors` must not repeat a name.

`home` is the sole placement input. A translator resolves no repo-tier artifact to decide
where an item goes, so the tree the batch names must still exist when its agent starts: do
not restructure `rust/` during a wave.

## 6. Routes

`kind` selects the agent route, and every item in a batch must select the same one. A
batch mixing routes is rejected.

| kind | route |
|---|---|
| `type` | `type` |
| `symbol`, `callback` | `symbol` |

A batch of the foundational `void` or `string` subsystem routes like any other. Its batch
id names the subsystem, and its binder binds the items with a lifecycle role as
strategies (`docs/binding.md`, Lifecycle strategies).
