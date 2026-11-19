---
name: ffibox
description: "The library the port's Rust holds C memory through, in both directions: owners, handles, lifecycle policies, status conventions, callbacks and exports, and how the agent grows it. Read before writing any owner, handle, lifecycle strategy, callable type or export, when judging a crate for adoption, when testing or reviewing code that uses it, and before adding a primitive to it."
---

# ffibox

ffibox is the library the port's Rust expresses C's ownership and lifetime conventions
through, in both directions: memory C allocates, frees, copies, refcounts or locks, held
from Rust behind a safe API, and memory Rust owns that C holds, calls or reads. Its
primitives stand in for raw pointers and hand-written `Drop` impls wherever C aliases a
value; what C does not alias is plain Rust.

Read its `README.md` in full before writing the first owner or export, and read in full
the documents under its `docs/` that each section below names before that kind of work.
Which primitive serves which C declaration, and how each is built, is those documents'. A
representation ffibox cannot express is hand-written, as its `docs/hand-written.md`
describes, with the same seam and safety-comment discipline.

What follows is what ffibox adds to each kind of work.

## Dependencies

A candidate crate's soundness is read against the hazards that the Soundness section of
`docs/goals.md` lists. ffibox excludes each of them from the port's own code, so a crate
qualifies where its safe API excludes them too, by whatever means it uses. The comment
beside the crate in the manifest gives the judgement in brief.

## Rust tree

The workspace depends on ffibox by path, on the checkout the host provides. The path is
the checkout's canonical one, with no symbolic link on it, and a `[patch]` that redirects
another source of ffibox names the same path: compile-fail snapshots normalize a path
dependency only where the compiler's paths match the dependency's canonical directory.
Name the checkout's revision in the report.
<!-- TODO: a released ffibox, as a versioned dependency, once `devel` reaches `main`.
Until then the path leaves the crate and pins no revision. -->

## Types and functions C shares

Read `docs/ownership.md`, `docs/borrows.md`, `docs/patterns.md`, `docs/vtables.md`,
`docs/hand-written.md` and `docs/outbound.md`.

### Types

A type that stays interoperable with C is held through ffibox's primitives wherever they
apply, as `docs/ownership.md` and `docs/borrows.md` walk from its C declaration to them.

While a type keeps its C layout, `define_ctype!` mints `Foo`, `FooRef<'a>` and `FooMut<'a>`,
and its owners are aliases of ffibox's owners over the policy that names its lifecycle
routines: `pub type FooBox = CBox<Foo, FooFree>;`, and `CArc<Foo, P>` for `FooArc`. A
value held inline that disposes its resources on drop is a `CVal<Foo, P>`. Once the type's
layout is native and C no longer allocates or frees it, `FooRef` and `FooMut` are native
borrows and `FooBox` is `Box<Foo>`, or `Pin<Box<Foo>>` while C keeps its address.

A struct whose layout is native while C still allocates or frees its storage cannot be held
by ffibox's single-object owners, which hold only C-layout types. Where C releases it with
its allocation family's free alone, the native type is not zero-sized and needs no drop
(`size_of::<Foo>() != 0` and `!core::mem::needs_drop::<Foo>()`, both asserted at compile
time), and C does not keep its address, `FooBox` is `Box<Foo, CAllocator<P>>` and a counted
run of them `Vec<Foo, CAllocator<P>>`. `P` is the family's `Copy` policy with the alignment
the family guarantees: an existing `CLenAlloc` policy of the family, or one declared with
`impl_clenalloc!`'s `align =`. A box is built with `CAllocator::try_box`, which refuses an
over-aligned type at compile time and returns C's out-of-memory failure, and handed to C
with `Box::into_raw_with_allocator`. A run grows with `Vec::try_reserve`, keeping C's
out-of-memory failure, and is handed to C through `CVec::try_from` and `into_raw_parts`. A
pointer C hands back is adopted with `Box::from_raw_in`, under the conditions
`CBox::into_box`'s documentation lists, and a run with `Vec::from_raw_parts_in`, its length
as its capacity, under the allocator's fit rule. Once C no longer allocates or frees it,
they become `Box<Foo>` and `Vec<Foo>`.
<!-- TODO: a native-layout struct that C still allocates or frees and that C releases
through a lifecycle routine of its own, that needs drop, whose address C keeps
(`Pin<Box<Foo, A>>` needs an allocator std does not accept yet) or that is
reference-counted (`Arc::new_in` is unstable) has no owner ffibox or std provides: it is
hand-written until one exists, or C's allocation of it is ported first. -->

