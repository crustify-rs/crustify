---
name: dependencies
description: "How a campaign reaches libraries from outside its tree: wrappers, side campaigns, sources, reuse, adopted crates. Read before planning or advancing an out-of-tree library's wrapper."
---

# Dependencies

How a campaign reaches the libraries its target uses from outside its tree: libc, zlib,
OpenSSL and the like. The [decomposition](../decomposition/SKILL.md) records each one a module
uses as a dependency record, counting the entities the module consumes from it, and
`dependencies.json` records each library once: the release the target links, its source,
its wrapper and the Rust crates that port or bind it, as
[`dependencies-schema`](../../artifacts/dependencies-schema/SKILL.md) describes. This spec describes
what the campaign does with them.

## 1. Wrappers

An out-of-tree library a campaign uses is reached through a Crustify wrapper of its own,
or through an existing crate the user adopts for it, as [Adopted crates](#6-adopted-crates)
describes. The choice is made per library once the plan is complete: the plan's `ported`
and `bindings` records of `dependencies.json`, each with its feature parity and the notes
that argue it, are put to the user, who chooses, and the choice is recorded as the
library's `decision`. The records inform the choice; they do not make it.

What a library provides that the Rust standard library provides too is reached through
the standard library wherever no state is shared with C, as
[Standard-library equivalents](#2-standard-library-equivalents) describes.

A library's wrapper is a wrap campaign of the source it is built from, in a repository of
its own: `<source>-crustify` under the `crustify-rs` organization, `<source>` being the
name of that source's repository, named and laid out as
[`versioning`](../../operations/versioning/SKILL.md)'s Repositories section and [`layout`](../../operations/layout/SKILL.md)'s
Tree section describe for any wrap campaign, so that a later campaign whose target is the
source itself continues it. The libraries one source builds share its wrapper, each a link
unit of it: OpenSSL's `libcrypto` and `libssl` are both wrapped in `openssl-crustify`.
It is cloned beside the campaign's repository, as `../<source>-crustify`, never inside
it. The campaign's workspace depends on its crate by
Git, pinned to a commit, with a Cargo `[patch]` pointing at the clone while the campaign
extends it; the parent campaign's safe crate, its raw bindings included, names its safe
wrappers, never its raw bindings once a safe wrapper exists.

A wrapper covers only what the campaigns that use it reach through it: the entities
their waves need through the wrapper rather than the standard library, wrapped as those
waves need them. It exposes its own safe
types, with no conversions to or from the types of other crates that wrap the same
library.

## 2. Standard-library equivalents

The campaign's Rust reaches an out-of-tree library's entity through the Rust standard
library wherever the state the entity works on stays in Rust, or crosses to C only as
values the boundary converts, and through the library's wrapper wherever that state is
shared with C, as [`binding`](../../rust/binding/SKILL.md)'s Safe boundary
section describes. The agent doing the work judges which; no plan records it, so a
wrapper covers what the campaign's Rust reaches through it as its waves need it.

## 3. Side campaigns

A wrapper's work is a side campaign, continued in its own repository: it keeps its own
settings, plan, schedule, branches, builds and accounting there, and its batches land on
its own wave branches, as any wrap campaign's do. Its scope is what the parent campaign
reaches through the wrapper, not the whole library, and it grows as the parent's waves
need more of it. Its settings are the parent's, but for its `campaign`, which is `wrap`, its
`source`, the library at the release the target links, and its `scope`; a settings change
the parent applies is applied to its side campaigns too.

The side campaign advances at the parent's pace. Before a parent wave starts, the
entities its items need through each library's wrapper are judged from the items, the
libraries their modules' `depends_on.external` records name and the entities they use:
every entity of a library the standard library does not replace, and of the others those
whose state the items share with the remaining C, as
[Standard-library equivalents](#2-standard-library-equivalents) describes. What the
wrapper lacks of them, the side campaign plans and runs waves to wrap; once those are
promoted to its working branch, the parent's pin, its library's `wrapper.pin` in
`dependencies.json`, moves to that commit, and the parent wave starts. A batch that needs
an entity through a wrapper that lacks it reports it rather than reaching it through raw
bindings, and runs again once the side campaign has wrapped it. The parent ships
only once each wrapper it pins has shipped the commit it pins, each with the user's
approval.

Each wrapper's crate bundles its own raw bindings, generated from the library's headers,
as [`bindgen`](../../rust/bindgen/SKILL.md) describes. While its `c/` is the whole
library, the crate builds by default in system mode, linking the system's copy, as the
other crates of a dependent's build that wrap the same library do, so that a process holds
one copy of it; its version check accepts any release ABI-compatible with the one its
bindings were generated from, which shares its soname. Once its side campaign has ported
part of the library, the crate bundles the C that remains, with its symbols prefixed, so
that it never collides with another copy of the library in the same process, and passes
the prefix to the C builds of the campaigns that depend on it, as the raw bindings'
Generation section describes.

## 4. Sources

A library the target links from the system has no
source of the campaign's own, so its side campaign's `c/` is the library's upstream
repository at the release the target was built against: the version its build resolved,
as its build system reports it (CMake's found version, `pkg-config --modversion`), the
system package that provides it, or, for a library built from source, its own version
header. The distribution's patches to that release, if any, are recorded beside it, in the
library's `resolved` and `source` in `dependencies.json`.

The side campaign builds and installs the library locally, once per build variant of its
parent, under its own `crustify/builds/<variant>/install`, so that each variant of the
target links the library built with the same instrumentation; a sanitizer that instruments
every component, MSan among them, needs it. The parent's variants are then rebuilt against
those installs, as the setup workflow's Builds section describes.

libc is the exception. Every other library on the system, and the dynamic loader, depend
on the system's glibc, so the target keeps linking it, and its side campaign's `c/` holds
glibc's source at the installed version, for reading its behaviour. Its raw bindings, like
any wrapper's, are generated from the host's headers, which are that glibc's, so layouts and
constants that differ between architectures, such as `struct stat`, are the campaign
target's.

## 5. Reuse

Before a campaign creates a library's wrapper, it checks `crustify-rs` for
`<source>-crustify`. One that exists is cloned and its side campaign continued: what it
already wraps is not scheduled again, and only what it lacks is planned, as additions to
its own plan. A library without one gets a new repository, created once the user approves,
which every later campaign that uses the library continues.

## 6. Adopted crates

When the user adopts a crate for a library, such as one of its `ported` or `bindings`
records, the library gets no wrapper and no batches: its consumers use the crate directly,
and their bindings name its types and functions where they would name the wrapper's.
