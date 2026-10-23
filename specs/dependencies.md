# Dependencies

How a campaign reaches the libraries its target uses from outside its tree: libc, zlib,
OpenSSL and the like. The [decomposition](decomposition.md) records each one a module
uses as a dependency record, counting the entities the module consumes from it, and
`dependencies.json` records each library once: the release the target links, its source,
its wrapper and the Rust crates that port or bind it, as
[`artifacts/dependencies.md`](artifacts/dependencies.md) describes. This spec describes
what the campaign does with them.

## 1. Wrappers

An out-of-tree library a campaign uses is reached through a Crustify wrapper of its own,
unless the user instructs the campaign to adopt an existing crate. The `ported` and
`bindings` records of `dependencies.json` inform that choice and the user's instructions; they
do not make it.

A library's wrapper is a wrap campaign of that library, in a repository of its own:
`<library>-bindings` under the `crustify-rs` organization, named and laid out as
[`versioning.md`](versioning.md)'s Repositories section and [`layout.md`](layout.md)'s
Tree section describe for any wrap campaign, so that a later campaign whose target is the
library itself continues it. It is cloned beside the campaign's repository, as
`../<library>-bindings`, never inside it. The campaign's workspace depends on its crate by
Git, pinned to a commit, with a Cargo `[patch]` pointing at the clone while the campaign
extends it; the safe crate and the `-sys` crates name its safe wrappers, never its raw
bindings once a safe wrapper exists.

A wrapper covers only what the campaigns that use it consume: the entities their
dependency records count, wrapped as their consumers need them.

## 2. Side campaigns

A wrapper's work is a side campaign, continued in its own repository: it keeps its own
settings, plan, schedule, branches, builds and accounting there, and its batches land on
its own wave branches, as any wrap campaign's do. Its scope is what the parent campaign
consumes from the library, not the whole library, and it grows as the parent's waves need
more of it. Its settings are the parent's, but for its `campaign`, which is `wrap`, its
`source`, the library at the release the target links, and its `scope`; a settings change
the parent applies is applied to its side campaigns too.

The side campaign advances at the parent's pace. Before a parent wave whose items use
entities of the library that the wrapper lacks, as [scheduling](scheduling.md)'s Wrap
waves section places it, the side campaign plans and runs the waves that wrap them; once
those are promoted to its working branch, the parent's pin, its library's `wrapper.pin`
in `dependencies.json`, moves to that commit, and the parent wave starts. The parent ships
only once each wrapper it pins has shipped the commit it pins, each with the user's
approval.

## 3. Sources

Campaigns run on Linux, with glibc, on 64-bit architectures. A library the target links from the system has no
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
any wrapper's, are generated from the host's headers, which are that glibc's; layouts and
constants that differ between 64-bit architectures, such as `struct stat`, are generated
for each architecture a campaign builds on, and verified there.

## 4. Reuse

Before a campaign creates a library's wrapper, it checks `crustify-rs` for
`<library>-bindings`. One that exists is cloned and its side campaign continued: what it
already wraps is not scheduled again, and only what it lacks is planned, as additions to
its own plan. A library without one gets a new repository, created once the user approves,
which every later campaign that uses the library continues.

## 5. Adopted crates

When the user instructs a campaign to adopt a crate for a library, such as one of its
`ported` or `bindings` records, the library gets no wrapper and no batches: its consumers
use the crate directly, and their bindings name its types and functions where they would
name the wrapper's.