### Functions

A C routine's status convention becomes a `Result` through `status`, an object returned
through an out-parameter a return value through `from_c_out` or `from_raw_out`, and C's
iteration conventions iterators, as `docs/patterns.md` maps them.

### Function pointers

A function pointer's callable type is a `CCallback`, where C holds it for a call or a
borrow, or a `CCallbackBox`, where C keeps it until it releases its context. Its Rust half
is a closure, a `CClosure` or a `CPayload`, which C reaches through its trampoline. Its C
half is a C function with its context, a `CFn` or a `CFnBox`, which Rust calls, built only
inside the crate through its `unsafe` constructor. A trampoline is the panic barrier,
`callback::barrier`, which also guards an export's body.

A struct of function pointers a library calls into, implemented by a Rust trait, is a
`CTable` whose slots `impl_cvtable!` mints, over the port's own `unsafe impl CVtable`, as
`docs/vtables.md` describes. A table C implements is held as any other C object. A family of
hooks that carries no context is trampolines over `callback::barrier`, not a table.

### Lifecycles

Each lifecycle is held by the owner `docs/ownership.md` chooses for its shape, over the
policy that names its routines. A policy with state, such as an allocator context, is held
by `CBoxState`. A Rust value whose release C drives, such as a refcounted user payload, is
a `CPayload`, released through the routine it gives C.

### Exports

An export gateway is built from the primitives `docs/outbound.md` chooses for what C does
with the Rust it reaches:

- the lifecycle routines C still calls on a ported type are `export_cnew!`,
  `export_cdrop!` and `export_cdupclone!` over the type's policy, which take and return
  its owners and handles;
- memory C frees comes from the allocator C frees it with: Rust's, `RustAlloc`, when C
  frees it through an exported release;
- a callback C passes an export is a `CFn` or a `CFnBox`, and a value C keeps a
  `CPayload`; and
- the gateway's body runs in `callback::barrier`.

## Testing

The public seam interface ffibox exports on a type is meant to be used inside the crate
only, as an escape hatch for external consumers, so it gets no UB tests: a test of it, for
UB or functionality, is a unit test.

## Reviewing

Read `docs/goals.md` before reviewing code that uses ffibox.

The code's use of ffibox's primitives is reviewed against ffibox's documentation, and its
hand-written representations against the contract ffibox would have enforced. For
undefined behaviour, the hazards that the Soundness section of `docs/goals.md` lists are
the checklist: each is excluded by the primitive or the producer's contract it names, or
is a finding.

A soundness or ergonomics gap in ffibox itself, in its safe primitives or its unsafe FFI
seams, is a defect in ffibox: file it in `crustify/reviews/` with its reproducer, and fix it
as [Growing ffibox](#growing-ffibox) describes.

## Growing ffibox

The agent adds a primitive to ffibox when the same interop pattern comes up in more than
one place in the port, or when a pattern's soundness argument is subtle enough that it
should be made once and tested once rather than repeated at each use. `docs/goals.md` is
what a new primitive is judged against: the properties it meets before it is added, among
them that it recurs in independent APIs rather than serving one project. A rule that holds
for one target alone stays in the port.

Change ffibox in its own repository, on a branch of its own, with its tests, its
documentation and its examples updated together, and have an agent that did not write the
primitive review it against `docs/goals.md`. Then migrate the port's uses of the pattern to
the primitive, and record in the report what each primitive replaced.
