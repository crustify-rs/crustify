---
name: porting
description: "How a scheduled C item is reimplemented in safe Rust: the FFI boundary and its exports, the type route for structs, unions and enums, the symbol route for functions, globals, static inline functions and macros, each with its later stages. Read before porting any item, and when reviewing ports."
---

# Porting

How a scheduled C item is reimplemented in safe Rust. A port starts from the item's
analysis, as [`analysis`](../analysis/SKILL.md) describes, and keeps C interoperability
and observable behaviour for as long as C consumes the item.

A port gives an item its native safe API at once, and that API does not change after it.
An item the remaining C still uses keeps a C form behind it, its C layout, its storage in
C's allocator, its export or its integer values, so that the C keeps working while its
Rust consumers stay agnostic of which form implements it. The later stages its kind
describes below migrate that form to Rust, part by part, once the integrations that free
it have landed, as [`scheduling`](../../planning/scheduling/SKILL.md)'s Later stages
section schedules them. An item no C uses is native in its API and its implementation from
its port.

A later stage changes the item and the code inside the crate that reaches its C form, its
seams and export gateways, never the safe API its consumers use, and keeps the item's tests
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

- The raw gateway reconstructs safe wrappers and calls the native function.
- The gateway is compiled only under its module's export feature, which stays off until
  the module is integrated, so that the exports never collide with the C they replace.
- At integration, the Rust static library is linked in place of the TU through the actual
  build system, without assuming link mechanics, and the TU is deleted, as
  [`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Builds section describes.

---

## 2. Type route

A ported type's surface covers every field the targeted symbols touch and every lifecycle
primitive, not only those the public API publishes.

### 2.1 Structs

Ported storage becomes Rust-owned only once no C path accesses, allocates or frees it.
While C still owns either operation, compatible storage is retained and the blocker
reported.

A layout is ported only once no unported C of the target touches it: no field toucher,
and no other layout user. Tests and the C consumers outside the target do not count, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section
describes, so neither a test's field access nor a definition in an installed header keeps
the layout in C.

Its later stages:

- `port/layout`: the struct takes a Rust-native layout, its C layout gone with its last C
  layout user; and
- `port/memory`: its storage moves from C's allocator to Rust's: its owners allocate and
  drop it natively, and it uses native Rust lifecycle operations instead of the C
  primitives.

### 2.2 Unions

A union's safe API is the tagged Rust enum [`binding`](../binding/SKILL.md)'s Unions
section presents it as, from its port. Its storage keeps the C union, with its
discriminator beside it, while C uses its layout, and is ported as a struct's is, with the
same later stages: its `port/layout` makes the tagged enum its storage, the discriminator
folded into the enum's tag.

### 2.3 Enums

A ported enum takes the safe type [`binding`](../binding/SKILL.md)'s Enums section gives
it, and its header keeps the C definition for the remaining C: the two are not linked,
beyond the Rust type's annotation, as the [conventions](../conventions/SKILL.md)' Anchors
section describes, and the enum is not exported.

A closed enum keeps its integer form, which binding's Enums section describes, only while
remaining C uses it, its constants or values of its type. Its later stage, `port/layout`,
removes that form, its C layout: its `repr`, its discriminants and its conversions. A
closed enum that no remaining C uses by its port has no integer form, and a flags enum or
an enum without a name has no later stage.
<!-- TODO: no enum's `port/layout` is planned until wavefront schedules enums, as its
skill's TODO says. -->

---

## 3. Symbol route

A ported symbol's implementation is translated to safe, idiomatic Rust with its observable
behaviour preserved.

### 3.1 Functions

A function that remaining C calls or takes the address of is exported, as
[FFI boundary](#1-ffi-boundary) describes. Its later stage, `port/unexport`, removes the
export, with the raw binding and the allowlist entry that reach it, once no remaining C
references it.

### 3.2 Globals

A global that remaining C accesses is exported, and keeps its C layout and its
synchronization protocol while it is, as `binding`'s Globals section describes. Its later
stage, `port/unexport`, removes the export, as a function's does.

### 3.3 Static inline functions

A `static inline` function a header defines is internal API of the module the
decomposition gives it, and is ported as its other functions are. Its C callers expand its
body in their own TUs, so an export alone does not reach them: at the module's
integration, the header's definition is replaced by its prototype, and the remaining C
calls the Rust module's export, under the function's bare name, where it inlined the body.
<!-- TODO: cross-language LTO (`-Clinker-plugin-lto`, with a clang whose LLVM matches
rustc's) would inline the export back into its C callers. -->

### 3.4 Macros

A macro takes the Rust form [`binding`](../binding/SKILL.md)'s Macros section gives it,
which reaches the Rust items its expansion uses once they are ported. A macro a TU defines
goes with its TU. A macro a header defines, internal or public API that another module's C
may expand, also stays in its header for the remaining C, unexported, and its C and Rust
forms are not linked, beyond the Rust form's annotation. It keeps expanding where remaining C
invokes it, until its header goes with the last C file that includes it, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section
describes: a type generator keeps minting the instances its remaining invocations define,
and what an expansion calls or accesses is reached as any remaining C reaches it, a
function or global Rust owns through its export, a type through its C layout. An
expansion site is a use by the function that holds it, so it holds back the later stages
of what it reaches, as [`scheduling`](../../planning/scheduling/SKILL.md)'s Later stages
section counts its users.
