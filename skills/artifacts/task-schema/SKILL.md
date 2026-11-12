---
name: task-schema
description: "The fields of a run's task.json: run fields, batch fields, routes and items. Read before writing or reading a task.json."
---

# task.json schema

Field meaning for `task.json`, the one input of a run, in its run dir: of a `wrap` batch,
a `port` batch or a later stage's, a review batch, or a planner run. One task is one run's
entire worklist and how it runs.

A translation batch's task is one batch entry of `schedule-schema`,
packed from its wave's items when the wave starts. When the batch launches, that entry is
written as `task.json`: its `kind` as `objective`, its `items`, the
[batch fields](#2-batch-fields) that place it in the schedule, and the
[run fields](#1-run-fields).

`task.json` sits in its run's dir, as [`layout`](../../operations/layout/SKILL.md)'s Artifact dirs section spells it.
Its `session_id` is recorded in it as soon as the run's session has one, which ties the run
to its transcript and its records in crustify's home; a task that already holds one is not
run again. A batch that is run again gets a new run dir and task, so every attempt keeps
its own.

```json
{
  "objective": "wrap",
  "wave": 0,
  "batch": 0,
  "link_unit": "libavutil",
  "module": "libavutil/frame.c",
  "foundational": false,
  "base_branch": "crustify/waves/wave-0",
  "backend": "claude",
  "billing": "subscription",
  "revisions": {"crustify": "<sha>", "wavefront": "<sha>", "ffimap": "<sha>", "ffibox": "<sha>"},
  "items": [
    {
      "name": "AVFrame",
      "defined_in": "libavutil/frame.h",
      "kind": "struct",
      "field_users": ["data", "linesize"],
      "typedefs": [],
      "home": "src/libavutil/libavutil/frame.rs"
    }
  ]
}
```

| root field | meaning |
|---|---|
| `objective` | execution objective for every item: `wrap` or `port`, or a later stage of a port campaign, `port/layout`, `port/memory` or `port/unexport`, as `scheduling`'s Later stages section describes |
| `items` | non-empty worklist; every item selects the same route |
| `wave`, `batch`, `link_unit`, `module`, `foundational` | the [batch fields](#2-batch-fields) |
| `base_branch`, `backend`, `billing`, `model_proxy`, `session_id`, `args`, `revisions` | the [run fields](#1-run-fields) |

All but `model_proxy`, `session_id` and `args` are required, and no other root
field is accepted. `session_id` is absent until the run starts.

## 1. Run fields

| field | meaning |
|---|---|
| `base_branch` | the unchecked-out integration branch the agent lands on: its wave branch, or in an audit its review wave branch; a `refs/heads/` prefix is accepted |
| `backend` | the provider CLI the agent runs on: `claude`, Claude Code, or `codex` |
| `billing` | how the provider CLI authenticates: `subscription`, its own logged-in account, or `api`, an API key from the environment |
| `model_proxy` | optional: the gateway the CLI's requests go through, with its own key, such as `openrouter`; it needs `api` billing, and its rates price the run |
| `session_id` | the session the run became, recorded once it starts, never before |
| `revisions` | the commits of Crustify and of each tool the run uses, by name, such as `{"crustify": "<sha>", "wavefront": "<sha>"}`, recorded as it launches, from the checkouts it reads and runs |
| `args` | optional: arguments passed to the provider CLI unchanged, after Crustify's own, in the CLI's own syntax, such as `["--model", "opus", "--effort", "high"]` |

Without `args` naming one, the CLI runs its own default model; Codex through a model proxy
needs its model named, as the proxy knows it. A batch's task carries `base_branch`,
`backend` and `billing`. A planner task carries `backend` and `billing` only: a planner
run commits on the planner branch it is spawned on, which is then promoted to the working
branch, `crustify/devel`.

## 2. Batch fields

| field | meaning |
|---|---|
| `wave` | the `index` of the batch's wave in `schedule.json` |
| `batch` | the batch's `index` within that wave |
| `link_unit` | its wave's `link_unit`; `null` in an audit, which has no decomposition |
| `module` | its wave's `module`, the module's `name`; `null` in an audit |
| `foundational` | its wave's `foundational` |

`wave` and `batch` form the batch id, `wave-<wave>/batch-<batch>`, which names the batch's
branch, worktree and reviews dir as `versioning` and `layout` spell them, and leads from the run
back to the batch's entry in `schedule.json`. A batch's task carries all five; a planner
task carries none.

## 3. Task message

An agent's task message names what its Inputs section lists, its `task.json` among them,
and the instructions its run needs beyond its role, if any, which take precedence over
the rest of its prompt where the two conflict. It is kept in the run's artifact dir, as
`task.md` beside `task.json`, so that git records what the agent was told along with the
task.

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
  "module": "libavutil/frame.c",
  "foundational": false,
  "base_branch": "crustify/waves/wave-1",
  "backend": "claude",
  "billing": "subscription",
  "revisions": {"crustify": "<sha>", "wavefront": "<sha>", "ffimap": "<sha>", "ffibox": "<sha>"}
}
```

```json
{
  "objectives": ["ub", "contracts", "disclose"],
  "paths": ["src/frame.rs", {"path": "src/codec.rs", "types": ["Decoder"], "trait_impls": ["Drop for Decoder"], "functions": ["open_input"]}]
}
```

```json
{"objectives": ["revisit", "disclose", "fix"], "reports": ["crustify/reviews/<module dir>/<batch id>/ub_safe/<slug>"]}
```

| root field | meaning |
|---|---|
| `objectives` | the review objectives to run; optional, every one that applies when absent |
| `commits` | distinct commit ids, as they sit on its wave's branch; route `commits`: the `commits` of the batches its schedule entry `reviews`, whose `items` there list the C items they bound or ported |
| `paths` | repo-relative source files and directories; route `paths`. An entry may instead be `{"path", "types", "trait_impls", "functions"}`, naming the parts of a module too large to review whole: types, each with its fields and inherent impls; trait impls, each `<trait> for <type>` as its impl header spells it; and free functions |
| `reports` | repo-relative report dirs, `<reviews dir>/<kind>/<slug>`, to revisit |
| `wave_gates` | optional, `false` when absent: `true` on the wave's last review batch, launched once every translation batch of the wave has landed, which runs the wave's gates, as `reviewing`'s Gates section describes; only on a batch with `commits`, or on a module pass |
| `module_pass` | optional, `false` when absent: `true` on a module pass, whose `paths` are its module's Rust file and its test files in each suite, and which carries `wave_gates` |

The batch and run fields are required, as on a translation task; the second and third
examples leave them out. An audit's batch has a `null` `link_unit` and `module`, and a `false`
`foundational`.
A batch carries `commits` or `paths`, not both, and needs one of them or `reports`; one
with only `reports` has route `reports`. A module path appears once, and a module object
names one or more of `types`, `trait_impls` and `functions`, each a distinct list. `reports` is given exactly when `revisit` is among the
objectives, and an absent `objectives` includes `revisit` exactly when `reports` is given.
The optional `wave_gates` and `module_pass` are the only other root fields accepted.

The objectives are those `reviewing`'s Objectives section describes and those the
installed tools' skills add, such as wavefront's `lifecycle`. A batch naming an objective
neither offers is rejected.

## 5. Planner tasks

A planner task says only how a planner run runs. What it plans is the branch it is spawned
on, forked from the working branch: every run emits what the committed plan lacks, updates what follows an earlier
schema, corrects what earlier runs decided, and re-plans the waves its changes move.

```json
{"backend": "claude", "billing": "subscription", "revisions": {"crustify": "<sha>", "wavefront": "<sha>"}}
```

| root field | meaning |
|---|---|
| `backend`, `billing`, `model_proxy`, `session_id`, `args`, `revisions` | the [run fields](#1-run-fields) |

`backend`, `billing` and `revisions` are required, and no other root field is accepted. It is written as
`task.json` in the run's artifact dir, `crustify/artifacts/planner/run-<n>/`.

## 6. items[*]

Every field is required on every item, and no other field is accepted.

| field | meaning |
|---|---|
| `name` | C entity name, non-empty: a function pointer written inline is named by its signature |
| `defined_in` | path of its definition below the C root |
| `kind` | what the C entity is: `struct`, `union`, `enum`, `function`, `global`, `macro`, `function_pointer`, declared by a typedef or written inline, or `typedef`, one that names no struct, union, enum or function pointer |
| `field_users` | the members of a struct, a union or an enum its consumers use: a struct's or a union's fields, whose accessors the batch writes, or an enum's constants; empty on any other kind |
| `typedefs` | the typedefs that name a struct, a union, an enum or a function pointer besides its `name`, which the batch binds with it; empty on any other kind |
| `home` | `.rs` path, relative to the repository's root, the item is authored into |

`(name, defined_in)` identifies an item and must be unique within the batch. A
`port/layout` batch holds only structs, unions and enums, a `port/memory` batch only
structs and unions, and a `port/unexport` batch only functions, globals and function
pointers.
`field_users` and `typedefs` must not repeat a name.

`home` is the sole placement input: no other artifact decides where an item goes, so the
Rust tree a wave's batches name is not restructured while the wave runs.

## 7. Routes

`kind` selects the agent route, and every item in a batch must select the same one. A
batch mixing routes is rejected.

| kind | route |
|---|---|
| `struct`, `union`, `enum`, `typedef`, and a `macro` that generates types | `type` |
| `function`, `global`, `function_pointer`, and any other `macro` | `symbol` |

A macro generates types when its record in the planning tools lists the instance types it
mints: its instances share the one generic the type route writes for it, as
[`binding-symbols`](../../rust/binding/symbols/SKILL.md)'s Macros section describes.

A batch of a foundational module routes like any other. Its `module` and `foundational`
name the module, which `modules.json` marks `foundational`, and its items with a lifecycle
role are bound as strategies (`binding-symbols`, Lifecycle strategies).
