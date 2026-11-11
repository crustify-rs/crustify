---
name: dependencies-schema
description: "The fields of dependencies.json. Read before writing or reading dependencies.json."
---

# dependencies.json schema

Field meaning for `<workdir>/crustify/artifacts/dependencies.json`, the out-of-tree
libraries the campaign's target uses. Layout example:
[`templates/dependencies.json`](../../../templates/dependencies.json).

Planning emits it beside `modules.json`, whose dependency records name each library and
count what each module consumes from it; this artifact records what holds for the
library as a whole, once. How a campaign reaches these libraries is
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
| `recommendation` | the plan's route for what the campaign uses of the library, shaped as `decision` |
| `decision` | how the campaign reaches the library, as the user chose it once the plan was complete, below; `null` until the user decides |
| `wrapper` | `repository`, the wrapper's `crustify-rs/<source>-crustify`, shared by the libraries one source builds, and `pin`, the commit of its working branch the campaign's workspace pins, or `null` until it pins one; `null` for an adopted crate |
| `rust_equivalent` | what Rust already provides for it: `ported` and `bindings`, below |

The assessment fields, `resolved`, `source`, `rust_equivalent` and `recommendation`, are
the plan's; the `decision` is the user's, and the `wrapper.pin` and each fork's `pin` are
progress, which move as the side campaign and the forks advance.

### 1.1 decision and recommendation

| field | meaning |
|---|---|
| `adopt` | the crates adopted, each `crate`, its `areas`, the parts of the library it covers, and `fork`: `null`, or `repository`, `branch` and `pin` of the fork that extends it |
| `remainder` | what no adopted crate covers: `wrapper` for the library's wrapper, `local` for local bindings over the `-sys` crate `remainder_sys` names, or `null` when the adopted crates cover everything |
| `remainder_sys` | for `local`, the established `-sys` crate the local bindings are made over, such as `libc`; `null` otherwise |

## 2. libraries[*].rust_equivalent

`ported` lists the crates that reimplement the library in Rust, and `bindings` the crates
that put a safe Rust API over the C library itself. Each is in descending order of feature
parity, and empty when no such crate exists. They inform whether a crate is adopted in
place of the wrapper, which the user decides, as `dependencies` describes.

| `ported[*]` and `bindings[*]` field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `sys` | `bindings` only: the raw `-sys` crate it builds on, or `null` when it binds the library itself |
| `feature_parity` | `full` when it provides every entity the campaign consumes from the library, with the same behaviour; `partial` otherwise |
| `license` | its SPDX license expression |
| `notes` | for `partial`, what it lacks or how it differs; empty for `full` |
| `version` | the version assessed |
| `areas` | the areas of the library it covers that the campaign uses |
| `shares_state` | whether it can share an area's state with the remaining C: `true` for one that exposes the C library's raw handles, `false` otherwise |
| `soundness` | `judgement`, `sound`, `unsound` or `unclear`, and `evidence`, what the read of its API and unsafe code found, with the scan it ran, if any |
| `advisories` | the unfixed advisories that affect the assessed version and the features the campaign uses, by id; empty when none does |
| `maintenance` | `last_release`, the date of its latest release, and `publisher`, the organization or the maintainers that publish it |
| `qualifies` | the areas it meets every criterion of `dependencies`' Adopted crates section for |

A crate that wraps the library but exposes raw pointers or `unsafe` to its users is not
safe bindings; a `-sys` crate alone is listed as no binding.
