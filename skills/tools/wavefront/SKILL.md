---
name: wavefront
description: "wavefront, which answers deterministic queries about the C codebase and orders it by dependency. Read before querying the C codebase, choosing the order to port components in, or judging a pointer's ownership or a type's lifecycle."
---

# wavefront

wavefront extracts facts about a C codebase with CodeQL: its entities, their uses and
dependencies, their pointers and lifecycles. It answers queries over them and orders the
codebase so that every item comes after what it needs. Read its `README.md`, which covers
installing CodeQL and building its database, its `--help`, and its `docs/` wherever you
need them. Keep its state under `.crustify/`.
