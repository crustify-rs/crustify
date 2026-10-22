# Crustify coding conventions

These are the shared, mechanical contracts of the code a campaign generates. The roles'
prompts contain the decisions and procedures.

## 1. Rust baseline

Crustify crates use Rust edition 2024. Wrapper crates inherit workspace lints that deny
`clippy::undocumented_unsafe_blocks` and allow `clippy::module_inception`, since a C
directory often holds a TU of its own name; generated `-sys` code is exempt.

Every unsafe block carries a specific, falsifiable `// SAFETY:` comment. Native Rust APIs
are safe unless their caller obligation cannot be expressed in the type system.

## 2. Naming

The safe surface uses ordinary Rust naming: `snake_case` for functions, methods and
modules, `UpperCamelCase` for types and traits, `SCREAMING_SNAKE_CASE` for constants and
statics. A C name's library or owning-type prefix is dropped wherever the crate, module or
receiver already supplies it, and the idiomatic Rust term is preferred over a
transliterated C one. The filled anchor records the C name, so renaming costs no
traceability. Names that cross the language boundary keep their C-derived spelling, as
below.

### 2.1 Functions

A C function's raw binding is `ffi::<name>`. Its safe wrapper is a free function homed in
the owning module, named by the rules above. When one C function has several valid
ownership contracts, each safe variant has a distinct, descriptive name.

### 2.2 Types

A wrapped C type is the layout-compatible newtype `Foo`, named by the rules above; its
shared and exclusive borrowed handles are `FooRef<'a>` and `FooMut<'a>`.

### 2.3 Shims

A callable macro shim is `crustify_<NAME>`. Constant macros remain generated constants in
the `-sys` crate.

### 2.4 Exports

Each ported C source file has one `mod ffi_export { use super::*; ... }` raw ABI gateway
in its Rust module, whose exports use `#[unsafe(no_mangle)] extern "C"`. Externally
visible and header-inline symbols are exported under their bare names; static functions,
TU-inline functions and static globals as `crustify_<file>__<name>`.

### 2.5 Build switches

The per-file C/Rust build switch is `CRUSTIFY_<FILE>`, with `<FILE>` derived by sanitizing
the translation unit's path.

## 3. Crates, modules, and TUs

The Rust tree mirrors the following layout, all relative to `<repo>/crustify/rust/`:

- `Cargo.toml` - top-level virtual manifest.
- `<link-unit>-sys/` - raw bindings package, one per link unit.
- `<repo>/` - safe repo package, one for the whole repo.
- `<repo>/<link-unit>/` - one sub-dir per link unit, `cfg`-gated module in `lib.rs`.

Within a link unit's sub-dir, the tree follows the module decomposition in `modules.json`
exactly, and preserves the C layout as far as the idiomatic organization of a Rust tree
allows:

- each module is one `.rs` file, at its translation unit's repo-relative path with the
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
belongs in, as `crustify/rust/<repo>/<link-unit>/…/<file>.rs`. Entities sharing a
definition site co-home. A home may be shared across waves.

## 4. Anchors

A scheduled item arrives with the authored Rust file it belongs in, named by its batch.
Nothing is written into that file ahead of the agent: the binder or translator emits exactly
one filled doc-comment anchor per item, and those anchors are the only record that an item
was translated.

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

## 5. Testing

Tests are placed by what they target. Tests of the public interface are Cargo integration
tests of the safe crate, under `crustify/rust/<target>/tests/`, so crate privacy enforces
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
