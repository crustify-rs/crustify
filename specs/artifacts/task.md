# task.json schema

Field meaning for `task.json`, the one input of a spawned agent: `crustify spawn-binder
<workdir> <run dir>/task.json --log-dir <run dir>` for a `wrap` batch, `crustify
spawn-translator` with the same arguments for a `port` batch, `crustify spawn-reviewer`
for a review batch, and `crustify spawn-planner <workdir> <run dir>/task.json --log-dir
<run dir>` for a planner run. The path names the file itself; a missing file fails the
command. One task is one
agent's entire worklist and how that agent runs, and each command rejects a task whose
objective belongs to another.

A planner plans a binder's or translator's task as one batch entry of
`specs/artifacts/schedule.md`. When the batch launches, that entry is written as
`task.json`: its `kind` as `objective`, its `items`, the [batch fields](#2-batch-fields)
that place it in the schedule, and the [run fields](#1-run-fields).

`task.json` sits in the artifact dir of the agent's run, `crustify/artifacts/<role>/run-<n>/`,
which is also passed as `--log-dir`. The agent writes its log and usage record there, so
the directory holds everything about the run: what it was given, how it ran, and what it
produced. A batch that is run again gets a new run dir, so every attempt keeps its own.

```json
{
  "objective": "wrap",
  "wave": 0,
  "batch": 0,
  "link_unit": "libavutil",
  "module": 4,
  "base_branch": "crustify/waves/wave-0",
  "model": "anthropic/claude-opus-5-5",
  "billing": "subscription",
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "type",
      "field_anchors": ["data", "linesize"],
      "home": "src/libavutil/libavutil/frame.rs"
    }
  ]
}
```

| root field | meaning |
|---|---|
| `objective` | execution objective for every item: `wrap` or `port` |
| `items` | non-empty worklist; every item routes to the same agent |
| `wave`, `batch`, `link_unit`, `module` | the [batch fields](#2-batch-fields) |
| `base_branch`, `model`, `billing` | the [run fields](#1-run-fields) |
| `instructions` | optional [additional instructions](#3-additional-instructions) |

All nine are required, and `instructions` is the only other root field accepted.

## 1. Run fields

| field | meaning |
|---|---|
| `base_branch` | the unchecked-out integration branch the agent lands on: its wave branch, or its review wave branch; a `refs/heads/` prefix is accepted |
| `model` | the agent's model, `<provider>/<model>`, such as `anthropic/claude-opus-5-5`; an unknown provider is rejected |
| `billing` | how the provider CLI authenticates: `subscription`, its own logged-in account, or `api`, an API key from the environment |

A binder, translator or reviewer task carries all three. A planner task carries `model`
and `billing` only: a planner commits on the planner branch it is spawned on, which is
then promoted to the working branch, `crustify/devel`.

## 2. Batch fields

| field | meaning |
|---|---|
| `wave` | the `index` of the batch's wave in `schedule.json` |
| `batch` | the batch's `index` within that wave |
| `link_unit` | its wave's `link_unit`; `null` when the campaign has no decomposition |
| `module` | its wave's `module`; `null` when the wave belongs to no module |

`wave` and `batch` form the batch id, `wave-<wave>/batch-<batch>`, which names the batch's
branch, worktree and reviews dir as `specs/versioning.md` and `specs/layout.md` spell them, and leads from the run
back to the batch's entry in `schedule.json`. A binder, translator or reviewer task
carries all four; a planner task carries none.

## 3. Additional instructions

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

## 4. Review batches

A review batch carries, instead of `objective`, an optional `objectives` array, and a Rust
worklist instead of `items`: in a translate campaign, the commits its translation batches
landed; in an audit, modules of the crate.

```json
{
  "objectives": ["lifecycle", "unsafety", "ub", "equiv", "fix"],
  "commits": ["3f2a9c1", "8be04d7"],
  "wave": 1,
  "batch": 0,
  "link_unit": "libavutil",
  "module": 4,
  "base_branch": "crustify/waves/wave-1",
  "model": "anthropic/claude-opus-5-5",
  "billing": "subscription"
}
```

```json
{
  "objectives": ["ub", "contracts", "disclose"],
  "paths": ["src/frame.rs", {"path": "src/codec.rs", "types": ["Decoder"], "trait_impls": ["Drop for Decoder"], "functions": ["open_input"]}]
}
```

| root field | meaning |
|---|---|
| `objectives` | the review objectives to run; optional, every one the reviewer offers that applies when absent |
| `commits` | distinct commit ids, as they sit on the reviewed wave's branch; route `commits`: the `commits` of the batches its schedule entry `reviews`, whose `items` there list the C items they bound or ported |
| `paths` | repo-relative source files and directories; route `paths`. An entry may instead be `{"path", "types", "trait_impls", "functions"}`, naming the parts of a module too large to review whole: types, each with its fields and inherent impls; trait impls, each `<trait> for <type>` as its impl header spells it; and free functions |
| `reports` | repo-relative report dirs, `crustify/reviews/<batch id>/<kind>/<slug>`, to revisit |

The batch and run fields are required, as on a translation task; the second example
leaves them out. An audit's batch has a `null` `link_unit` and `module`.
A batch carries `commits` or `paths`, not both, and needs one of them or `reports`; one
with only `reports` has route `reports`. A module path appears once, and a module object
names one or more of `types`, `trait_impls` and `functions`, each a distinct list. `reports` is given exactly when `revisit` is among the
objectives, and an absent `objectives` includes `revisit` exactly when `reports` is given.
The optional `instructions` is the only other root field accepted.

The reviewer's prompt offers `unsafety`, `contracts`, `ub`, `equiv`, `internal`,
`conventions`, `misc`, `coverage`, `revisit`, `disclose` and `fix`, with `conventions`
applying to a Crustify-generated batch only. Its skills add their own. A batch naming
an objective the installed skills do not offer is rejected.
Without `fix`, the reviewer reports and reproduces what it finds but patches nothing.

## 5. Planner tasks

A planner task says only how a planner run runs. What it plans is the branch it is spawned
on, forked from the working branch: every run emits what the committed plan lacks, updates what follows an earlier
schema, corrects what earlier runs decided, and re-plans the waves its changes move.

```json
{"model": "anthropic/claude-opus-5-5", "billing": "subscription"}
```

| root field | meaning |
|---|---|
| `model`, `billing` | the [run fields](#1-run-fields) |
| `instructions` | optional [additional instructions](#3-additional-instructions) |

Both run fields are required, and `instructions` is the only other root field accepted. It is written as
`task.json` in the run's artifact dir, `crustify/artifacts/planner/run-<n>/`.

## 6. items[*]

Every field is required on every item, and no other field is accepted.

| field | meaning |
|---|---|
| `name` | C entity name, non-empty |
| `defined_in` | path of its definition below the C root |
| `kind` | `type`, `symbol` or `callback` |
| `field_anchors` | C field identifiers assigned to this item; empty unless `kind` is `type` |
| `home` | `.rs` path, relative to the repository's root, the item is authored into |

`(name, defined_in)` identifies an item and must be unique within the batch.
`field_anchors` must not repeat a name.

`home` is the sole placement input. A translator resolves no repo-tier artifact to decide
where an item goes, so the tree the batch names must still exist when its agent starts: do
not restructure `rust/` during a wave.

## 7. Routes

`kind` selects the agent route, and every item in a batch must select the same one. A
batch mixing routes is rejected.

| kind | route |
|---|---|
| `type` | `type` |
| `symbol`, `callback` | `symbol` |

A batch of a foundational module routes like any other. Its `module` is the module's index,
which `modules.json` marks `foundational`, and its binder binds the items with a
lifecycle role as
strategies (`specs/items/binding.md`, Lifecycle strategies).
