# ffibox › rust/items/binding

## Type route

A type that stays interoperable with C is bound through ffibox's primitives wherever they
apply, as its documentation describes.

## Symbol route › Lifecycle strategies

`CBox` and `CArc` own only `CCell` layout types: a single C struct is a `CBox<Foo, P>`
with matching constructor and destructor pairs, which asserts the validity claim its
allocator makes, zeroed memory with `CZeroable` or raw memory with `MaybeUninit`. An array
is a `CVec<MaybeUninit<T>, P>` with a safe initializer, or a `CVec<T, P>` for a
`CPlainElem`; copies into the allocator use `CVec::from_slice` or `CSlice::to_cvec`, and
its `CLenClone` declares `ALIGN`. A Rust value whose release C drives, such as a
refcounted user payload, gets a hand-written owner whose free callback runs the value's
destructor.
