# Testing

Classify tests by what they target, and place each where the conventions' Testing section places
tests of its kind:

- UB tests on the safe public interface ensure it does not reach UB, mainly by not
  triggering sanitizer/Miri crashes, or by failing to compile for a given illegal path;
- UB tests on the unsafe public interface target UB bugs there: each public `unsafe fn` or
  method of your workset, called within its stated `# Safety` contract, edge cases
  included. Raw `ffi::` round-trips are not UB tests on the unsafe interface; they are unit
  or equivalence tests;
- equivalence tests ensure the safe public interface matches the C-observable behaviour,
  mainly by passing equivalence assertions;
- unit tests ensure the internal routines behave correctly, mainly by passing Rust
  assertions.

Construct test objects through safe constructors. While a type has none, adopt the raw
constructor's result in one documented unsafe fixture per type, and replace the fixture
once the safe constructor exists.

## UB tests

Emit tests to ensure the public API of your workset is free of UB.

Test the unsafe public interface with one suite per public unsafe function or method your
workset adds, with its inputs built through the safe API wherever one exists. A workset
that adds no public unsafe API adds no UB tests on the unsafe interface.

The sanitizers available are those the campaign built: the instrumented variants of
`crustify/build.json`, where `asan-ubsan` provides ASan and UBSan, `tsan` TSan and `bsan`
BSan. A sanitizer without a variant is not available, so no test is written for it and
none runs under it. Miri needs no C build and is always available.

Each available sanitizer is a separate obligation:

- ASan/UBSan: bounds errors, use-after-free, use-after-return, invalid free,
  double free, leak, pointer/alignment UB, and integer/division/shift UB.
- BSan: conflicting foreign writes and retained foreign pointers across Rust reborrows.
  Write these tests like the others. BSan is the slowest instrument and reports false
  positives at the foreign boundary, so it runs only as Regressions below describes.
- TSan: races reachable through safe APIs, including every asserted `Send` or `Sync`
  implementation and threaded callback.
- Miri: Rust-side lifetime, bounds, initialization, validity, alignment, intrinsic, and
  `repr` assumptions. Miri cannot call the foreign library, read its globals or spawn a
  process. Give every test that cannot run under Miri `#[cfg_attr(miri, ignore = "<reason>")]`
  on its test function, naming what stops it: `"calls C"`, `"reads a C global"`, and so on.
  Mark a test only after running it alone under Miri and seeing Miri stop there; never to
  silence a Miri report of undefined behaviour, a panic or a failed assertion, which are
  findings. Do not use `#[cfg(not(miri))]` or test-name filters instead: with the attribute
  in place, `cargo miri test` runs every other test.

Exercise every owner and borrowed form, shared and mutable access path, lifecycle
strategy, generic instance, and callback variant emitted by the batch. Attempt to outlive
the owner, alias a reborrow, reenter a callback, and drop a parent first.

Use compile-fail doctests or `trybuild` when the type system should reject the program.


## Equivalence tests

Emit functional equivalence tests that run the raw C implementation and public Rust API on
equivalent, independently owned inputs.

Compare:

- return values and errors;
- out-parameters and buffers;
- callbacks;
- state transitions; and
- lifecycle effects.

Use multi-call sequences and compare after each step. Single calls are only a baseline.

For `port`, the reference build must have the Rust feature disabled so the C symbol cannot
resolve to the Rust export.

Do not copy a confirmed C defect into Rust. Document the divergence, retain equivalence
tests for unaffected behaviour, and make the corrected-behaviour regression a unit test.


## Unit tests

Write a unit test when Rust assertions supply the verdict or the test exercises internal
facilities, including:

- Rust-only `Iterator`, `Debug`, `Clone`, conversions, and builders;
- input rejected by Rust before FFI, including the error and no panic;
- deliberate correction of defective C behaviour;
- unsafe adoption through `from_raw`, `from_ptr`, or similar constructors;
- private or `pub(crate)` constructors and internal destructor/drop plumbing; and
- resource release exercised through any of those raw, unsafe, or internal paths.


## Coverage

Run the worklist's tests with the campaign's coverage-instrumented build and inspect
coverage for the C and Rust execution paths belonging to the worklist. Add focused tests
to maximize coverage on the reachable uncovered paths triggered by your worklist. Report
paths that remain uncovered because they are unreachable, environment-dependent, or
intentionally nondeterministic.

## Regressions

Every batch checks, lints and tests the workspace on the tree it lands:

```bash
cargo check --workspace
cargo clippy --workspace
cargo test --workspace
```

Every FFI, UB, and equivalence test runs against the matching reusable sanitized C library
or a private sanitized replacement, and under every available sanitizer. BSan, when
available, is the exception, and runs with discipline:

- A translation batch runs BSan only on the tests it wrote and expects to trigger it, by
  exact name; never a whole binary or suite. It runs its own tests under Miri.
- A review batch in its sub-campaign's last wave owns the sub-campaign's BSan gate. Its
  wave is the last when its index is the highest of its subsystem's waves in
  `crustify/campaigns/<campaign-id>/schedule.json`; its branch's name gives the link unit,
  subsystem and wave. The gate covers everything the sub-campaign landed, so a report on an
  earlier wave's items is that batch's to triage as well. It runs over the whole
  workspace, one invocation per test binary in parallel, each under a `timeout`, on the
  wave tip before any change. Each run starts in the background and is waited on to exit;
  its output is neither polled nor read while it runs. Only true positives are pursued.
- A review batch in any other wave runs BSan only on the individual reproducers it emits,
  each alone; never on a test binary, a suite or the workspace.
- Only a true positive, a report that reproduces through the Rust side as a single test or
  standalone reproducer, becomes a UB finding.

Every review batch also owns the workspace-wide Miri gate, in every wave: one
`cargo +nightly miri test` per test binary (`--lib`, and `--test <name>` for each
integration binary), in parallel, each with `-- --skip compile_fail`, on the wave tip
before any change. Each run starts in the background and is waited on to exit. The gate
passes only with no Miri error: a test that stops at the foreign boundary without the
attribute gets it, and any other Miri error is a UB candidate of the item it touches.

A review batch that patches what it finds runs both gates again on the tree it lands,
after its last rebase. One that patches nothing files each true positive either gate finds
as a UB report.

When C changed, the configured C build and baseline run with the Rust feature off, and for
`port` again with it on. A wrap-only batch with no C change does not need the full C
baseline.
