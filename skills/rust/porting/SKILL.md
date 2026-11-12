---
name: porting
description: "How a scheduled C item is reimplemented in safe Rust: its native API, its later stages, the FFI boundary and its exports, and the routes porting-types and porting-symbols give types and symbols. Read before porting any item, and when reviewing ports."
---

# Porting

How a scheduled C item is reimplemented in safe Rust. A port starts from the item's
analysis, as [`analysis`](../analysis/SKILL.md) describes, and keeps C interoperability
and observable behaviour for as long as C consumes the item. A type takes the type route,
for structs, unions, enums and typedefs, as [`porting-types`](types/SKILL.md) describes; a
symbol the symbol route, for functions, globals, function pointers, static inline functions
and macros, as [`porting-symbols`](symbols/SKILL.md) describes.

A port gives an item its native safe API at once, and that API does not change after it.
An item the remaining C still uses keeps a C form behind it, its C layout, its storage in
C's allocator, its export or its integer values, so that the C keeps working while its
Rust consumers stay agnostic of which form implements it. The later stages its kind
describes below migrate that form to Rust, part by part, once the switches that free
it have landed, as [`scheduling`](../../planning/scheduling/SKILL.md)'s Later stages
section schedules them. An item no C uses is native in its API and its implementation from
its port.

A later stage changes the item and the code inside the crate that reaches its C form, in
its module's unsafe regions, as the [conventions](../conventions/SKILL.md)' Unsafe regions
section describes, never the safe API its consumers use, and keeps the item's tests
passing. A stage that moves state out of C, a lock or a handle a type held in its C layout,
or memory C's allocator held, moves its uses onto the standard library where
[`binding`](../binding/SKILL.md)'s Safe boundary section lets it.

## 1. FFI boundary

`binding`'s Safe boundary section applies to a port unchanged. When a wrapper of the item
already exists, because a module that ran before needed it, the port keeps that wrapper's
safe API and replaces only what is behind it, so that its consumers do not change, as do
its later stages. A standard-library operation is used directly when it is equivalent and
no C-interoperability requirement remains, an out-of-tree library's entity included, as
`binding`'s Safe boundary section describes.

While C consumers remain, a ported item is re-exported to C as the
[conventions](../conventions/SKILL.md)' Exports section describes:

- The raw gateway, its module's `ffi_export` region, reconstructs safe wrappers and calls
  the native function.
- The gateway is compiled only under its module's export feature, which stays off until
  the module switches, so that the exports never collide with the C they replace.
- At the switch, the Rust static library is linked in place of the TU through the actual
  build system, without assuming link mechanics, and the TU is deleted, as
  [`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Builds section describes.
