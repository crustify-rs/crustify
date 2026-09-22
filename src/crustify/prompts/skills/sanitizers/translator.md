---
name: sanitizers
description: >-
  Which instrumented build a test runs against. ASan+UBSan for FFI and
  lifecycle tests, the separate TSan build for race tests, BSan for aliasing
  when available, and Miri for Rust-side reasoning with no C build and no
  foreign calls. Read before running or authoring a UB test.
---

# Sanitizer builds

The campaign prepares one reusable build per instrument. Reuse the matching
one; treat it as immutable and write agent-unique logs and outputs.

- **ASan + UBSan** — FFI and lifecycle tests.
- **TSan** — race tests only, and a build of its own. Never run a test against
  a build combining it with ASan: the two instrument the same memory
  operations and their runtimes conflict.
- **BSan** — aliasing, when BorrowSanitizer is available.
- **Miri** — Rust-side only. It needs no C build and **cannot call the foreign
  library**, so a test that crosses FFI cannot be a Miri test.

A build matches only when the C revision, `build.json` version, compiler and
instrumentation all agree with your batch. Otherwise build privately and report
the invalidation.
