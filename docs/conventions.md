# Crustify coding conventions

These are the shared, mechanical contracts between the orchestrator, the binder, the
translator and the reviewer. Their prompts contain the decisions and procedures.

## Rust baseline

Crustify crates use Rust edition 2024. Wrapper crates inherit workspace lints that deny
`clippy::undocumented_unsafe_blocks` and allow `clippy::module_inception`; generated
`-sys` code is exempt.

Every unsafe block carries a specific, falsifiable `// SAFETY:` comment. Native Rust APIs
are safe unless their caller obligation cannot be expressed in the type system.

## Naming

The safe surface uses ordinary Rust naming: `snake_case` for functions, methods and
modules, `UpperCamelCase` for types and traits, `SCREAMING_SNAKE_CASE` for constants and
statics. A C name's library or owning-type prefix is dropped wherever the crate, module or
receiver already supplies it, and the idiomatic Rust term is preferred over a
transliterated C one. The filled anchor records the C name, so renaming costs no
traceability. Names that cross the language boundary keep their C-derived spelling, as
below.

### Functions

A C function's raw binding is `ffi::<name>`. Its safe wrapper is a free function homed in
the owning module, named by the rules above. When one C function has several valid
ownership contracts, each safe variant has a distinct, descriptive name.

### Types

A wrapped C type is the layout-compatible newtype `Foo`, named by the rules above; its
shared and exclusive borrowed handles are `FooRef<'a>` and `FooMut<'a>`.

### Shims

A callable macro shim is `crustify_<NAME>`. Constant macros remain generated constants in
the `-sys` crate.

### Exports

Each ported C source file has one `mod ffi_export { use super::*; ... }` raw ABI gateway
in its Rust module, whose exports use `#[unsafe(no_mangle)] extern "C"`. Externally
visible and header-inline symbols are exported under their bare names; static functions,
TU-inline functions and static globals as `crustify_<file>__<name>`.

### Build switches

The per-file C/Rust build switch is `CRUSTIFY_<FILE>`, with `<FILE>` derived by sanitizing
the translation unit's path.

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
  - a TU an item-granular subsystem takes items from likewise becomes a sub-module of each
    subsystem, homing the units it owns.

In a wrap campaign, an item-granular subsystem's items home in the module of the public
header that publishes them, which the subsystem that owns the header's other items shares.

## Anchors

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

## Testing

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
