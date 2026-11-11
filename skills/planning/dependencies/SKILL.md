---
name: dependencies
description: "How a campaign reaches libraries from outside its tree: the order of routes, adopted crates and their criteria, local bindings, wrappers, side campaigns, sources, reuse. Read before planning an out-of-tree library's route, or advancing its wrapper or a fork of an adopted crate."
---

# Dependencies

How a campaign reaches the libraries its target uses from outside its tree: libc, zlib,
OpenSSL and the like. The [decomposition](../decomposition/SKILL.md) records each one a module
uses as a dependency record, counting the entities the module consumes from it, and
`dependencies.json` records each library once: the release the target links, its source,
its crustify campaign, the Rust crates that port or bind it, and every entity the
campaign uses of it, mapped to what those crates offer, as
[`dependencies-schema`](../../artifacts/dependencies-schema/SKILL.md) describes. This spec describes
what the campaign does with them.

## 1. Routes

What a campaign uses of an out-of-tree library is reached, in this order of preference:

1. through the Rust standard library, wherever no state is shared with C, as
   [Standard-library equivalents](#2-standard-library-equivalents) describes;
2. through established crates adopted for parts of the library, extended in a fork where
   they lack a little, as [Adopted crates](#6-adopted-crates) describes;
3. bound locally, in the consuming module's own `ffi_import` region over the library's
   established `-sys` crate, such as `libc`, for what is left too small to be worth a
   wrapper, as [Local bindings](#7-local-bindings) describes; and
4. through the library's crustify campaign, a wrap campaign of its own whose crate is the
   library's Crustify wrapper, as the rest of this section and
   [Side campaigns](#3-side-campaigns) describe.

The routes are named `std`, `crate`, `local` and `crustify-campaign` in
`dependencies.json`. The plan records each library's candidate crates, each with its
quality assessment, and maps every entity the campaign uses of the library to what each
candidate and the standard library offer for it, recommending a route for each entity and,
from those, the crates to adopt and the route of what they leave uncovered. Once the plan is
complete, the recommendation is put to the user, who chooses per library, and the choice
is recorded as the library's `decision`, as
[`dependencies-schema`](../../artifacts/dependencies-schema/SKILL.md) describes. The
records inform the choice; they do not make it. Each entity's route is then checked against
the code by the first batch that needs it, as [Confirmation](#8-confirmation) describes.

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
section describes. The plan recommends which for each entity, from what it knows of the
uses; the batch that first needs the entity judges it from the code, as
[Confirmation](#8-confirmation) describes, so a wrapper covers what the campaign's Rust
reaches through it as its waves need it.

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
promoted to its working branch, the parent's pin, its library's `crustify_campaign.pin`
in `dependencies.json`, moves to that commit, and the parent wave starts. A batch that needs
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

A crate is adopted for a coherent part of what the campaign uses of a library, the
entities a subsystem, a header's API or a kind of resource (sockets, memory maps,
processes) groups, never for an item or two: entities that share state, such as a stream's
initializer, its operations and its finalizer, take the same crate. A library may be
covered by several crates, the fewest that cover what the campaign uses: libc's uses may
be the standard library's for files and threads, one crate's for sockets and another's for
the remaining system calls. What no adopted crate covers takes the next route.

Each entity's `matches` record what each candidate offers for it, and how closely; each
candidate's `quality_assessment` reasons, in prose, on the criteria below. A crate is fit to
adopt for the entities it matches when it meets every one:

- **coverage**: it provides what the campaign uses of those entities, with the same
  behaviour, or does once extended a little, as their `matches` show;
- **shared state**: where the remaining C shares an entity's state with the Rust, such as
  a handle the C still uses, the crate exposes that state to C, which the entity's match
  note says, citing the release point after which the C stops sharing it. A crate that binds the C
  library and exposes its raw handles can; one that reimplements the library qualifies
  only where no state crosses to the remaining C, as
  [Standard-library equivalents](#2-standard-library-equivalents) describes;
- **soundness**: a read of its public API and its unsafe code finds no undefined
  behaviour reachable from its safe API, by the hazards
  [`binding`](../../rust/binding/SKILL.md)'s Safe boundary excludes from the campaign's
  own; a deterministic scan of its unsafe surface backs the judgement where that surface
  is large or the judgement is borderline;
- **advisories**: no unfixed security advisory affects the version and the features the
  campaign uses; and
- **maintenance**: it released within the last 12 months, it is published by an
  organization or by more than one maintainer, and its license and minimum Rust version
  suit the campaign's.

Every fit crate is recommended for the entities it serves best. Once the user adopts it,
those entities get no wrapper and no batches: their consumers use the crate directly, and
their bindings name its types and functions where they would name the wrapper's.

A crate that lacks a little of what it is adopted for is extended rather than passed over: in a fork
cloned beside the campaign's repository, as a wrapper is, on a branch of its own, which the
campaign's workspace pins with a Cargo `[patch]`. The extension is offered upstream, as a
pull request opened with the user's approval, so that the fork can be dropped once it is
merged.
<!-- TODO: whether a ship point may pin an unmerged fork is decided at the end of the
first campaign that meets one. -->

## 7. Local bindings

What a library's adopted crates leave uncovered, when it is too small to be worth a
wrapper, a few functions, is bound where it is used: over the library's established `-sys` crate, in
the consuming module's `ffi_import` region, behind a safe API of that module's, as
[`binding`](../../rust/binding/SKILL.md) describes for any item, by the batch that consumes
it. What grows past a few functions, or what several modules need, is the library's
crustify campaign's.

## 8. Confirmation

An entity's route is a recommendation made before any of its uses was translated. The first
batch that binds or ports one of its users checks the route against the code it translates,
by the uses the entity's `match` and note describe, and reports what it found in its final
message; the assistant records it as the entity's `confirmation`. Each later batch takes
the confirmed route.

When the route does not hold, the batch reaches the entity through another route the
library's `decision` already allows, in this order: the standard library, where
[Standard-library equivalents](#2-standard-library-equivalents) allows it; another crate the
decision adopts for the library; the decision's `uncovered` route. A `crustify-campaign`
route that the library's crustify campaign does not yet cover is reported, and advanced as
[Side campaigns](#3-side-campaigns) describes, before the batch runs again. Where no route
the decision allows serves the entity, because the library leaves nothing `uncovered` or
only a crate the user has not adopted would, the batch reports it, and the assistant puts
it to the user, whose answer is recorded among the decision's `overrides`.
