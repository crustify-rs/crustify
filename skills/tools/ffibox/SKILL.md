---
name: ffibox
description: "The library the campaign's Rust holds C memory through, in both directions: owners, handles, lifecycle policies, status conventions, callbacks and exports. Read before writing any wrapper, owner, lifecycle strategy, callable type or export, when judging a crate for adoption, and when testing or reviewing one."
---

# ffibox

ffibox is the library a campaign's Rust expresses C's ownership and lifetime conventions
through, in both directions: memory C allocates, frees, copies, refcounts or locks, held
from Rust behind a safe API, and memory Rust owns that C holds, calls or reads. Its
primitives stand in for raw pointers and hand-written `Drop` impls wherever C aliases a
value; what C does not alias is plain Rust.

Its `README.md` is read in full before the first wrapper is written, and each section
below names the documents under its `docs/` that its stage reads, also in full. Which
primitive serves which C declaration, and how each is built, is those documents'. A
representation ffibox cannot express is hand-written, as its `docs/hand-written.md`
describes, with the same seam and safety-comment discipline. Its goals and non-goals,
`docs/goals.md`, are what a change to ffibox is judged against, as
[`evolution`](../../crustify/evolution/SKILL.md) describes.

What follows is how ffibox serves each stage: each section names the skill and section it
adds to, and states only what ffibox adds there.

## Planning

### Dependencies › Adopted crates

A candidate crate's soundness is read against the hazards `docs/goals.md`'s G9 lists,
each of which ffibox excludes from the campaign's own bindings: the crate qualifies where
its safe API excludes them too, by whatever means it uses.

## Binding workflow

### Binding workflow › Rust tree

The workspace depends on ffibox by path, on the checkout of its `devel` branch that the
host provides, `ffibox = { path = "/opt/venv/share/ffibox" }` in Crustify's image, so that
each run records its revision among its task's `revisions`.
<!-- TODO: a released ffibox, as a versioned dependency, once `devel` reaches `main`.
Until then the path leaves the crate, against `bindgen`'s Layout section, and pins no
revision. -->

## Binding and porting

Binding reads `docs/ownership.md`, `docs/borrows.md`, `docs/patterns.md` and
`docs/hand-written.md`; porting reads `docs/outbound.md` too.

### Binding types

A type that stays interoperable with C is bound through ffibox's primitives wherever they
apply, as `docs/ownership.md` and `docs/borrows.md` walk from its C declaration to them.

### Binding types › Safe layout

While a type keeps its C layout, `define_ctype!` mints `Foo`, `FooRef<'a>` and `FooMut<'a>`,
and its owners are aliases of ffibox's owners over the policy that names its lifecycle
routines: `pub type FooBox = CBox<Foo, FooFree>;`, and `CArc<Foo, P>` for `FooArc`. A
value held inline that disposes its resources on drop is a `CVal<Foo, P>`.

### Binding symbols › Functions

A C routine's status convention becomes a `Result` through `status`, an object returned
through an out-parameter a return value through `from_c_out` or `from_raw_out`, and C's
iteration conventions iterators, as `docs/patterns.md` maps them.

### Binding symbols › Function pointers

A function pointer's callable type is a `CCallback`, where C holds it for a call or a
borrow, or a `CCallbackBox`, where C keeps it until it releases its context. Its Rust half
is a closure, a `CClosure` or a `CPayload`, which C reaches through its trampoline; its C
half is a C function with its context, a `CFn` or a `CFnBox`, which Rust calls, built only
inside the crate through its `unsafe` constructor. A trampoline is the panic barrier,
`callback::barrier`, which also guards an export's body.
<!-- TODO: ffibox has no primitive yet for a struct of function pointers a library calls
into, bound to a trait the Rust side implements: a binding hand-writes it until it does. -->

### Binding symbols › Lifecycle strategies

Each lifecycle is held by the owner `docs/ownership.md` chooses for its shape, over the
policy that names its routines; a policy with state, such as an allocator context, is held
by `CBoxState`. A Rust value whose release C drives, such as a refcounted user payload, is
a `CPayload`, released through the routine it gives C.

### Porting › FFI boundary

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

### Porting types › Structs

Until a ported struct's `port/layout`, its handles are ffibox's, as
[Binding types › Safe layout](#binding-types--safe-layout) describes; from it
on, `FooRef` and `FooMut` are aliases of native borrows. Its owners stay ffibox's until its
`port/memory`, their policy calling its lifecycle routines, C's through their raw bindings
until each is ported, then the Rust ones. A `port/memory` before its `port/layout` keeps
them ffibox's and changes their policy to `RustAlloc` alone: `FooBox` becomes
`CBox<Foo, RustAlloc>`, its handles unchanged, until its `port/layout` makes it
`Box<Foo>`, or `Pin<Box<Foo>>` while C keeps its address.
<!-- TODO: ffibox's owners hold only `CCell` layout types, so an owner over C's allocator
of a struct whose layout is native, between its `port/layout` and its `port/memory`, is
hand-written until ffibox has one. -->

## Testing

### Testing › UB tests

The public seam interface ffibox exports on a type is meant to be exercised inside the
crate only, as an escape hatch for external consumers, so it gets no UB tests: a test of
it, for UB or functionality, is a unit test.

## Reviewing

Reviewing reads `docs/goals.md`.

### Reviewing › Objectives

A workset's use of ffibox's primitives is reviewed against ffibox's documentation, and its
hand-written representations against the contract ffibox would have enforced. Under `ub`,
the hazards `docs/goals.md`'s G9 lists are the checklist: each is excluded by the
primitive or the producer's contract it names, or is a finding.

### Reviewing › Reports

A soundness or ergonomics gap in ffibox itself, in its safe primitives or its unsafe FFI
seams, is a defect in a tool: a proposal, as any tool defect is.
