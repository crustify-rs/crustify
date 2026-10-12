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

---

## Workflow - symbols

### 3. Raw lifetime strategies

`CBox` and `CArc` own only `CCell` layout types: a single C struct is a `CBox<Foo, P>` with matching
constructor / destructor pairs, which asserts the right validity claim based on the allocator (e.g. zeroed
coupled with `CZeroable` vs. raw coupled with `MaybeUninit`). Arrays are `CVec<MaybeUninit<T>, P>` with a safe initializer, or
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

If you discover any soundness or ergonomics gap in ffibox, both in its safe primitives
or unsafe FFI seams, emit a reproducer and report in `crustify/reviews` to demonstrate
the flaw, like you would for bugs in the target repo. Then, emit a patch in a separate
branch and worktree of the local ffibox checkout.