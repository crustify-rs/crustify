---
name: testing
description: "How work is tested: test kinds and suites, test objects, how thoroughly a wrapper is tested, UB tests under sanitizers and Miri, equivalence and unit tests, and the C tests carried over; testing-builds and testing-gates give the builds, coverage and gates. Read before writing tests."
---

# Testing

Tests are classified by what decides them and by the side of a module they test, and each
is placed where the conventions' Testing section places tests of its kind:

- UB tests on the safe public interface show that it does not reach UB, mainly by not
  triggering sanitizer or Miri crashes, or by failing to compile for a given illegal path;
- UB tests on the unsafe public interface target UB there: each public `unsafe fn` or
  method a workset adds, called within its stated `# Safety` contract, edge cases
  included. Raw `ffi::` round-trips are not UB tests on the unsafe interface; they are unit
  or equivalence tests;
- equivalence tests show that the Rust behaves as the C it translates, mainly by passing
  equivalence assertions: `equiv_pub` on the module's exported API, `equiv_priv` on its
  internals; and
- unit tests show that the Rust keeps its contract, by passing Rust assertions, without
  the C: `unit_pub` on the public interface, `unit_priv` on the internal routines.

Test objects are constructed through safe constructors. The UB tests on the safe public
interface use the safe API alone, their suite forbidding `unsafe_code` at its root: a type
that no safe constructor or producer yields yet gets those tests in the batch that wraps
its first one. Elsewhere, while a type has no safe constructor, one documented unsafe
fixture per type adopts the raw constructor's result, and is replaced once the safe
constructor exists.

A test exercises the safe API wherever it can, so that the later stages of a port, which
keep that API, keep it passing. A test of a C form an item keeps, such as an unsafe
adoption, a function pointer's unsafe constructor, a trampoline or an export, goes with
the stage that removes the form.

How thoroughly a wrapper is tested follows how long it lasts. One a port will replace, a
type wrapped ahead of its port or a dependency whose module will be ported, keeps its safe
API through the port: it gets the tests of its public interface, which outlive it, and
none of its internals. A permanent one, every wrapper of a wrap campaign, the foundational
modules' and one whose later stage is held back for good, gets every kind.

The builds the tests run against and how coverage is measured are
[`testing-builds`](builds/SKILL.md)'s, and the gates every landing passes
[`testing-gates`](gates/SKILL.md)'s.

## 1. UB tests

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

Each available sanitizer is a separate obligation of an item while it reaches C or unsafe
code; once it reaches neither, as a port's later stages bring about, Miri covers it alone:

- ASan/UBSan: bounds errors, use-after-free, use-after-return, invalid free, double free,
  pointer/alignment UB, and integer/division/shift UB.
- MSan: use of uninitialized memory, including branches and addresses computed from it,
  uninitialized bytes crossing the FFI boundary, and struct tails or buffers a foreign
  initializer left partly unwritten. Its build instruments every component, the standard
  library through `-Zbuild-std` included: memory written by uninstrumented code reads as
  uninitialized, so a partial build reports falsely.
- BSan: conflicting foreign writes and retained foreign pointers across Rust reborrows.
  These tests are written like the others. BSan is the slowest instrument and reports
  false positives at the foreign boundary, so it runs only as
  [`testing-gates`](gates/SKILL.md)' Regressions section describes.
- TSan: races reachable through safe APIs, including every asserted `Send` or `Sync`
  implementation and threaded callback.
- Miri: Rust-side lifetime, bounds, initialization, validity, alignment, intrinsic, and
  `repr` assumptions. Miri cannot call the foreign library, read its globals or spawn a
  process, so every test that cannot run under it carries
  `#[cfg_attr(miri, ignore = "<reason>")]` on its test function, naming what stops it:
  `"calls C"`, `"reads a C global"`, and so on. A test is marked only after it was run
  alone under Miri and seen to stop there; never to silence a Miri report of undefined
  behaviour, a panic or a failed assertion, which are findings. The mark goes once what it
  names no longer stops the test, as an integration or a later stage brings about. Neither
  `#[cfg(not(miri))]` nor test-name filters stand in for the attribute: with it in place,
  `cargo miri test` runs every other test.

A leak is not undefined behaviour, in Rust or in C, so neither a LeakSanitizer report,
which ASan's runtime makes by default, nor Miri's leak check is a UB candidate.

UB tests exercise every owner and borrowed form, shared and mutable access path, lifecycle
strategy, generic instance, and callback variant a batch emits. They attempt to outlive the
owner, alias a reborrow, reenter a callback, and drop a parent first. Storage that C and
Rust both allocate or free, or whose allocator a port moves, is tested for a free through
the wrong allocator.

When the type system should reject a program, the test is a compile-fail doctest or a
`trybuild` case.

## 2. Equivalence tests

Equivalence tests run the C and the Rust that translates it on independently owned inputs
built from one description, and compare:

- return values and errors;
- out-parameters and buffers;
- callbacks;
- state transitions; and
- lifecycle effects.

They use multi-call sequences and compare after each step; single calls are only a
baseline.

They compare what the C specifies, through the mapping the safe API applies to it, such as
its status returns as errors and its null pointers as absent values, and not what it leaves
unspecified, such as an iteration order, a message's text, a pointer's value or an
allocation count. A confirmed C defect is not copied into Rust. The divergence is
documented, equivalence tests are retained for the unaffected behaviour, and the
corrected-behaviour regression is a unit test.

`equiv_pub` holds the module's exported API to the C strictly. `equiv_priv` compares an
internal routine with its C counterpart only where one exists, since an idiomatic port may
restructure the internals; a C function the raw bindings do not reach, one with internal
linkage, is compared through the functions that call it.

In a port, equivalence tests are the evidence of a module's migration. While its waves run,
the variants still build its C, which they reach through the raw bindings while the ported
Rust runs under its own names; at its integration they are retired with the C, and the
module evolves as Rust from then on, as
[`porting-workflow`](../../workflows/porting-workflow/SKILL.md)'s Principles section
describes. Only its exports still keep the C contract, which the C tests that stay check.

## 3. Unit tests

A unit test is the right kind when Rust assertions supply the verdict: `unit_pub` on the
public interface, whose tests outlive the C, and `unit_priv` on internal facilities,
including:

- Rust-only `Iterator`, `Debug`, `Clone`, conversions, and builders;
- input rejected by Rust before FFI, including the error and no panic;
- deliberate correction of defective C behaviour;
- unsafe adoption through `from_raw`, `from_ptr`, or similar constructors;
- private or `pub(crate)` constructors and internal destructor/drop plumbing; and
- resource release exercised through any of those raw, unsafe, or internal paths.

## 4. C tests carried over

The `unit_pub` tests the port batches write for a module's items mirror the regression
cases of the C tests tied to it: their inputs, edge cases and call sequences, with the
assertions adapted to the safe Rust contract, so that what the C suites established
outlives them. Each names the C test case it carries over, so that before a C test
leaves, at the module's integration or with the exports it calls, the cases none carries
over are listed, and each is carried over or recorded as behaviour the safe API
deliberately changes.
