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
shared and exclusive borrowed handles are `FooRef<'a>` and `FooMut<'a>`, and its sole and
counted owners `FooBox` and `FooArc`. A port keeps these names while what they name
changes, as [`porting-types`](../porting/types/SKILL.md)'s Structs section describes. A typedef that
names a type under another name, which its item lists among its `typedefs`, is a
`pub type` alias of the type's Rust form.

A function pointer a typedef declares is named after its typedef. One written inline is
named after the site that declares it, its holder's name followed by its own and `Fn`: a
field's `<Struct><Field>Fn`, a parameter's `<Function><Param>Fn`, a return's
`<Function>ReturnFn` and a global's `<Global>Fn`.

### 1.3 Shims

A callable macro shim is `crustify_<NAME>`.

### 1.4 Exports

Each ported module has one raw ABI gateway, its `ffi_export` region, as
[Unsafe regions](#21-unsafe-regions) describes, whose exports use `#[unsafe(no_mangle)] extern "C"` under the bare C names: the
module's functions and globals that C outside the module references, another module's TU
or a C test or executable that stays, the `static inline` functions its headers define
included. The exports serve that C, which reaches the module through them once it is
integrated. A function or global only the module's own C references is not exported: that
C leaves the build with the module at its integration, and its callers are Rust from then
on; nor are static functions and static globals, which nothing outside their TU reaches.
The target's public C API, for C outside the target, is deferred: exports serve the
target's own remaining C alone, and that API is a layer of its own over the native Rust API,
added once the modules it covers are ported.
An export is removed, with the raw binding that reaches it, by its symbol's `port/unexport`,
after the integration that removes the last C that calls it, takes its address or
accesses it. A C test tied to the module that stays, using only its public API, does not
hold an export back: it checks the export while other C needs it, and leaves with it.

### 1.5 Export features

Each module's `ffi_export` is compiled only under the safe crate's Cargo feature
`ffi-export-<tu>`, with `<tu>` its translation unit's path below the C root, every character
that is not an ASCII letter or digit replaced by `-`. The feature is off until the module is
integrated, so that its exports never collide with the C they replace, and the integration
deletes it, its gateway compiling unconditionally from then on.

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

### 2.1 Unsafe regions

A module's unsafe code is confined to at most two inline child modules of its file, its
unsafe regions, so that the rest of the file, its native code, holds none:

- `mod ffi_import`: what the module reaches in C: its calls through the raw bindings, the C
  layouts it wraps with their handles and accessors, the owners and lifecycle policies over
  C's allocator, and the trampolines and contexts through which C calls a Rust closure
  back; and
- `mod ffi_export { use super::*; … }`: the gateway through which C reaches the module by
  symbol, as [Exports](#14-exports) describes, compiled only under its
  [export feature](#15-export-features).

Unsafe code is every `unsafe` block, `unsafe fn`, `unsafe impl`, `unsafe extern` block and
`#[unsafe(…)]` attribute, and every invocation of another crate's macro that expands to
one, such as ffibox's `define_ctype!`, which the compiler's `unsafe_code` lint does not
see. Outside the regions, only the raw bindings hold any. The regions take the lint back as
[`toolchain`](../toolchain/SKILL.md)'s Unsafe code section describes.

A region exposes to its module only what [`binding`](../binding/SKILL.md)'s Safe boundary
section lets it expose, and the module re-exports the public items a region defines, as
`pub use ffi_import::{Foo, FooBox, FooMut, FooRef};`, so that their paths do not depend on
which side defines them. A type's inherent `impl` blocks may be split between the native
code and a region: each method is visible as its own visibility says, counted from the
module that holds its block, so that a region's private helpers stay hidden from the
native code.

A region exists only while it holds something. A wrap's items are in `ffi_import`. A port
writes its item in the native code, and keeps in the regions only the C form the item
keeps, as [`porting`](../porting/SKILL.md) describes; a wrapped item it ports leaves
`ffi_import` with its re-export. The later stages empty the regions part by part: an
item's C layout and C owners leave `ffi_import` with its `port/layout` and `port/memory`,
its export leaves `ffi_export` with its `port/unexport`. A module without either region is
native, and its file carries `#![forbid(unsafe_code)]`.

## 3. Anchors

The Rust item that stands in for each C item is annotated, and those annotations are the
only record that an item was translated.

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
| `st` | a struct |
| `un` | a union |
| `enm` | an enum, or one of its constants |
| `fnp` | a function pointer |
| `tdf` | a typedef: one of its own, or one an item lists among its `typedefs` |
| `fld` | a member of a struct or union |
| `glb` | a global |
| `mac` | a macro |

A path is made of names only: the names the source resolves the item by, outermost first,
separated by `.`, as the source language scopes them. A function, a type, an enum's
constant, a global, a typedef or a function pointer a typedef declares is its own name,
since C scopes a constant as it does its enum. A member is its struct's or union's path
followed by the member's name, and a member of a member continues the path, as
`fld::AVOption.default_val.i64`. A function pointer written inline is its declaring site's
path: a member's, `<function>.<param>` for a parameter, `<function>.return` for a return,
or a global's name. An element without a name adds no step to the paths of what it holds:

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
`st::<tag>`. An enum without a name has no annotation of its own, and its constants keep
theirs.

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
- a union: the tagged enum that stands in for it at every use.
- an enum: the Rust enum or newtype that stands in for it, and each of its constants: the
  variant or the constant that stands in for it.
- a macro: the generic, `const`, function or `macro_rules!` that stands in for it; a type
  generator's instances keep their own kinds, on the aliases.
- a function pointer: the callable type that stands in for it, or the trait, for a struct
  of function pointers.
- a typedef: the alias that stands in for it.
- a member: each of its accessors, the getter and the setter alike.

### 3.2 Several stand-ins

One C item may have several annotated Rust items, each carrying the same anchor and
alias: the ownership variants one C function is split into when one signature cannot
express every valid contract, as [`binding-symbols`](../binding/symbols/SKILL.md)'s
Functions section describes, and the accessors of one field. That is the only case in which an
annotation is duplicated. Existing annotations are completed work unless the current
objective deliberately promotes their item: a port of an item a binding wraps, or the
`port/layout` that gives a wrapped struct or union its native layout, replaces its `Wraps`
anchor with a `Replaces` one, and keeps its alias.

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
- Tests that compare the module's exported API with C's are placed in `tests/equiv_pub`,
  and those that compare its internals with C's in an inline `#[cfg(test)] mod equiv_priv`
  beside the unit they test.
- Tests that check the public interface through Rust assertions are placed in
  `tests/unit_pub`, and those that check internal routines in an inline
  `#[cfg(test)] mod unit_priv` beside the unit they test.

An inline test of a region's code sits in that region, and an inline test that holds
unsafe code, such as an `equiv_priv` test calling the C, sits in a region: the module's
`ffi_import`, for the C it calls. The suites whose tests call the raw bindings or the public unsafe API,
`tests/ub_unsafe` and `tests/equiv_pub`, take `unsafe_code` back at their `main.rs`, as a
region does.

A standalone reproducer is not a test: it is placed with the report that cites it.
