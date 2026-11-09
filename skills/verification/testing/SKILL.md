---
name: testing
description: "How work is tested: test kinds, prebuilt builds, coverage, UB tests under sanitizers and Miri, equivalence and unit tests, regression gates. Read before writing tests or running a batch's gates."
---

# Testing

Tests are classified by what they target, and each is placed where the conventions'
Testing section places tests of its kind:

- UB tests on the safe public interface show that it does not reach UB, mainly by not
  triggering sanitizer or Miri crashes, or by failing to compile for a given illegal path;
- UB tests on the unsafe public interface target UB there: each public `unsafe fn` or
  method a workset adds, called within its stated `# Safety` contract, edge cases
  included. Raw `ffi::` round-trips are not UB tests on the unsafe interface; they are unit
  or equivalence tests;
- equivalence tests show that the safe public interface matches the C-observable
  behaviour, mainly by passing equivalence assertions;
- unit tests show that the internal routines behave correctly, mainly by passing Rust
  assertions.

Test objects are constructed through safe constructors. The UB tests on the safe public
interface use the safe API alone, their suite forbidding `unsafe_code` at its root: a type
that no safe constructor or producer yields yet gets those tests in the batch that wraps
its first one. Elsewhere, while a type has no safe constructor, one documented unsafe
fixture per type adopts the raw constructor's result, and is replaced once the safe
constructor exists.

## 1. Builds

Tests run against the target's prebuilt, immutable builds, recorded as the `variants` of
`crustify/artifacts/build.json`: each an out-of-tree `dir` and the `configure` and `build`
commands run from it, its `version` raised whenever a command changes. They are:

- `plain`, the functional baseline;
- `coverage`, the coverage-instrumented build for campaign measurements, instrumented as
  [Coverage](#11-coverage) describes; and
- one variant per sanitizer the campaign enables:
  - `asan-ubsan`, the general build, which FFI and lifecycle tests use;
  - `msan`, which instruments every component, the standard library included;
  - `tsan`, separate from `asan-ubsan`, since ASan and TSan instrument the same memory
    operations and their runtimes conflict; and
  - `bsan`, when BorrowSanitizer's `bsan` toolchain is installed (`cargo bsan --version`
    succeeds); it instruments the C through its own matched clang.

A Rust- or bindgen-only change reuses a matching variant: same C revision, `build.json`
version, compiler and instrumentation. A change to the compiled target needs a private
build, which the raw bindings link when `CRUSTIFY_BUILD_DIR` names it in place of a
variant, and the shared variants are rebuilt once that change lands.

### 1.1 Coverage

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

## 2. UB tests

UB tests show that a workset's public API is free of UB.

The unsafe public interface is tested with one suite per public unsafe function or method
a workset adds, its inputs built through the safe API wherever one exists. A workset that
adds no public unsafe API has no UB tests on the unsafe interface.

The sanitizers available are those the campaign built: the instrumented variants of
`crustify/artifacts/build.json`, where `asan-ubsan` provides ASan and UBSan, `msan` MSan, `tsan` TSan
and `bsan` BSan. A sanitizer without a variant is not available, so no test is written for
it and none runs under it. Miri needs no C build and is always available.

A target that ships its own sanitizers, because the standard ones cannot run against it,
is tested with those instead: the Linux kernel's KASAN, KMSAN, KCSAN and kernel UBSAN each
stand for the sanitizer they implement.

Each available sanitizer is a separate obligation:

- ASan/UBSan: bounds errors, use-after-free, use-after-return, invalid free, double free,
  pointer/alignment UB, and integer/division/shift UB.
- MSan: use of uninitialized memory, including branches and addresses computed from it,
  uninitialized bytes crossing the FFI boundary, and struct tails or buffers a foreign
  initializer left partly unwritten. Its build instruments every component, the standard
  library through `-Zbuild-std` included: memory written by uninstrumented code reads as
  uninitialized, so a partial build reports falsely.
- BSan: conflicting foreign writes and retained foreign pointers across Rust reborrows.
  These tests are written like the others. BSan is the slowest instrument and reports
  false positives at the foreign boundary, so it runs only as Regressions below describes.
- TSan: races reachable through safe APIs, including every asserted `Send` or `Sync`
  implementation and threaded callback.
- Miri: Rust-side lifetime, bounds, initialization, validity, alignment, intrinsic, and
  `repr` assumptions. Miri cannot call the foreign library, read its globals or spawn a
  process, so every test that cannot run under it carries
  `#[cfg_attr(miri, ignore = "<reason>")]` on its test function, naming what stops it:
  `"calls C"`, `"reads a C global"`, and so on. A test is marked only after it was run
  alone under Miri and seen to stop there; never to silence a Miri report of undefined
  behaviour, a panic or a failed assertion, which are findings. Neither
  `#[cfg(not(miri))]` nor test-name filters stand in for the attribute: with it in place,
  `cargo miri test` runs every other test.

A leak is not undefined behaviour, in Rust or in C, so neither a LeakSanitizer report,
which ASan's runtime makes by default, nor Miri's leak check is a UB candidate.

UB tests exercise every owner and borrowed form, shared and mutable access path, lifecycle
strategy, generic instance, and callback variant a batch emits. They attempt to outlive the
owner, alias a reborrow, reenter a callback, and drop a parent first.

