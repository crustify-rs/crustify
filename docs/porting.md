# Porting

How a scheduled C item is reimplemented in safe Rust. A port builds on the binding how-to:
item analysis, macros and the safe boundary apply unchanged, and a ported item keeps C
interoperability and observable behaviour for as long as C consumes it.

## Surface

A ported type's surface covers every field the targeted symbols touch and every lifecycle
primitive, not only those the public API publishes.

## Storage and layout

Ported storage becomes Rust-owned only once no C path accesses, allocates or frees it. While
C still owns either operation, compatible storage is retained and the blocker reported.

A layout is ported only once every C-side field toucher is gone and no public C consumer
receives the concrete body. A public forward declaration alone does not block
opacification.

## Lifecycle

Once Rust fully owns allocation and destruction, the type uses native Rust lifecycle
operations instead of the C primitives.

## Symbols

A ported symbol's implementation is translated to safe, idiomatic Rust with its observable
behaviour preserved. A standard-library operation is used directly when it is equivalent
and no C-interoperability requirement remains.

While C consumers remain, the symbol is re-exported to C as the conventions describe:

- The raw gateway reconstructs safe wrappers and calls the native function.
- A TU-local export is removed after its last C consumer is removed.
- Only replaced C bodies are guarded, with the path-derived per-file guard; adjacent
  guarded bodies may be grouped, but the whole file is never guarded.
- The C fallback branch declares the Rust exports and redirects TU-local names to
  collision-safe exports.
- The file flag and the Rust static library are wired through the actual build system,
  without assuming link mechanics.
