# ffibox

ffibox is the library a campaign's Rust holds C memory through: memory a C library
allocates, frees, copies, refcounts or locks, wrapped in the raw bindings' types behind a
safe API, or managed by ported code. C's ownership and lifetime conventions are expressed
through its primitives rather than raw pointers and hand-written `Drop` impls. Its own
documentation, its `README.md`, which walks from a C declaration to the wrapper it needs,
and the documents under its `docs/`, is read in full before the first wrapper is written.

A representation ffibox cannot express is hand-written, with the same seam and
safety-comment discipline.
