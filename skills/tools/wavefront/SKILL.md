---
name: wavefront
description: "wavefront, which answers deterministic queries about the C codebase and orders it by dependency, and where its documentation covers each use. Read before querying the C codebase, choosing the order to port components in, or judging a pointer's ownership or a type's lifecycle."
---

# wavefront

wavefront extracts facts about a C codebase with CodeQL: its entities, their uses and
dependencies, their pointers and lifecycles. It answers queries over them and orders the
codebase so that every item comes after what it needs. Start from its `README.md`, which
covers installing CodeQL and building its database, and its `--help`, then read the
document for the use at hand:

| use | document |
|---|---|
| what wavefront analyzes and where the order starts, in its config | `docs/scoping.md` |
| the dependency graph and how it orders the codebase | `docs/graph.md` |
| a dependency order of components, with `wavefront schedule` | `docs/batching.md`, `docs/artifacts/schedule.md` |
| a pointer's extent, nullness and who releases it | `docs/pointer-properties.md` |
| a type's lifecycle: what creates, copies and releases it | `docs/type-lifecycle.md` |
| the fields of its records: types, symbols, findings, the ownership store, casts | `docs/artifacts/` |
| what wavefront is for | `docs/goals.md` |

Keep its state and scratch under `.crustify/`, as [`layout`](../../operations/layout/SKILL.md)
places the port's own files.
