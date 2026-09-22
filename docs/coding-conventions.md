# Crustify coding conventions

These are the shared, mechanical contracts between the orchestrator,
scheduler and translator. The playbooks contain the decisions and procedures.

## Rust baseline

Crustify crates use Rust edition 2024. Wrapper crates inherit workspace lints
that deny `clippy::undocumented_unsafe_blocks` and allow
`clippy::module_inception`; generated `-sys` code is exempt.

Every unsafe block carries a specific, falsifiable `// SAFETY:` comment. Native
Rust APIs are safe unless their caller obligation cannot be expressed in the
type system.

## Naming

The safe surface uses ordinary Rust naming: `snake_case` for functions, methods
and modules, `UpperCamelCase` for types and traits, `SCREAMING_SNAKE_CASE` for
constants and statics. Drop a C name's library or owning-type prefix wherever
the crate, module or receiver already supplies it, and prefer the idiomatic
Rust term over a transliterated C one. The filled anchor records the C name, so
renaming costs no traceability.

Names that cross the language boundary are fixed and exempt: `ffi::<name>` raw
bindings, `mod ffi_export` exports, `crustify_<NAME>` macro shims and the
`CRUSTIFY_<FILE>` build switch keep their C-derived spelling.

## Crates and modules

The Rust tree mirrors the following layout, all relative to `<repo>/crustify/rust/`:

- `Cargo.toml` - top-level virtual manifest.
- `<link-unit>-sys/` - raw bindings package, one per link unit.
- `<repo>/` - safe repo package, one for the whole repo.
- `<repo>/<link-unit>/` - one sub-dir per link unit, cfg-gated mod in `lib.rs`.

The Rust tree mirrors the subsystem decomposition in `subsystems.json`, and
the filesystem is the source of truth for an entity's home: a batch names the
`.rs` file each of its items belongs in. Each library wrapper crate has a
companion `<lib>-sys` crate for raw bindings.

There is one `.rs` home per C translation unit, or per header group when no
translation unit owns the entity. Entities sharing a definition site co-home.
A home is shared across waves; completed items remain in place.

Rust has no headers, they are homed using the following rules:
- for a wrap campaign: each public header gets its own `mod` and `.rs`. 
- for a port campaign:
  - a subsystem's headers and translation units share one module;
  - a TU and its companion header share a sub-module in their subsystem;
  - headers that export implementation (e.g. `static inline` functions)
  which logically do not belong to any TU get their own `_h.rs` sub-module;
  headers shared by multiple subsystems become sub-modules for each subsystem;

## Wrapped types

The canonical wrapped surface has three types:

| type | role |
|---|---|
| `Foo` | layout-compatible newtype used for embedding and owned storage |
| `FooRef<'a>` | copyable shared borrowed handle with getters |
| `FooMut<'a>` | exclusive borrowed handle with setters and shared reborrows |

Owning handles produce `FooRef` and `FooMut` through `as_ref()` and `as_mut()`;
they do not dereference to `Foo`. Layout access starts from
`FooRef::as_ptr()` or `FooMut::as_mut_ptr()`.

Never form a Rust reference to the wrapped C object. Borrowed handles contain
pointers and carry lifetimes; references to handles cover Rust-owned handle
storage only. Keep raw layout access in small justified unsafe blocks.
Read through the shared handle's pointer and write through the mutable handle's pointer.

## Functions and FFI names

The raw binding for a C function lives under `ffi::<name>`. Its safe wrapper is
a free function homed in the owning module and named per the naming rules
above. When one C function has several valid ownership contracts, give each
safe variant a distinct, descriptive name.

A callable macro shim is named `crustify_<NAME>`. Constant macros remain
generated constants in the `-sys` crate.

Each ported C source file has one `mod ffi_export { use super::*; ... }` raw ABI
gateway in its Rust module. Its exports use `#[unsafe(no_mangle)] extern "C"`.
Export externally visible and header-inline symbols under their bare names.
Export static functions, TU-inline functions and static globals as
`crustify_<file>__<name>`.

The per-file C/Rust build switch is `CRUSTIFY_<FILE>`, with `<FILE>` derived by
sanitizing the translation unit's path.

## Anchors

A scheduled item arrives with the authored Rust file it belongs in, named by
its batch. Nothing is written into that file ahead of the agent: the translator
emits exactly one filled doc-comment anchor per item, and those anchors are the
only record that an item was translated.

| anchor | meaning |
|---|---|
| `/// Wraps: <name>{.<field>}` | safe view over the FFI seam |
| `/// Replaces: <name>{.<field>}` | native Rust translation |
| `/// Field: <name>.<field>` | field accessor over a wrapped type |

`Field:` applies to a field only. It is what a field accessor emitted on a
wrapped type carries, and campaign coverage counts distinct `type.field` paths
that reached one.

The TODO does not survive beside the filled anchor. A surviving TODO is open
work. Duplicate a filled anchor only when several wrappers intentionally
represent the same item. Existing filled anchors are completed work unless the
current objective deliberately promotes that item.
