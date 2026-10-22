# Dependencies

How a campaign reaches the libraries its target uses from outside its tree: libc, zlib,
OpenSSL and the like. The [decomposition](decomposition.md) records each one a module
uses as a dependency record, with the entities the module consumes from it and the Rust
crates that port or bind it; this spec describes what the campaign does with them.

## 1. Wrappers

An out-of-tree library a campaign uses is reached through a Crustify wrapper of its own,
unless the user instructs the campaign to adopt an existing crate. The `ported` and
`bindings` records of `modules.json` inform that choice and the user's instructions; they
do not make it.

Each wrapped library has its own crate in the campaign's workspace, at
`wrappers/<library>/`, named `crustify-<library>`, with its raw bindings and the safe
wrappers over them. Its items are bound as [`items/binding.md`](items/binding.md)
describes, homed in its `src/` by the header that declares them, below the library's
include root, and anchored like any other binding. The safe crate and the `-sys` crates
depend on it, never on its raw bindings directly once a safe wrapper exists.

A wrapper covers only what the campaign consumes: the entities the dependency records
count, wrapped as their consumers need them.

## 2. Reuse

The `crustify-rs` organization keeps the wrappers earlier campaigns built, each in its
own repository, `crustify-rs/crustify-<library>`. Before a campaign plans a library's
wrap batches, it checks there for that library's wrapper. One that exists is the
campaign's starting point: the workspace depends on it, its items are not scheduled again,
and the campaign wraps only what it lacks, as additions to it. A library without one gets
a new wrapper, which can be published there for the next campaign.

## 3. Scheduling

A library's wrap batches are scheduled lazily, as [scheduling](scheduling.md)'s Wrap
waves section describes: each in the wave right before the first wave whose items use
what it wraps.

## 4. Adopted crates

When the user instructs a campaign to adopt a crate for a library, such as one of its
`ported` or `bindings` records, the library gets no wrapper and no batches: its consumers
use the crate directly, and their bindings name its types and functions where they would
name the wrapper's.
