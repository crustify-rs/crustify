---
name: conventions
description: "Naming, tree layout, anchors and test placement of the Rust a campaign generates. Read before writing, homing or reviewing generated Rust or tests."
---

# Crustify coding conventions

These are the shared, mechanical contracts of the code a campaign generates: how it is
named, where it sits, how it records what it translated and where its tests go. The
toolchain, edition, lints and formatting it is held to are [`toolchain`](../toolchain/SKILL.md)'s.

## 1. Naming

The workspace's lints enforce the standard Rust casing below, as [`toolchain`](../toolchain/SKILL.md)'s
Lints section describes.

The safe surface uses ordinary Rust naming: `snake_case` for functions, methods and
modules, `UpperCamelCase` for types and traits, `SCREAMING_SNAKE_CASE` for constants and
statics. A C name's library or owning-type prefix is dropped wherever the crate, module or
receiver already supplies it, and the idiomatic Rust term is preferred over a
transliterated C one. The filled anchor records the C name, so renaming costs no
traceability. Names that cross the language boundary keep their C-derived spelling, as
below.

### 1.1 Functions

A C function's raw binding is `ffi::<name>`. Its safe wrapper is a free function homed in
the owning module, named by the rules above. When one C function has several valid
ownership contracts, each safe variant has a distinct, descriptive name.

### 1.2 Types

A wrapped C type is the layout-compatible newtype `Foo`, named by the rules above; its
shared and exclusive borrowed handles are `FooRef<'a>` and `FooMut<'a>`.

### 1.3 Shims

A callable macro shim is `crustify_<NAME>`. Constant macros remain generated constants in
the raw bindings.

### 1.4 Exports

Each ported module has one `mod ffi_export { use super::*; ... }` raw ABI gateway in its
Rust file, whose exports use `#[unsafe(no_mangle)] extern "C"` under the bare C names: the
module's externally visible functions and globals, and the `static inline` functions its
headers define. Static functions and static globals are not exported: nothing outside
their TU reaches them. The exports serve the target's remaining C, its tests and
executables included, which reaches the module through them once it is integrated; an
export is removed, with the raw binding that reaches it, by its symbol's `port/unexport`,
after the integration that removes the last C that calls it, takes its address or
accesses it. An export whose C callers read `errno`
after the call sets it as the C function did, since the Rust behind it never does.

### 1.5 Export features

Each module's `ffi_export` is compiled only under the safe crate's Cargo feature
`ffi-export-<tu>`, with `<tu>` its translation unit's path below the C root, every character
that is not an ASCII letter or digit replaced by `-`. The feature is off until the module is
integrated, so that its exports never collide with the C they replace.

## 2. Crates, modules, and TUs

The Rust tree is the repository's own, as [`layout`](../../operations/layout/SKILL.md)'s Tree section lays it
out, all relative to the repository's root:

- `Cargo.toml` - the safe crate's manifest, which also declares the workspace.
- `src/lib.rs` - the safe crate's root, with one `cfg`-gated module per link unit.
- `src/<link-unit>/` - one sub-dir per link unit.
- `src/ffi.rs` and `ffi/<link-unit>/` - the raw bindings, one public module per link unit,
  laid out as [`bindgen`](../bindgen/SKILL.md) describes.

The safe crate is named after its repository, `<repo>-crustify`, as
[`versioning`](../../operations/versioning/SKILL.md)'s Repositories section names it:
a name crates.io leaves free, which tells it apart from the source's own Rust bindings,
such as `git2` for libgit2.

Within a link unit's sub-dir, the tree follows the module decomposition in `modules.json`
exactly, and preserves the C layout as far as the idiomatic organization of a Rust tree
allows:

- each module is one `.rs` file, at its translation unit's path below the C root with the
  `.rs` extension: its TU and the headers bundled with it have no files of their own,
  since Rust has no headers;
- a header module is one `<stem>_h.rs` file, at its header's path;
- the two modules of a split foundational TU share the TU's file;
- C directories become Rust modules: a directory's `.rs` file sits beside the directory,
  as `<dir>.rs` and `<dir>/`, and declares the modules within it, or is the module of a TU
  with the directory's name where there is one; `mod.rs` files are not used; and
- a file or directory name that is not a Rust identifier is sanitized, hyphens to
  underscores, and a Rust keyword takes a trailing underscore.

