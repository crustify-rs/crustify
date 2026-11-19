---
name: testing
description: "What a port's tests show, and the sanitizers and Miri they run under; testing-builds and testing-gates give the builds, coverage and gates. Read before writing tests."
---

# Testing

The port's tests show that:

- the safe public API cannot reach undefined behaviour, whatever safe code calls it, and
  that the type system rejects what it should;
- the unsafe public API, and the exports C calls, reach no undefined behaviour when called
  within their stated contracts;
- the Rust behaves as the C it replaces, run side by side on the same inputs and compared
  after each call: return values and errors, out-parameters and buffers, callbacks, state
  and lifecycle effects;
- the Rust keeps its own contract, by Rust assertions alone, including where it corrects a
  defect of the C;
- the cases of the C tests tied to a component still hold, carried over to Rust before
  those tests leave with the C; and
- the C suites the remaining C keeps still pass against the Rust.

They run under these instruments, each in the build
[`testing-builds`](builds/SKILL.md) gives it:

- ASan with UBSan: bounds errors, use-after-free, invalid and double free, and pointer,
  alignment and integer undefined behaviour;
- TSan: data races reachable through the safe API, including every asserted `Send` or
  `Sync` and every threaded callback;
- MSan, where it is built: uninitialized memory, including what crosses the C boundary;
- BSan, where it is built: aliasing violations across the C boundary; and
- Miri: the Rust side's undefined behaviour, on the tests that do not call C.

The gates every merge passes are [`testing-gates`](gates/SKILL.md)'s.
