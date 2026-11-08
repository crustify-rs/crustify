# Dependencies

How a campaign reaches the libraries its target uses from outside its tree: libc, zlib,
OpenSSL and the like. The [decomposition](decomposition.md) records each one a module
uses as a dependency record, counting the entities the module consumes from it, and
`dependencies.json` records each library once: the release the target links, its source,
its wrapper and the Rust crates that port or bind it, as
[`../artifacts/dependencies.md`](../artifacts/dependencies.md) describes. This spec describes
what the campaign does with them.

## 1. Wrappers

An out-of-tree library a campaign uses is reached through a Crustify wrapper of its own,
or through an existing crate the user adopts for it, as [Adopted crates](#6-adopted-crates)
describes. The choice is made per library once the plan is complete: the plan's `ported`
and `bindings` records of `dependencies.json`, each with its feature parity and the notes
that argue it, are put to the user, who chooses, and the choice is recorded as the
library's `decision`. The records inform the choice; they do not make it.

What a library provides that the Rust standard library provides too is not wrapped, as
[Standard-library equivalents](#2-standard-library-equivalents) describes: a wrapper covers
the rest.

A library's wrapper is a wrap campaign of the source it is built from, in a repository of
its own: `<source>-crustify` under the `crustify-rs` organization, `<source>` being the
name of that source's repository, named and laid out as
[`../operations/versioning.md`](../operations/versioning.md)'s Repositories section and [`../operations/layout.md`](../operations/layout.md)'s
Tree section describe for any wrap campaign, so that a later campaign whose target is the
source itself continues it. The libraries one source builds share its wrapper, each a link
unit of it: OpenSSL's `libcrypto` and `libssl` are both wrapped in `openssl-crustify`.
It is cloned beside the campaign's repository, as `../<source>-crustify`, never inside
it. The campaign's workspace depends on its crate by
Git, pinned to a commit, with a Cargo `[patch]` pointing at the clone while the campaign
extends it; the parent campaign's safe crate, its raw bindings included, names its safe
wrappers, never its raw bindings once a safe wrapper exists.

A wrapper covers only what the campaigns that use it consume: the entities their
dependency records count, wrapped as their consumers need them. It exposes its own safe
types, with no conversions to or from the types of other crates that wrap the same
library.

## 2. Standard-library equivalents

An entity of an out-of-tree library that the Rust standard library provides with full
feature parity, such as libc's `memcpy`, `strlen` and `stat` or libm's `pow`, is reached
through the standard library in the campaign's Rust, not through the library's wrapper.
Each such entity's equivalent is recorded in its library's `rust_equivalent.std` in
`dependencies.json`, with what differs in its behaviour, such as `O_CLOEXEC` on the files
`std::fs` opens or the locale `u8::is_ascii_alphabetic` ignores.

The standard library serves only where no remaining C shares the value or the state the
entity works on. While remaining C does, the entity is reached through the wrapper:

- memory the C frees or reallocates;
- a lock embedded in a type whose C layout the remaining C uses, which it locks too;
- `errno`, when remaining C reads it after the call;
- a handle the C uses, such as a `FILE *` or a `DIR *`; and
- a type whose layout the remaining C reads, such as `struct stat` or `struct timespec`.

Once the last remaining C that shares it has been integrated, the module that reaches the
entity through the wrapper switches to the standard library, in one wave of its own
scheduled after that integration, as a type's deferred port is, in
[scheduling](scheduling.md)'s Porting types section.

## 3. Side campaigns

A wrapper's work is a side campaign, continued in its own repository: it keeps its own
settings, plan, schedule, branches, builds and accounting there, and its batches land on
its own wave branches, as any wrap campaign's do. Its scope is what the parent campaign
consumes from the library, not the whole library, and it grows as the parent's waves need
more of it. Its settings are the parent's, but for its `campaign`, which is `wrap`, its
`source`, the library at the release the target links, and its `scope`; a settings change
the parent applies is applied to its side campaigns too.

The side campaign advances at the parent's pace. Before a parent wave whose items use
entities of the library that the wrapper lacks, as [scheduling](scheduling.md)'s Wrap
batches section places it, the side campaign plans and runs the waves that wrap them; once
those are promoted to its working branch, the parent's pin, its library's `wrapper.pin`
in `dependencies.json`, moves to that commit, and the parent wave starts. The parent ships
only once each wrapper it pins has shipped the commit it pins, each with the user's
approval.

Each wrapper's crate bundles its own raw bindings, generated from the library's headers,
as [`../rust/bindgen.md`](../rust/bindgen.md) describes. While its `c/` is the whole
library, the crate builds by default in system mode, linking the system's copy, as the
other crates of a dependent's build that wrap the same library do, so that a process holds
one copy of it; its version check accepts any release ABI-compatible with the one its
bindings were generated from, which shares its soname. Once its side campaign has ported
part of the library, the crate bundles the C that remains, with its symbols prefixed, so
that it never collides with another copy of the library in the same process, and passes
the prefix to the C builds of the campaigns that depend on it, as the raw bindings'
Generation section describes.

## 4. Sources

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