Where a C layout has no idiomatic Rust counterpart, the tree adapts it in the conventional
Rust way and keeps the C path recognizable. A batch names the `.rs` file each of its items
belongs in, as `src/<link-unit>/…/<file>.rs`. Entities sharing a
definition site co-home. A home may be shared across waves.

## 3. Anchors

The binder or translator annotates the Rust item that stands in for each C item, and those annotations are the only record
that an item was translated.

An annotation is two attributes on the same Rust item, a doc-comment anchor and a rustdoc
alias:

```rust
/// Wraps `fn::git_repository_open`
#[doc(alias = "git_repository_open")]
pub fn open(path: &Path) -> Result<RepositoryBox, Error> { … }
```

| anchor | meaning |
|---|---|
| ``/// Wraps `<kind>::<path>` `` | safe view over the FFI seam |
| ``/// Replaces `<kind>::<path>` `` | native Rust translation |

The anchor's path is a code span, in backticks, as rustdoc renders it and as the
workspace's `clippy::doc_markdown` lint requires of a path in a doc comment.

`<path>` names the item as its batch schedules it, and `<kind>` says what it is:

| kind | item |
|---|---|
| `fn` | a function |
| `ty` | a named type: a struct, a union or a callback typedef |
| `fld` | a member of a struct or union |
| `var` | a global |

A path is made of names only: the names the source resolves the item by, outermost first,
separated by `.`, as the source language scopes them. A function, a type or a global is its
own name; a member is its struct's or union's path followed by the member's name, and a
member of a member continues the path, as `fld::AVOption.default_val.i64`. An element
without a name adds no step to the paths of what it holds:

- an anonymous struct or union held by a named member is reached through that member, so
  its members are `fld::<path>.<member>.<inner>`;
- the members of an unnamed struct or union member, such as C11's anonymous members, are
  named as members of the type that holds it, as the source reaches them; and
- an array's elements are reached without an index, so the members of an array member's
  element type are `fld::<path>.<member>.<inner>`.

An element without a name has no annotation of its own. The Rust item that stands in for
it is annotated with the named member that holds it, or, when it is held by no name, with
each member it stands in for. A type declared inside another is named as its language
scopes it: a C struct tag has file scope, so a struct declared inside another is still
`ty::<tag>`.

The alias is the bare `<path>`, without the backticks, so that a consumer who searches the
documentation for the source's name finds every item that stands in for it. The kind is
the anchor's alone: a label in the alias would no longer match that search.

### 3.1 What is annotated

The annotation goes on the public item a consumer uses in place of the C item, which is
not necessarily the item that makes the FFI call:

- a function: the function or method the public API exports, which a consumer imports
  instead of the FFI function. The private helper that makes the call, an `ffi_export`
  gateway and a test are not annotated.
- a lifecycle routine, raw, typed or string: the method of the public lifecycle trait the
  strategy implements, such as `CDrop::c_drop`, where it is handwritten, or the macro
  invocation that mints it, which passes the annotation to the method. Again, the method
  annotated need not be the one making the unsafe call.
- a type: the layout newtype that defines the FFI type, handwritten or minted by
  `define_ctype!`.
- a member: each of its accessors, the getter and the setter alike.

### 3.2 Several stand-ins

One C item may have several annotated Rust items, each carrying the same anchor and
alias: the ownership variants one C function is split into when one signature cannot
express every valid contract, as [`binding`](../binding/SKILL.md)'s Functions
section describes, and the accessors of one field. That is the only case in which an
annotation is duplicated. Existing annotations are completed work unless the current
objective deliberately promotes their item.

## 4. Testing

Tests are placed by what they target. Tests of the public interface are Cargo integration
tests of the safe crate, under `tests/`, so crate privacy enforces
the public-interface boundary. Each suite's `main.rs` declares one module per tested
translation unit, in `<suite>/<the tested TU>.rs`.

- Tests that target undefined behaviour on the safe public interface are placed in
  `tests/ub_safe`, whose `main.rs` carries `#![forbid(unsafe_code)]`. Those the compiler
  should reject are placed in `tests/ub_safe/compile_fail/`.
- Tests that target undefined behaviour on the unsafe public interface are placed in
  `tests/ub_unsafe`.
- Tests that compare the public interface's behaviour with C's are placed in
  `tests/equiv`.
- Tests that check internal routines through Rust assertions are placed in an inline
  `#[cfg(test)] mod unit_tests` beside the unit they test.

A standalone reproducer is not a test: it is placed with the report that cites it.
