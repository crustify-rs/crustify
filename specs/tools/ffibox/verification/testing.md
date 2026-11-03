# ffibox › verification/testing

## UB tests

The public seam interface ffibox exports on a type is meant to be exercised inside the
crate only, as an escape hatch for external consumers, so it gets no UB tests: a test of
it, for UB or functionality, is a unit test.
