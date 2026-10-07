<!-- SKILL -->

---

## Workflow - types and symbols - wrap objective 

Read each primitive provided by ffibox and use them where
applicable to implement safe bindings for your worklist's types and symbols that need
to stay interoperable with C/C++. 

Hand-write a representation when ffibox cannot express the proven contract,
while preserving the same seam and safety-comment discipline. Annotate a
hand-written implementation with the `/// Handwritten` anchor so we can
account it later.

Use `CArc` only when a clone is the same pointer with a higher count (`CRefClone`); an API
whose reference is a new allocation per holder (e.g. FFmpeg's `av_buffer_ref`) is `CBox` + `CDupClone`, with
writability checked before any mutable view of the shared bytes.

---

## Workflow - symbols

### 3. Raw lifetime strategies

`CBox` and `CArc` own only `CCell` layout types: a single C struct is a `CBox<Foo, P>` from a
value constructor that writes a formed `Foo` (e.g. `Foo::default()` plus setters) into the
allocation, never raw storage. Arrays are `CVec<MaybeUninit<T>, P>` with a safe initializer, or
`CVec<T, P>` for `CPlainElem`; copies into the allocator use `CVec::from_slice` /
`CSlice::to_cvec`, and its `CLenClone` declares `ALIGN`. A Rust value whose release C drives (a
refcounted user payload) gets a hand-written owner whose free callback runs the value's
destructor.

---

## Tests

### UB tests

There is no need to add UB tests on the public seam interface exported by ffibox on a type, as
these are only meant to be exercised internally by the crate, while acting as escape hatches for
external consumers. Any UB or functionality test on those should be internal and emited in the
`#[cfg(test)] mod unit_tests` module.

---

## Review mode

If you discover any soundness or ergonomics hole in ffibox, both in its safe primitives
or unsafe FFI seams, proceed by emiting a reproducer in `crustify/reviews` to demonstrate
the flaw, like you would for bugs in the target repo. Then, emit a patch in a separate
branch and worktree in the local ffibox checkout.