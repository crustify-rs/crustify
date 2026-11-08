# Porting

How a scheduled C item is reimplemented in safe Rust. A port builds on the binding how-to:
item analysis, macros and the safe boundary apply unchanged, and a ported item keeps C
interoperability and observable behaviour for as long as C consumes it.

## 1. Surface

A ported type's surface covers every field the targeted symbols touch and every lifecycle
primitive, not only those the public API publishes.

## 2. Storage and layout

Ported storage becomes Rust-owned only once no C path accesses, allocates or frees it. While
C still owns either operation, compatible storage is retained and the blocker reported.

A layout is ported only once no unported C of the target touches it: no field toucher,
and no other layout user. Tests and the C consumers outside the target do not count, as
[`../../workflows/porting.md`](../../workflows/porting.md)'s Principles section describes, so neither
a test's field access nor a definition in an installed header keeps the layout in C.

## 3. Lifecycle

Once Rust fully owns allocation and destruction, the type uses native Rust lifecycle
operations instead of the C primitives.

## 4. Symbols

A ported symbol's implementation is translated to safe, idiomatic Rust with its observable
behaviour preserved. When a wrapper of it already exists, because a module that ran
before needed it, the port keeps that wrapper's safe API and replaces only what is behind
it, so that its consumers do not change, as do the deferred steps of the types it serves,
which [Deferred steps](#5-deferred-steps) describes. A standard-library operation is used directly when it is equivalent
and no C-interoperability requirement remains, an out-of-tree library's entity included, as
[`../../planning/dependencies.md`](../../planning/dependencies.md)'s Standard-library
equivalents section describes.

While C consumers remain, the symbol is re-exported to C as the conventions describe:

- The raw gateway reconstructs safe wrappers and calls the native function.
- The gateway is compiled only under its module's export feature, which stays off until
  the module is integrated, so that the exports never collide with the C they replace.
- An export is removed after its last C consumer is removed.
- At integration, the Rust static library is linked in place of the TU through the actual
  build system, without assuming link mechanics, and the TU is deleted, as
  [`../../workflows/porting.md`](../../workflows/porting.md)'s Builds section describes.

## 5. Deferred steps

A deferred step, as [`../../planning/scheduling.md`](../../planning/scheduling.md)'s
Deferred items section schedules it, changes an item that has already landed, once the
integrations that free it have landed:

- `layout`: the type takes a Rust-native layout, as [Storage and layout](#2-storage-and-layout)
  describes, its C layout gone with its last C user, and its safe API unchanged;
- `memory`: the type's storage moves from C's allocator to Rust's, as
  [Lifecycle](#3-lifecycle) describes: its owners allocate and drop it natively;
- `std`: a function moves onto the standard-library equivalent of an out-of-tree
  library's entity, which no remaining C shares any more, as
  [`../../planning/dependencies.md`](../../planning/dependencies.md)'s Standard-library
  equivalents section describes.

A step changes the item and the code inside the crate that reaches its C form, its seams
and export gateways, never the safe API its consumers use, and keeps the item's tests
passing.
