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

### Binding › Type route

A type that stays interoperable with C is bound through ffibox's primitives wherever they
apply, as its documentation describes.

### Binding › Symbol route › Lifecycle strategies

`CBox` and `CArc` own only `CCell` layout types: a single C struct is a `CBox<Foo, P>`
with matching constructor and destructor pairs, which asserts the validity claim its
allocator makes, zeroed memory with `CZeroable` or raw memory with `MaybeUninit`. An array
is a `CVec<MaybeUninit<T>, P>` with a safe initializer, or a `CVec<T, P>` for a
`CPlainElem`; copies into the allocator use `CVec::from_slice` or `CSlice::to_cvec`, and
its `CLenClone` declares `ALIGN`. A Rust value whose release C drives, such as a
refcounted user payload, gets a hand-written owner whose free callback runs the value's
destructor.

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
