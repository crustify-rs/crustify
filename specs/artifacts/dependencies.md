# dependencies.json schema

Field meaning for `<workdir>/crustify/artifacts/dependencies.json`, the out-of-tree
libraries the campaign's target uses. Layout example:
[`templates/dependencies.json`](../../templates/dependencies.json).

Planning emits it beside `modules.json`, whose dependency records name each library and
count what each module consumes from it; this artifact records what holds for the
library as a whole, once. How a campaign reaches these libraries is
[`specs/dependencies.md`](../dependencies.md).

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
| `wrapper` | `repository`, the wrapper's `crustify-rs/<name>-bindings`, and `pin`, the commit of its working branch the campaign's workspace pins, or `null` until it pins one |
| `rust_equivalent` | what Rust already provides for it: `ported` and `bindings`, below |

The assessment fields, `resolved`, `source` and `rust_equivalent`, are the plan's; the
`wrapper.pin` is progress, which moves as the side campaign advances.

## 2. libraries[*].rust_equivalent

`ported` lists the crates that reimplement the library in Rust, and `bindings` the crates
that put a safe Rust API over the C library itself. Each is in descending order of feature
parity, and empty when no such crate exists. They inform whether a crate is adopted in
place of the wrapper, which the user decides, as `specs/dependencies.md` describes.

| `ported[*]` and `bindings[*]` field | meaning |
|---|---|
| `crate` | the crate's name on crates.io |
| `sys` | `bindings` only: the raw `-sys` crate it builds on, or `null` when it binds the library itself |
| `feature_parity` | `full` when it provides every entity the campaign consumes from the library, with the same behaviour; `partial` otherwise |
| `license` | its SPDX license expression |
| `notes` | for `partial`, what it lacks or how it differs; empty for `full` |

A crate that wraps the library but exposes raw pointers or `unsafe` to its users is not
safe bindings; a `-sys` crate alone is listed as no binding.