When the type system should reject a program, the test is a compile-fail doctest or a
`trybuild` case.

## 3. Equivalence tests

Equivalence tests run the raw C implementation and the public Rust API on equivalent,
independently owned inputs, and compare:

- return values and errors;
- out-parameters and buffers;
- callbacks;
- state transitions; and
- lifecycle effects.

They use multi-call sequences and compare after each step; single calls are only a
baseline.

While a module's waves run, the variants still build its C, so a `port` batch's
equivalence tests reach the C reference through the raw bindings, while the ported Rust
runs under its own names. At the module's integration its C leaves the build, and its raw
bindings would reach its own exports: its equivalence tests are retired with it, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section describes.

A confirmed C defect is not copied into Rust. The divergence is documented, equivalence
tests are retained for the unaffected behaviour, and the corrected-behaviour regression is
a unit test.

## 4. Unit tests

A unit test is the right kind when Rust assertions supply the verdict or the test exercises
internal facilities, including:

- Rust-only `Iterator`, `Debug`, `Clone`, conversions, and builders;
- input rejected by Rust before FFI, including the error and no panic;
- deliberate correction of defective C behaviour;
- unsafe adoption through `from_raw`, `from_ptr`, or similar constructors;
- private or `pub(crate)` constructors and internal destructor/drop plumbing; and
- resource release exercised through any of those raw, unsafe, or internal paths.

## 5. Coverage

A worklist's tests run against the campaign's `coverage` variant, measured as
[Coverage](#11-coverage) describes, and coverage is inspected for the C and Rust execution
paths belonging to the worklist. Focused tests are added to cover its reachable uncovered
paths. Paths that remain uncovered because they are unreachable, environment-dependent, or
intentionally nondeterministic are reported as such.

## 6. Regressions

Every batch checks, formats, lints and tests the workspace on the tree it lands, with
warnings denied, as [`toolchain`](../../rust/toolchain/SKILL.md) describes:

```bash
cargo check --workspace --all-targets
cargo +nightly-<date> fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Every build of those gates runs in the raw bindings' campaign mode, as
[`bindgen`](../../rust/bindgen/SKILL.md)'s Build modes section describes, so that each fails when the
committed bindings do not match their input. A batch that changed the raw bindings, or a
landing that changes `c/`, also packages the safe crate, built alone in bundled mode from
the C it packages:

```bash
CRUSTIFY_BUILD_VARIANT= cargo package --config 'patch.crates-io.<crate>.path="<path>"' ...
```

Until the out-of-tree wrappers are published, each crate the package depends on is patched
to its local source, so that the package builds alone.

Every FFI, UB, and equivalence test runs against the matching reusable sanitized C library
or a private sanitized replacement, and under every available sanitizer.

BSan, when available, is run for every batch and at module end:

- For a batch, it runs only on the individual tests or reproducers the batch expects to
  trigger it, each by exact name and alone; never on a whole test binary, a suite or the
  workspace.
- At module end, it runs as a gate over everything the module landed: the
  whole workspace, one invocation per test binary, as many side by side as
  [`concurrency`](../../operations/concurrency/SKILL.md) describes, each under a `timeout`.

Miri is run after every wave, as a gate over the whole workspace: one
`cargo +nightly miri test` per test binary (`--lib`, and `--test <name>` for each
integration binary), as many side by side as [`concurrency`](../../operations/concurrency/SKILL.md) describes,
each with `-- --skip compile_fail`. The gate passes only
with no Miri error: a test that stops at the foreign boundary without the attribute gets
it, and any other Miri error is a UB candidate of the item it touches.

Each gate run starts in the background and is waited on to exit; its output is neither
polled nor read while it runs. BSan reports false positives at the foreign boundary, so
only a true positive, a report that reproduces through the Rust side as a single test or
standalone reproducer, becomes a UB finding.

When C changed, the configured C build and baseline run. A wrap-only batch with no C
change does not need the full C baseline.

A batch validates its own change on its own base first. Its rebase onto the integration
branch, under the landing lock that [`versioning`](../../operations/versioning/SKILL.md)'s Landing section
describes, then combines that change with the work landed since: the gates run again are
those that could catch a regression the combination introduces, judged from what the
batch's change and the rebased-in changes touch and how they could interact. A gate that
neither side's changes could affect keeps the result it had, and a rebase that conflicts
makes the resolved tree new work of the batch's own.

A `port` batch changes no C: its gates are those above, run against the variants with its
module's export feature off, so that the ported Rust is tested beside the C it replaces.

A module's integration removes its translation unit and the C tests tied to it from `c/`,
rebuilds the variants from the C that remains and turns the module's export feature on, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Builds section describes. Its gates
are those above, in campaign mode over the rebuilt variants, and the target's remaining C
tests, which link the remaining C and the safe crate's Rust static library, so that the C
reaches the ported module through its exports. A remaining C test is tied to no
integrated module: it checks the remaining C's behaviour, with the ported Rust under it.
A C test tied to a module asserts the C contract the port may change, so it leaves with
the module.

The tests the port batches write for a module's items mirror the regression cases of the
C tests tied to it: their inputs, edge cases and call sequences, with the assertions
adapted to the safe Rust contract, so that what the C suites established outlives them.
