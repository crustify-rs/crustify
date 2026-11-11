---
name: binding
description: "How a scheduled C item becomes a safe Rust binding: the safe boundary every binding keeps, and the routes binding-types and binding-symbols give types and symbols. Read before binding any item, and when reviewing bindings."
---

# Generating safe bindings

How a scheduled C item becomes a safe Rust binding.
A binding keeps the C implementation and puts a safe Rust API in front of it, shaped by the
item's analysis, as [`analysis`](../analysis/SKILL.md) describes. A type takes the type
route, for structs, unions, enums and typedefs, as [`binding-types`](types/SKILL.md)
describes; a symbol the symbol route, for functions, globals, function pointers, macros and
lifecycle strategies, as [`binding-symbols`](symbols/SKILL.md) describes.

## 1. Safe boundary

Any ABI or layout C still observes is preserved, and imported entities remain C-owned.

Rust consumers use safe APIs. Raw operations are confined to:

- wrapped-layout projection;
- wrapped FFI calls; and
- operations whose caller obligation cannot be represented in Rust types.

They sit in their module's unsafe regions, as the [conventions](../conventions/SKILL.md)'
Unsafe regions section lays them out, and a region's soundness rests on the region alone:
each item it exposes is sound for every input the rest of its module can give it, the
invariants its unsafe code relies on being held in the region's own private fields or
guaranteed by ffibox or the standard library, never by data the native code can build or
change. It exposes no field its unsafe code relies on, and no `unsafe fn` beyond the
public ones whose obligation no type expresses.

A dependency on a module that runs later, cut from a cycle, is reached through the safe
wrappers a wrap batch adds before its consumer, never through raw bindings. A wrapper over
the items of a module that will be ported is written as that module's API: the names,
ownership and error types its port keeps, so that its consumers do not change when it
ports. Every unsafe block carries
the safety comment [`toolchain`](../toolchain/SKILL.md)'s Unsafe code section specifies.

An out-of-tree library's entity, such as libc's or libm's, is reached through the Rust
standard library wherever it provides it and the state the entity works on stays in Rust,
or crosses to C only as values the boundary converts: `errno` set from an `io::Error` by
an export gateway, a `struct stat` filled from an `fs::Metadata`. It is reached through the
library's bindings wherever that state is shared with C: a lock, a handle or an allocation
the remaining C uses too. The code being translated decides which; no plan records it. An
entity needed through a wrapper that lacks it is reported, never reached through raw
bindings.
