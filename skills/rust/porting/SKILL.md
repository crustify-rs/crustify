---
name: porting
description: "How a scheduled C item is reimplemented in safe Rust: surface, storage and layout, lifecycle, symbols and their exports, later stages. Read before porting any item, and when reviewing ports."
---

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
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section describes, so neither
a test's field access nor a definition in an installed header keeps the layout in C.

## 3. Lifecycle

Once Rust fully owns allocation and destruction, the type uses native Rust lifecycle
operations instead of the C primitives.

## 4. Symbols

A ported symbol's implementation is translated to safe, idiomatic Rust with its observable
behaviour preserved. When a wrapper of it already exists, because a module that ran
before needed it, the port keeps that wrapper's safe API and replaces only what is behind
it, so that its consumers do not change, as do the later stages of the types it serves,
which [Later stages](#5-later-stages) describes. A standard-library operation is used
directly when it is equivalent and no C-interoperability requirement remains, an
out-of-tree library's entity included, as the binding how-to's Safe boundary section
describes.

While C consumers remain, the symbol is re-exported to C as the conventions describe:

- The raw gateway reconstructs safe wrappers and calls the native function.
- The gateway is compiled only under its module's export feature, which stays off until
  the module is integrated, so that the exports never collide with the C they replace.
- An export is removed by the symbol's `port/unexport`, after its last C consumer is removed.
- At integration, the Rust static library is linked in place of the TU through the actual
  build system, without assuming link mechanics, and the TU is deleted, as
  [`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Builds section describes.

## 5. Later stages

A later stage, as [`scheduling`](../../planning/scheduling/SKILL.md)'s Later
stages section schedules it, changes an item that has already landed, once the
integrations that free it have landed:

- `port/layout`: the type takes a Rust-native layout, as
  [Storage and layout](#2-storage-and-layout) describes, its C layout gone with its last C
  user;
- `port/memory`: the type's storage moves from C's allocator to Rust's, as
  [Lifecycle](#3-lifecycle) describes: its owners allocate and drop it natively; and
- `port/unexport`: the function's or global's export, which no remaining C references any
  more, is removed with the raw binding and the allowlist entry that reach it.

A stage changes the item and the code inside the crate that reaches its C form, its seams
and export gateways, never the safe API its consumers use, and keeps the item's tests
passing. A stage that moves state out of C, a lock or a handle a type held in its C layout,
or memory C's allocator held, moves its uses onto the standard library where the binding
how-to's Safe boundary section lets it.
