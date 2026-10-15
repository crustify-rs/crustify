---
name: testing
description: >-
  How Crustify tests a safe binding: UB tests on the safe and unsafe public
  interface, equivalence tests against C, and unit tests; which instruments
  they must pass (ASan/UBSan, BSan, TSan, Miri); and how coverage is
  measured. Read it before writing any test.
---

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

Cover every instrument prepared by the campaign as a separate obligation:

- ASan/UBSan: bounds errors, use-after-free, use-after-return, invalid free,
  double free, leak, pointer/alignment UB, and integer/division/shift UB.
- BSan: conflicting foreign writes and retained foreign pointers across Rust reborrows.
  Write these tests like the others. BSan is the slowest instrument and reports false
  positives at the foreign boundary, so run it only as your Regressions step prescribes.
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
