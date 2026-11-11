---
name: testing-builds
description: "The builds tests run against and how coverage is measured: the prebuilt variants, private builds, coverage instrumentation, objects, suites and figures, and a worklist's coverage. Read before building or choosing a test build, and before measuring or comparing coverage."
---

# Testing builds

The builds every test of [`testing`](../SKILL.md) runs against, and how coverage is measured
over them.

## 1. Builds

Tests run against the target's prebuilt, immutable builds, recorded as the `variants` of
`crustify/artifacts/build.json`: each an out-of-tree `dir` and the `configure` and `build`
commands run from it, its `version` raised whenever a command changes. They are:

- `plain`, the functional baseline;
- `coverage`, the coverage-instrumented build for campaign measurements, instrumented as
  [Coverage](#2-coverage) describes; and
- one variant per sanitizer the campaign enables, whose tests build the Rust with the same
  sanitizer, so that a report from the Rust's own unsafe code is caught too, and whose C
  consumers that link the safe crate's Rust static library, from a module's integration
  on, link one built with the same instrumentation:
  - `asan-ubsan`, the general build, which FFI and lifecycle tests use;
  - `msan`, which instruments every component, the standard library included;
  - `tsan`, separate from `asan-ubsan`, since ASan and TSan instrument the same memory
    operations and their runtimes conflict; and
  - `bsan`, when BorrowSanitizer's `bsan` toolchain is installed (`cargo bsan --version`
    succeeds); it instruments the C through its own matched clang.

A Rust- or bindgen-only change reuses a matching variant: same C revision, `build.json`
version, compiler and instrumentation. Nothing writes into a variant's `dir`: each run's
logs and outputs go to paths of its own. A change to the compiled target, or no matching
variant, needs a private build, which the raw bindings link when `CRUSTIFY_BUILD_DIR` names
it in place of a variant, and the shared variants are rebuilt once that change lands.

## 2. Coverage

Coverage is counted with one instrument for C and Rust, so that a C figure and a Rust
figure, and the campaign's figures and those of a crate it is compared with, are counted
alike, and count the code under test only:

- **Instrumentation.** The `coverage` variant compiles the C with clang's source-based
  coverage, `-fprofile-instr-generate -fcoverage-mapping` in its compile and link flags,
  from a clang of the pinned nightly's LLVM major version, and the Rust is compiled on that
  nightly with `-C instrument-coverage`. One profiling runtime counts both, into a profile
  per process and module (`LLVM_PROFILE_FILE=<dir>/%p-%m.profraw`), and the nightly's
  `llvm-profdata` and `llvm-cov` read both. gcc's `--coverage` and gcov are not used: their
  lines follow the line table of the optimized code, which the optimization level changes,
  so their figures cannot be compared with Rust's.
- **Test code.** Test code is not instrumented, so it is neither credited as covered nor
  counted as code to cover. Counted, it would inflate the suite that runs it, whose own
  lines run whenever it does, and deflate every other suite, whose denominator would hold
  lines it never runs. Every test item of the measured crate, under `#[test]`,
  `#[cfg(test)]` or a `cfg` that requires `test`, carries `#[coverage(off)]`, which covers
  everything nested in it, and the crate root enables `#![feature(coverage_attribute)]`.
  The attributes are added in a scratch copy of the measured tree under `crustify/tmp/`,
  which is measured in its place, so that the measured crates are not changed. Integration
  test crates, examples, benches, the crate root's build script and the generated raw
  bindings under `ffi/` are left out of the report by path. Test code that is not an item, such as a `#[cfg(test)]`
  block inside a library function, stays instrumented, and is reported with the figures.
- **Objects.** C coverage is read from the objects the tests load: the variant's shared
  libraries, or the object files a crate links statically, every TU compiled into them
  counting, and one no test reaches at zero. A figure covers the sources of the library it
  names, selected by directory, so that the copies of its inline functions and of its TUs
  that other libraries compile, the configuration headers the build generates and the C's
  own tests count toward none. Rust coverage is read from every test and doctest binary of
  the crate. All objects are passed for every suite, so that every suite has the same
  denominator.
- **Suites.** Each suite runs alone, into its own profile directory, merged into one
  profile; the total merges the suites' profiles, so it is their union, never their sum.
  Doctests are a suite of their own.
- **Figures.** The figures are the totals `llvm-cov report` prints, unmodified: line,
  function and region coverage, line coverage leading. Its per-line views (`llvm-cov show`
  and the LCOV export) count lines differently, marking the bodies of C macro definitions
  as executed: they locate gaps, and never compute a figure.
- **Comparisons.** A crate the campaign is compared with is measured the same way: its
  test items marked in a scratch copy, its own release of the C built as the `coverage`
  variant is, its suites run alone, and its figures read from `llvm-cov report`. A
  comparison names its scope, and both sides are measured over the same one.

### 2.1 A worklist's coverage

A worklist's tests run against the campaign's `coverage` variant, measured as
above, and coverage is inspected for the C and Rust execution
paths belonging to the worklist. Focused tests are added to cover its reachable uncovered
paths. Paths that remain uncovered because they are unreachable, environment-dependent, or
intentionally nondeterministic are reported as such.

Coverage is maximized, not gated. Each worklist reports its regions and branches beside
its lines, and which of its types' states and transitions, as the analysis lists them, its
tests reach. In a port, a module's C is the reference until its integration: its coverage
under the module's equivalence tests shows how much of its behaviour they compare, set
against what its own C tests reach. From the integration on, the module's coverage is its
Rust's.
