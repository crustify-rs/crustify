---
name: dependencies-schema
description: "The fields of dependencies.json. Read before writing or reading dependencies.json."
---

# dependencies.json schema

Field meaning for `<workdir>/crustify/artifacts/dependencies.json`, the out-of-tree
libraries the campaign's target uses. Layout example:
[`templates/dependencies.json`](../../../templates/dependencies.json).

Planning emits it beside `modules.json`, whose dependency records name each library and
count what each module consumes from it; this artifact records each library once, with
the crates assessed for it and every entity the campaign uses of it, mapped to what those
crates offer. How a campaign reaches these libraries is
[`dependencies`](../../planning/dependencies/SKILL.md).

| root field | meaning |
|---|---|
| `version` | the analyzed tree's revision, as `modules.json`'s |
| `libraries` | one entry per out-of-tree library a module of `modules.json` depends on |

## 1. libraries[*]

| field | meaning |
|---|---|
| `name` | the library as linked, such as `libz`; the dependency records' `library` |
| `resolved` | what the target's build found: `path`, the file it linked; `version`, the release, as the build system reports it or the library's version header gives it; and `package`, the system package that installed it, or `null` for a library built from source |
| `source` | the side campaign's `c/`: `repository`, the library's upstream repository, and `tag`, the release `resolved.version` names; and `patches`, the distribution patches to that release, named by the package that carries them, or `null` when there are none |
| `linked_from` | `side-campaign` when the target links the side campaign's per-variant install, `system` when it keeps linking the system's copy, as libc does |
| `candidates` | the crates assessed for it, below; empty when none was found |
| `c_entities` | every entity of the library the campaign uses, each mapped to what the candidates offer for it, below |
| `recommendation` | the plan's route for the library, shaped as `decision` |
| `decision` | how the campaign reaches the library, as the user chose it once the plan was complete, below; `null` until the user decides |
| `crustify_campaign` | the library's side campaign, the crustify campaign the `crustify-campaign` route reaches it through: `repository`, its `crustify-rs/<source>-crustify`, shared by the libraries one source builds, and `pin`, the commit of its working branch the campaign's workspace pins, or `null` until it pins one; `null` when no entity takes that route |

The assessment fields, `resolved`, `source`, `candidates`, `c_entities` but for each
entity's `confirmation`, and `recommendation`, are the plan's; the `decision` is the
user's; and the `crustify_campaign.pin`, each fork's `pin` and each entity's
`confirmation` are progress, which the assistant records as the side campaign, the forks
and the batches advance.

## 2. libraries[*].candidates

The crates that could serve some of what the campaign uses of the library, with the
standard library left out: it is never assessed, and appears only in `c_entities`.

| field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `version` | the version assessed |
| `license` | its SPDX license expression |
| `kind` | `ported` for a crate that reimplements the library in Rust, `bindings` for one that puts a safe Rust API over the C library itself |
| `sys` | for `bindings`, the raw `-sys` crate it builds on, or `null` when it binds the library itself; `null` for `ported` |
| `quality_assessment` | free text: the planner's reasoning on whether the crate is fit to adopt, by the criteria of `dependencies`' Adopted crates section, with what it read and ran, citing `file:line`, advisory ids and release dates |

A crate that wraps the library but exposes raw pointers or `unsafe` to its users is not
safe bindings; a `-sys` crate alone is no candidate, but may be a local route's
`uncovered_sys`.

## 3. libraries[*].c_entities

One record per entity of the library the campaign uses, from the external records of
`schedule.json`'s modules, which list each use: what the campaign needs, and what each
candidate offers for it.

| field | meaning |
|---|---|
| `c_name` | the C entity's name, as the library's header declares it |
| `kind` | its C kind: `function`, `global`, `macro`, `struct`, `union`, `enum`, `typedef` or `function_pointer` |
| `header` | the installed header that declares it, such as `zlib.h`, which groups the entities that belong together |
| `used_by` | the modules that use it, each `{link_unit, module, foundational}` as `schedule.json` names a module |
| `matches` | what each candidate, and the standard library as `std`, offers for it, below; empty when none offers anything |
| `recommended` | the plan's route for it: `route`, `std`, `crate`, `local` or `crustify-campaign`; for `std` and `crate`, `crate` (`std` for the standard library) and `rust_api`, the path of the Rust item that replaces it; `null` otherwise |
| `confirmation` | `null` until a batch first binds or ports one of its users; then that batch's check of its route against the code, below |

| `matches[*]` field | meaning |
|---|---|
| `crate` | the candidate's `crate`, or `std` |
| `rust_api` | the path of the Rust item closest to the entity, or `null` when the crate offers none |
| `match` | `exact` when it does what the entity does for every use the campaign makes of it; `differs` when it serves those uses with differences the note gives; `missing` when it offers nothing for it |
| `note` | for `differs`, how it differs and what that asks of its users; for `missing`, how the uses do without it, if they can; empty for `exact` |

| `confirmation` field | meaning |
|---|---|
| `batch` | the batch that checked it, as `wave-<index>/batch-<index>` |
| `route` | the route it took: `recommended`, as the decision gives it, or the route the batch switched it to |
| `crate`, `rust_api` | what it is reached through, as in `recommended` |
| `note` | why the batch switched it, or what its use showed that the match note missed; empty when it held as recorded |

## 4. decision and recommendation

| field | meaning |
|---|---|
| `adopt` | the crates adopted, each `crate`, a candidate's, and `fork`: `null`, or `repository`, `branch` and `pin` of the fork that extends it |
| `uncovered` | the route of the entities whose recommended crate is not adopted and that `std` does not serve: `crustify-campaign` for the library's crustify campaign, `local` for local bindings over the `-sys` crate `uncovered_sys` names, or `null` when nothing is left uncovered |
| `uncovered_sys` | for `local`, the established `-sys` crate the local bindings are made over, such as `libc`; `null` otherwise |
| `overrides` | `decision` only, optional: entities the user routes otherwise than their `recommended` route, each `c_name` and the `route`, `crate` and `rust_api` it takes |

An entity's route is its `recommended` route, unless `overrides` names it, or its
recommended crate is not adopted, which sends it to `uncovered`.
