---
name: ffibox
description: "The library the campaign's Rust holds C memory through: owners, handles, lifecycle policies and C/Rust interop primitives. Read before writing any wrapper, owner or lifecycle strategy, and when testing or reviewing one."
---

# ffibox

ffibox is the library a campaign's Rust holds C memory through: memory a C library
allocates, frees, copies, refcounts or locks, wrapped in the raw bindings' types behind a
safe API, or managed by ported code. C's ownership and lifetime conventions are expressed
through its primitives rather than raw pointers and hand-written `Drop` impls. Its own
documentation, its `README.md`, which walks from a C declaration to the wrapper it needs,
and the documents under its `docs/`, is read in full before the first wrapper is written.

A representation ffibox cannot express is hand-written, with the same seam and
safety-comment discipline.

What follows is how ffibox serves each stage: each section names the skill and section it
adds to, and states only what ffibox adds there.

## Binding and porting

### Binding types

A type that stays interoperable with C is bound through ffibox's primitives wherever they
apply, as its documentation describes.

### Binding types › Safe layout

While a type keeps its C layout, `define_ctype!` mints `Foo`, `FooRef<'a>` and `FooMut<'a>`,
and its owners are aliases of ffibox's owners over the policy that names its lifecycle
routines: `pub type FooBox = CBox<Foo, FooFree>;`, and `CArc<Foo, P>` for `FooArc`. A
value held inline that disposes its resources on drop is a `CVal<Foo, P>`.

### Binding symbols › Function pointers

A Rust closure reaches C through `callback::CClosure`, where C keeps it for the call that
receives it, and `callback::CPayload`, where C keeps it until it releases its context: each
gives the trampoline, typed as the C declaration names it, and the context, and its
trampoline is the panic barrier, `callback::barrier`, which also guards an export's body.
<!-- TODO: both are on ffibox's `feat/bidirectional` branch, not yet released; and ffibox
has no primitive yet for a C function with its context that Rust calls, nor for the
callable type that holds either, which a binding hand-writes until it does. -->

### Binding symbols › Lifecycle strategies

`CBox` and `CArc` own only `CCell` layout types: a single C struct is a `CBox<Foo, P>`
with matching constructor and destructor pairs, which asserts the validity claim its
allocator makes, zeroed memory with `CZeroable` or raw memory with `MaybeUninit`. An array
is a `CVec<MaybeUninit<T>, P>` with a safe initializer, or a `CVec<T, P>` for a
`CPlainElem`; copies into the allocator use `CVec::from_slice` or `CSlice::to_cvec`, and
its `CLenClone` declares `ALIGN`. A Rust value whose release C drives, such as a
refcounted user payload, gets a hand-written owner whose free callback runs the value's
destructor.

### Porting types › Structs

Until a ported struct's `port/layout`, its handles are ffibox's, as
[Binding types › Safe layout](#binding-types--safe-layout) describes; from it
on, `FooRef` and `FooMut` are aliases of native borrows. Its owners stay ffibox's until its
`port/memory`, their policy calling its lifecycle routines, C's through their raw bindings
until each is ported, then the Rust ones.
<!-- TODO: ffibox's owners hold only `CCell` layout types, so an owner over C's allocator
of a struct whose layout is native, between its `port/layout` and its `port/memory`, is
hand-written until ffibox has one. -->

## Testing

### Testing › UB tests

The public seam interface ffibox exports on a type is meant to be exercised inside the
crate only, as an escape hatch for external consumers, so it gets no UB tests: a test of
it, for UB or functionality, is a unit test.

## Reviewing

### Reviewing › Objectives

A workset's use of ffibox's primitives is reviewed against ffibox's documentation, and its
hand-written representations against the contract ffibox would have enforced.

### Reviewing › Reports

A soundness or ergonomics gap in ffibox itself, in its safe primitives or its unsafe FFI
seams, is a defect in a tool, filed on a dedicated branch and worktree of the local ffibox
checkout.
