# Crustify coding conventions

These are the shared, mechanical contracts between the orchestrator and the translator.
Their prompts contain the decisions and procedures.

## Rust baseline

Crustify crates use Rust edition 2024. Wrapper crates inherit workspace lints that deny
`clippy::undocumented_unsafe_blocks` and allow `clippy::module_inception`; generated
`-sys` code is exempt.

Every unsafe block carries a specific, falsifiable `// SAFETY:` comment. Native Rust APIs
are safe unless their caller obligation cannot be expressed in the type system.

## Naming

The safe surface uses ordinary Rust naming: `snake_case` for functions, methods and
modules, `UpperCamelCase` for types and traits, `SCREAMING_SNAKE_CASE` for constants and
statics. Drop a C name's library or owning-type prefix wherever the crate, module or
receiver already supplies it, and prefer the idiomatic Rust term over a transliterated C
one. The filled anchor records the C name, so renaming costs no traceability.

Names that cross the language boundary are fixed and exempt: `ffi::<name>` raw bindings,
`mod ffi_export` exports, `crustify_<NAME>` macro shims and the `CRUSTIFY_<FILE>` build
switch keep their C-derived spelling.

## Crates, modules, and TUs

The Rust tree mirrors the following layout, all relative to `<repo>/crustify/rust/`:

- `Cargo.toml` - top-level virtual manifest.
- `<link-unit>-sys/` - raw bindings package, one per link unit.
- `<repo>/` - safe repo package, one for the whole repo.
- `<repo>/<link-unit>/` - one sub-dir per link unit, `cfg`-gated module in `lib.rs`.

The Rust tree within `<repo>/` mirrors the subsystem decomposition in `subsystems.json`, and each item is homed
in a `.rs` TU corresponding to its location on the original C/C++ filesystem; a batch names the `.rs` file each of its
items belongs in, as `crustify/rust/<repo>/<link-unit>/…/<file>.rs`. Entities sharing a definition site co-home. A home
may be shared across waves.

Rust has no headers, they are homed using the following rules:
- for a wrap campaign: each public header gets its own `mod` and `.rs`.
- for a port campaign:
  - a subsystem's headers and translation units share one sub-dir and module rooted at
    `rust/<repo>/<link-unit>/<subsystem>/<subsystem>.rs`;
  - a TU and its companion header share a sub-module within their subsystem;
  - headers that export implementation (e.g. `static inline` functions) which logically do
    not belong to any TU get their own `_h.rs` sub-module; headers shared by multiple
    subsystems become sub-modules for each subsystem homing the units belonging to that subsystem;

## Wrapped types

The canonical wrapped surface has three types:

| type | role |
|---|---|
| `Foo` | layout-compatible newtype named in every owner and handle, and held by value only in Rust-owned storage (a local, or embedded) |
| `FooRef<'a>` | copyable shared borrowed handle with getters |
| `FooMut<'a>` | exclusive borrowed handle with setters, and shared and exclusive reborrows |

Owners never dereference to `Foo`; they hand out handles. A sole owner, or a `Foo` value,
produces `FooRef` and `FooMut` through `as_ref()` and `as_mut()`. A shared owner without a
lock produces `FooRef` directly, and `FooMut` only when it can prove its reference is the
only one, or after copying the object. A shared owner whose object carries its own lock
produces both through read and write guards, which hold the lock while the handle lives.
Layout access starts from `FooRef::as_ptr()` or `FooMut::as_mut_ptr()`.

Getters that read `Foo`'s fields go on `FooRef` as methods in `impl FooRef` blocks taking `&self`,
while setters that write its fields go on `FooMut` as methods in `impl FooMut` blocks taking
`&self mut`. 

Never form a Rust reference to the wrapped C object. Borrowed handles contain pointers and
carry lifetimes; references to handles cover Rust-owned handle storage only. Keep raw
layout access in small justified unsafe blocks. Read through the shared handle's pointer
and write through the mutable handle's pointer.

## Functions and FFI names

The raw binding for a C function lives under `ffi::<name>`. Its safe wrapper is a free
function homed in the owning module and named per the naming rules above. When one C
function has several valid ownership contracts, give each safe variant a distinct,
descriptive name.

A callable macro shim is named `crustify_<NAME>`. Constant macros remain generated
constants in the `-sys` crate.

Each ported C source file has one `mod ffi_export { use super::*; ... }` raw ABI gateway
in its Rust module. Its exports use `#[unsafe(no_mangle)] extern "C"`. Export externally
visible and header-inline symbols under their bare names. Export static functions,
TU-inline functions and static globals as `crustify_<file>__<name>`.

The per-file C/Rust build switch is `CRUSTIFY_<FILE>`, with `<FILE>` derived by sanitizing
the translation unit's path.

## Anchors

A scheduled item arrives with the authored Rust file it belongs in, named by its batch.
Nothing is written into that file ahead of the agent: the translator emits exactly one
filled doc-comment anchor per item, and those anchors are the only record that an item was
translated.

| anchor | meaning |
|---|---|
| `/// Wraps: <name>{.<field>}` | safe view over the FFI seam |
| `/// Replaces: <name>{.<field>}` | native Rust translation |
| `/// Field: <name>.<field>` | field accessor over a wrapped type |

`Field:` applies to a field only. It is what a field accessor emitted on a wrapped type
carries, and campaign coverage counts distinct `type.field` paths that reached one.

`Wraps` and `Replaces` apply to symbols and types. `Wraps: <name>{.<field>}` is for anonymous
embedded structs. For release/clone strategies `<name>` takes the name of the lifecycle routine called by the
strategy via FFI. Emit anchors for the raw/typed lifecycle routines when implementing the Drop/Clone
that calls them.

Duplicate a filled anchor only when several wrappers intentionally represent the same
item. Existing filled anchors are completed work unless the current objective deliberately
promotes that item.
