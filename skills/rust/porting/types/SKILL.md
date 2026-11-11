---
name: porting-types
description: "How a scheduled C type is reimplemented in safe Rust, porting's type route: structs, unions, enums and typedefs, each with its later stages. Read before porting any type, and when reviewing ports."
---

# Porting types

How a scheduled C type is reimplemented in safe Rust: the type route, which follows
[`porting`](../SKILL.md)'s FFI boundary section and starts from
[`binding-types`](../../binding/types/SKILL.md)'s; the symbols it reaches are
[`porting-symbols`](../symbols/SKILL.md)'s.

A ported type's surface covers every field the targeted symbols touch and every lifecycle
primitive, not only those the public API publishes.

## 1. Structs

Ported storage becomes Rust-owned only once no C path accesses, allocates or frees it.
While C still owns either operation, compatible storage is retained and the blocker
reported.

A layout is ported only once no unported C of the target touches it: no field toucher,
and no other layout user. Tests and the C consumers outside the target do not count, as
[`porting-workflow`](../../../workflows/porting-workflow/SKILL.md)'s Principles section
describes, so neither a test's field access nor a definition in an installed header keeps
the layout in C. A struct whose layout another module's C still uses is wrapped where the
order places it instead, keeping its C layout behind a binding, and takes its native layout
from its `port/layout`, as [`scheduling`](../../../planning/scheduling/SKILL.md)'s Later
stages section schedules it.

A struct's lifecycle API is fixed by the item that first gives it a safe API, its port, or
the wrap that precedes its later stages: the owners, handles, constructors, drop and clone
its consumers use from then on, which its later stages keep. Each lifecycle routine behind
them is ported where the order places it, as a function of its own, so that a routine
whose call graph is not ported yet does not bring it forward: until then, the owner's
policy calls the C routine through its raw binding, as a binding's does. Its storage stays
in C's allocator while any C allocates or frees it raw, a lifecycle routine of its own
module still in C included, so that what Rust allocates is never freed by C's releaser,
nor the reverse.

Its handles keep the names that item gives them, `Foo`, `FooRef`, `FooMut` and its owners,
while what they name follows its later stages, so that its consumers never change, as
`binding-types`' Safe layout section describes:

- `port/layout`: the struct, wrapped until then, takes a Rust-native layout, its C layout
  gone with its last C layout user. `Foo` is defined in its module's native code, out of `ffi_import`, each field of the
  native type that keeps the ownership the analysis established, an owning string a
  `String` and a borrowed one a borrow; `FooRef<'a>` and `FooMut<'a>` become aliases of
  `&'a Foo` and `&'a mut Foo`, and the getters and setters move to `impl Foo`, reading and
  writing its fields; and
- `port/memory`: its storage moves from C's allocator to Rust's: its owners become aliases
  of the native ones, `FooBox` of `Box<Foo>` and `FooArc` of `Arc<Foo>`, which allocate and
  drop it natively, with native Rust lifecycle operations instead of the C primitives.

Each switches with its own stage, or with the struct's port where that stage is not
planned, and the two stages come in either order. A `port/memory` before the struct's
`port/layout` keeps its C layout and its handles, and moves its owners to Rust's allocator
alone: they stay the C-layout owners, over a policy of Rust's allocator, since remaining
C still holds pointers into the object and reads its fields, which a native owner's claim
to sole access would break. Its `port/layout` then makes them the native ones.

From its native layout on, from its port or its `port/layout`, a struct has by-value
constructors, `Foo::new(…) -> Foo`, and a constructor that returns an owner builds the
value and moves it into the owner, whose allocator its stage decides: C's while
any C still frees it raw, Rust's from its `port/memory`.

While C keeps its address, as `binding-types`' Lifecycle section describes, a struct with a
native layout is `!Unpin` and its native handles are pinned: `FooMut<'a>` is an alias of
`Pin<&'a mut Foo>` and `FooBox` of `Pin<Box<Foo>>`, and an export gateway rebuilds the
pinned handle from the pointer C passes it. Once no remaining C keeps its address, the
struct becomes `Unpin`, so that its pinned handles give plain access, and its aliases keep
their `Pin`, unchanged for its consumers.

## 2. Unions

A union's safe API is the tagged Rust enum [`binding-types`](../../binding/types/SKILL.md)'s Unions
section presents it as, from its port. Its storage keeps the C union, with its
discriminator beside it, while C uses its layout, and is ported as a struct's is, with the
same later stages: its `port/layout` makes the tagged enum its storage, the discriminator
folded into the enum's tag. A union whose tag what refers to it holds becomes a tagged
enum too, once no other C uses its layout, its referrers' tags folded into it.

## 3. Enums

A ported enum takes the safe type [`binding-types`](../../binding/types/SKILL.md)'s Enums section gives
it, and its header keeps the C definition for the remaining C: the two are not linked,
beyond the Rust type's annotation, as the [conventions](../../conventions/SKILL.md)' Anchors
section describes, and the enum is not exported.

A closed enum keeps its integer form, which `binding-types`' Enums section describes, only while
remaining C uses it, its constants or values of its type. Its later stage, `port/layout`,
removes that form, its C layout: its `repr`, its discriminants and its conversions. A
closed enum that no remaining C uses by its port has no integer form, and a flags enum or
an enum without a name has no later stage. Which enums are closed is the plan's judgment,
as [`scheduling`](../../../planning/scheduling/SKILL.md)'s Later stages section describes: a
port whose analysis finds otherwise gives the enum the form its analysis finds, and reports
the mismatch, which the next planner run corrects.

## 4. Typedefs

A ported typedef takes the Rust form [`binding-types`](../../binding/types/SKILL.md)'s Typedefs section
gives it, which is native from its port, and its header keeps the C typedef for the
remaining C: the two are not linked, beyond the Rust form's annotation, and the typedef is
not exported. It has no later stage: no C form of it remains in Rust for one to remove.
