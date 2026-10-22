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

Test objects are constructed through safe constructors. While a type has none, one
documented unsafe fixture per type adopts the raw constructor's result, and is replaced
once the safe constructor exists.

## 1. Builds

Tests run against the target's prebuilt, immutable builds, recorded as the `variants` of
`crustify/artifacts/build.json`: each an out-of-tree `dir` and the `configure` and `build`
commands run from it, its `version` raised whenever a command changes. They are:

- `plain`, the functional baseline;
- `coverage`, the coverage-instrumented build for campaign measurements; and
- one variant per sanitizer the campaign enables:
  - `asan-ubsan`, the general build, which FFI and lifecycle tests use;
  - `msan`, which instruments every component, the standard library included;
  - `tsan`, separate from `asan-ubsan`, since ASan and TSan instrument the same memory
    operations and their runtimes conflict; and
  - `bsan`, when BorrowSanitizer's `bsan` toolchain is installed (`cargo bsan --version`
    succeeds); it instruments the C through its own matched clang.

A Rust- or bindgen-only change reuses a matching variant: same C revision, `build.json`
version, compiler and instrumentation. A change to the compiled target needs a private
build, and the shared variants are rebuilt once that change lands.

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
  leak, pointer/alignment UB, and integer/division/shift UB.
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

TODO (porting): how a `port` batch's equivalence tests reach the C reference while its
module's waves run, and how they are retired at integration, as
[`workflows/porting.md`](workflows/porting.md)'s Principles and Builds sections describe.
The Rust feature switch this section assumed no longer exists.

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

A worklist's tests run against the campaign's coverage-instrumented build, and coverage is
inspected for the C and Rust execution paths belonging to the worklist. Focused tests are
added to cover its reachable uncovered paths. Paths that remain uncovered because they are
unreachable, environment-dependent, or intentionally nondeterministic are reported as such.

Coverage counts the code under test, never the tests themselves. Rust coverage counts only
the authored non-test sources: the test crates are dropped and, inside the library sources,
every line under a `#[cfg(test)]` item such as an inline `mod unit_tests`. Otherwise a
workload that cannot run those lines reads low, and the unit tests are credited for
executing themselves. Each workload runs alone against the coverage-instrumented build, and
the total is the union of their lines, never the sum of the workloads.

## 6. Regressions

Every batch checks, lints and tests the workspace on the tree it lands:

```bash
cargo check --workspace
cargo clippy --workspace
cargo test --workspace
```

Every FFI, UB, and equivalence test runs against the matching reusable sanitized C library
or a private sanitized replacement, and under every available sanitizer.

BSan, when available, is run for every batch and at module end:

- For a batch, it runs only on the individual tests or reproducers the batch expects to
  trigger it, each by exact name and alone; never on a whole test binary, a suite or the
  workspace.
- At module end, it runs as a gate over everything the module landed: the
  whole workspace, one invocation per test binary in parallel, each under a `timeout`.

Miri is run after every wave, as a gate over the whole workspace: one
`cargo +nightly miri test` per test binary (`--lib`, and `--test <name>` for each
integration binary), in parallel, each with `-- --skip compile_fail`. The gate passes only
with no Miri error: a test that stops at the foreign boundary without the attribute gets
it, and any other Miri error is a UB candidate of the item it touches.

Each gate run starts in the background and is waited on to exit; its output is neither
polled nor read while it runs. BSan reports false positives at the foreign boundary, so
only a true positive, a report that reproduces through the Rust side as a single test or
standalone reproducer, becomes a UB finding.

When C changed, the configured C build and baseline run. A wrap-only batch with no C
change does not need the full C baseline.

TODO (porting): the gates of a `port` batch, which changes no C, and those of a module's
integration, which links its Rust in place of its TU, removes the C tests gated with it and
runs the target's test suite over the hybrid, as
[`workflows/porting.md`](workflows/porting.md)'s Builds section describes; and how a
module's C tests are ported into the Rust suites.
