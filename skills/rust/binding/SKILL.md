---
name: binding
description: "How a scheduled C item becomes a safe Rust binding: the safe boundary, and the type route for structs, unions as tagged enums, enums and typedefs. Read before binding any item, and when reviewing bindings."
---

# Generating safe bindings

How a scheduled C item becomes a safe Rust binding.
A binding keeps the C implementation and puts a safe Rust API in front of it, shaped by the
item's analysis, as [`analysis`](../analysis/SKILL.md) describes. The symbol route, for
functions, globals, function pointers, macros and lifecycle strategies, is
[`binding-symbols`](../binding-symbols/SKILL.md)'s.

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

---

## 2. Type route

### 2.1 Surface

A binding's surface is the fields and lifecycle primitives the public API publishes: in a
wrap batch that precedes its consumers, the fields those consumers access and the
type's lifecycle primitives, so that a type none of whose fields they access is bound
opaque.
Releasers, field disposers, cloners, constructors, casts and pointer-field semantics are
identified before a representation is chosen.

### 2.2 Safe layout

A type is bound as a safe layout over the raw type and its handles. The canonical wrapped
surface has three types, named as the conventions describe:

| type | role |
|---|---|
| `Foo` | layout-compatible newtype named in every owner and handle, and held by value only in Rust-owned storage (a local, or embedded) |
| `FooRef<'a>` | copyable shared borrowed handle with getters |
| `FooMut<'a>` | exclusive borrowed handle with setters, and shared and exclusive reborrows |

