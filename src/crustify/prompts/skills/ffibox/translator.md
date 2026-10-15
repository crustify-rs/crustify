<!-- SKILL -->

Each section below augments the how-to section it names, as `<how-to> › <section>`.

## testing › UB tests

There is no need to add UB tests on the public seam interface ffibox exports on a type, as
it is only meant to be exercised internally by the crate, as an escape hatch for external
consumers. Any UB or functionality test on it is an internal unit test.