Its owners, which [Lifecycle](#23-lifecycle) describes, are named `FooBox` and `FooArc`, as
the conventions name them too. These names are what consumers use, whatever they name: here
pointer wrappers and owners over C's allocator, which a port changes, stage by stage, into
native borrows and owners, as [`porting`](../porting/SKILL.md)'s Structs section describes,
without changing its consumers. A consumer relies only on what every form they may take
offers: their methods, their reborrows (`as_ref`, `as_mut`) and the dereferences the
native forms offer, which the pointer wrappers mirror. What one form offers beyond that,
such as an owner's raw access, is no part of the safe API.

No Rust reference to the wrapped C object is ever formed. Borrowed handles contain
pointers and carry lifetimes; references to handles cover Rust-owned handle storage only.
Layout access starts from `FooRef::as_ptr()` or `FooMut::as_mut_ptr()`, in small justified
unsafe blocks.

A synthetic type generator is bound as:

- a generic wrapper for a homogeneous family converging on the generator;
- an alias of a dominant concrete instance to the generator with its element wrapper; and
- specializations only for behaviour that differs from the generic surface.

### 2.3 Lifecycle

Every ownership variant the analysis supports has a representation.

Owners never dereference to `Foo`; they hand out handles. A sole owner, or a `Foo` value,
produces `FooRef` and `FooMut` through `as_ref()` and `as_mut()`. A shared owner without a
lock produces `FooRef` directly, and `FooMut` only when it can prove its reference is the
only one, or after copying the object. A shared owner whose object carries its own lock
produces both through read and write guards, which hold the lock while the handle lives.

Lifecycle and clone
strategies are stateless, layout-compatible and statically selected when the state is
recoverable from the object; runtime state is carried only when construction, destruction
or cloning needs external data.

A type's constructor and init routines are bound with its lifecycle policy, so that where
possible it is exported as a safe function returning the fully-formed object. Every type an
argument names is wrapped before it, since a wrap brings in its signature's types.

C lifecycle primitives are kept while C can allocate or free the storage.

A type whose address C keeps beyond the call that receives it, to read it, call back with it
or free it, as the analysis establishes, is never moved while C keeps it: a value of it
held by value is never handed to C to keep, and an owner that could move it out is
pinned.

Promoting construction-phase storage into an owner is unsafe, so it is encapsulated in the
type's safe constructor: consumers of the public API never call `assume_init` in their own
unsafe blocks.

Lifecycle routines are also scheduled as free symbols, although the type route emits them
as it binds their types; the symbol route, [`binding-symbols`](../binding-symbols/SKILL.md)'s,
skips those a type batch already emitted.

### 2.4 Field accessors

Each accessor follows from the ownership, mutability, nullability, cardinality and lifetime
findings, and every pointer-derived result is tied to the state that keeps it alive.

Getters that read `Foo`'s fields are methods in `impl FooRef` blocks taking `&self`, and
setters that write them are methods in `impl FooMut` blocks taking `&mut self`. A field is
read through the shared handle's pointer and written through the mutable handle's pointer,
projected with `addr_of!`, `addr_of_mut!`, `&raw const` or `&raw mut`, never with
`&(*p).field` or `&mut (*p).field`.

Each kind of field is expressed as follows:

- An owned-reference field has a replacement setter that drops the old owner, an owning
  getter that leaves the field valid, and a shared borrowed getter.
- A by-value wrapped field has a shared or mutable handle over the projected place.
- A stored borrow without an expressible lifetime has an unsafe setter whose caller
  contract carries the referent-lifetime obligation.
- Statically known owned and borrowed cases have distinct wrapper forms, with a shared
  trait where useful.
- A runtime ownership flag has separately checked owned and borrowed operations.
- A union field and its discriminator are one accessor of a tagged Rust enum, as
  [Unions](#25-unions) describes.
- Scalar and array variants have separate typed forms.
- A type-erased field takes a generic element type when it is known, and the discovered
  untyped lifetime strategy otherwise.
- `Send` and `Sync` are implemented only with a specific synchronization or immutability
  proof.

Translated dependent types and function pointers are used through their safe wrappers,
and strings, arrays and erased owners through real release strategies.

An inline function-pointer helper without an ownership-compatible wrapper gets one,
emitted with the type.

### 2.5 Unions

A union is not bound as a type of its own: the types its members hold are bound, and the
union is presented where it is used, a field accessor or a function's signature, as a
tagged Rust enum, with a variant for each member, each over its member's safe type. One
tagged enum stands in for the union at every use. Its tag is the discriminator the
analysis establishes as selecting the active member: a sibling field, a parameter, or a
predicate over sibling fields, such as a length that is zero only while an inline member
is active. Reading the union evaluates the discriminator to choose the variant, and
writing it writes both.

A union whose active member nothing beside it selects, its tag held by what refers to it,
such as the sign of the index that reaches it, is presented by an `unsafe` accessor for
each member, whose caller contract states which member must be active.

### 2.6 Enums

An enum is bound to a safe Rust type over the constants bindgen generates for it:

- a closed enum is a Rust enum, with a variant for each of its constants;
- an enum whose constants C combines as flags is a `#[repr(transparent)]` newtype over its
  integer type, with an associated constant for each of its constants and the bitwise
  operators, since a combination is no variant; and
- an enum without a name has no type to bind: its constants become constants of its
  integer type.

Beneath a closed enum's safe type sits its integer form, the interop layer C needs: a
`#[repr]` over the enum's integer type, as bindgen gives it, each constant's value its
variant's discriminant, and the conversions through which its values cross the boundary
as that integer. A value from C is converted fallibly where it enters Rust, since C may
pass one the enum does not name, which a Rust enum may not hold: such a value takes the
path the C gives an invalid value, or an error of the safe API where it gives none. A
binding keeps the integer form for good, since C implements what produces and consumes
the enum's values.

### 2.7 Typedefs

A typedef of its own, one that names no struct, union, enum or function pointer, gives
another name to a type that has a Rust form already: a primitive, an array, a pointer, or a
type another link unit or an out-of-tree library's wrapper owns. It is bound under its own
name to the Rust form the analysis shapes from its uses: an alias of the type it names where
they give it no meaning that type lacks, and a type of its own where they do, an invariant,
an ownership or a type erasure that an alias would flatten. Its raw form is no part of the
safe API, as [Safe boundary](#1-safe-boundary) describes, and it has no interop layer of
its own: its values cross the boundary as those of the type it names do.
